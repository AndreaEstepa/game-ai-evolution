import csv
import json
import math
from pathlib import Path
import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, Float32, String
from .evolution import GeneticAlgorithm
from .network import ACTION_BUTTONS, MLPPolicy
from .observations import encode_detections


class EvolutionaryAgent(Node):
    """
    Consume detecciones de visión y emite acciones para un episodio puntuado manualmente.
    """
    def __init__(self):
        """
        Pone la política, el algoritmo genético, y el topic de ROS.
        """
        super().__init__("evolutionary_agent")

        self.declare_parameter("image_width", 320)
        self.declare_parameter("image_height", 180)
        self.declare_parameter("hidden_size", 16)
        self.declare_parameter("population_size", 50)
        self.declare_parameter("elite_count", 2)
        self.declare_parameter("tournament_size", 3)
        self.declare_parameter("mutation_probability", 0.1)
        self.declare_parameter("mutation_sigma", 0.15)
        self.declare_parameter("random_seed", 1)
        self.declare_parameter("scores_path", "evolution_scores.csv")
        self.declare_parameter("best_policy_path", "best_policy.json")

        self.image_width = int(self.get_parameter("image_width").value)
        self.image_height = int(self.get_parameter("image_height").value)
        self.policy = MLPPolicy(hidden_size=int(self.get_parameter("hidden_size").value))
        self.evolution = GeneticAlgorithm(
            gene_count=self.policy.parameter_count,
            population_size=int(self.get_parameter("population_size").value),
            elite_count=int(self.get_parameter("elite_count").value),
            tournament_size=int(self.get_parameter("tournament_size").value),
            mutation_probability=float(self.get_parameter("mutation_probability").value),
            mutation_sigma=float(self.get_parameter("mutation_sigma").value),
            seed=int(self.get_parameter("random_seed").value),
        )
        self.scores_path = Path(str(self.get_parameter("scores_path").value))
        self.best_policy_path = Path(str(self.get_parameter("best_policy_path").value))
        self.episode_active = False
        self.invalid_message_reported = False

        self.action_publisher = self.create_publisher(String, "/agent/action", 10)
        self.detections_subscription = self.create_subscription(
            String,
            "/vision/detections",
            self.on_detections,
            1,
        )
        self.start_subscription = self.create_subscription(
            Bool,
            "/agent/start_episode",
            self.on_start_episode,
            10,
        )
        self.fitness_subscription = self.create_subscription(
            Float32,
            "/agent/fitness",
            self.on_fitness,
            10,
        )
        self.get_logger().info(
            "Listo: /vision/detections -> MLP -> /agent/action. "
            "Usa /agent/start_episode para iniciar y /agent/fitness al terminar "
            "cada episodio."
        )

    def on_start_episode(self, message):
        """
        Habilita o pausa la publiccion de acciones para el individuo activo
        """
        if not message.data:
            self.episode_active = False
            self.get_logger().info("Episodio pausado")
            return
        if self.episode_active:
            self.get_logger().warning("Ya hay un episodio activo")
            return
        self.episode_active = True
        self.get_logger().info(
            f"Generacion {self.evolution.generation}, "
            f"individuo {self.evolution.individual_index + 1}/"
            f"{self.evolution.population_size}"
        )

    def on_detections(self, message):
        """
        Convierte cada mesje detectado en una acción discreta"""
        if not self.episode_active:
            return

        try:
            observation = encode_detections(
                message.data,
                image_width=self.image_width,
                image_height=self.image_height,
            )
        except ValueError as error:
            if not self.invalid_message_reported:
                self.get_logger().error(f"Deteccion ignorada: {error}")
                self.invalid_message_reported = True
            return

        self.invalid_message_reported = False
        action = self.policy.choose_action(self.evolution.current_genome, observation,)

        output = String()
        output.data = json.dumps(
            {
                "action": action,
                "buttons": ACTION_BUTTONS[action],
                "generation": self.evolution.generation,
                "individual": self.evolution.individual_index,
            },
            separators=(",", ":"),
        )
        self.action_publisher.publish(output)

    def on_fitness(self, message):
        """
        Puntua al individuo activo y prepara el siguiente para repetir el proceso
        """
        if not self.episode_active:
            self.get_logger().error("Fitness recibido sin episodio activo; no se ha aplicado.")
            return

        score = float(message.data)
        if not math.isfinite(score):
            self.get_logger().error("Fitness ignorado: debe ser finito.")
            return

        generation = self.evolution.generation
        individual = self.evolution.individual_index
        self.episode_active = False
        generation_completed = self.evolution.submit_fitness(score)
        self._append_score(generation, individual, score)
        self._save_best_policy()
        self.get_logger().info(
            f"Fitness {score:.4f} registrado para generacion {generation}, "
            f"individuo {individual + 1}."
        )
        if generation_completed:
            self.get_logger().info(
                f"Generacion {self.evolution.generation} preparada; "
                "reinicia el juego y envia /agent/start_episode."
            )
        else:
            self.get_logger().info(
                "Reinicia el juego para el siguiente individuo y envia "
                "/agent/start_episode."
            )

    def _append_score(self, generation, individual, score):
        """
        Un capitulo completo de puntuacion se guarda en un csv para su luego analizarlo
        """
        try:
            new_file = not self.scores_path.exists()
            with self.scores_path.open("a", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                if new_file:
                    writer.writerow(("generation", "individual", "fitness"))
                writer.writerow((generation, individual, score))
        except OSError as error:
            self.get_logger().error(f"No se pudo guardar el historial: {error}")

    def _save_best_policy(self):
        """
        permite guardar la mejor politica observada hasta ahora
        """
        if self.evolution.best_genome is None:
            return
        payload = {
            "generation": self.evolution.best_generation,
            "individual": self.evolution.best_individual_index,
            "fitness": self.evolution.best_fitness,
            "input_size": self.policy.input_size,
            "hidden_size": self.policy.hidden_size,
            "actions": list(self.policy.action_names),
            "weights": self.evolution.best_genome.tolist(),
        }
        try:
            self.best_policy_path.write_text(json.dumps(payload, indent=2), encoding="utf-8",)
        except OSError as error:
            self.get_logger().error(f"No se pudo guardar la mejor politica: {error}")


def main(args=None):
    rclpy.init(args=args)
    node = EvolutionaryAgent()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == "__main__":
    main()