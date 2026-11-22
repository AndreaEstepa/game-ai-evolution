import time

import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import Bool, Float32, String

from .episode_core import (
    is_black_frame,
    success_fitness,
    timeout_fitness,
)

class EpisodeManager(Node):
    """
    Termina un episodio por fundido negro o por tiempo limite
    """
    def __init__(self):
        super().__init__("episode_manager")
        self.declare_parameter("timeout_seconds", 60.0)
        self.declare_parameter("black_level", 25.0)
        self.declare_parameter("black_fraction", 0.75)
        self.declare_parameter("black_frames", 3)
        self.declare_parameter("restart_delay", 2.0)

        self.timeout_seconds = float(self.get_parameter("timeout_seconds").value)
        self.black_level = float(self.get_parameter("black_level").value)
        self.black_fraction = float(self.get_parameter("black_fraction").value)
        self.black_frames_needed = int(self.get_parameter("black_frames").value)
        self.restart_delay = float(self.get_parameter("restart_delay").value)
        self.bridge = CvBridge()
        self.active = False
        self.start_time = 0.0
        self.black_count = 0
        self.max_progress = 0.0

        self.start_publisher = self.create_publisher(
            Bool,
            "/agent/start_episode",
            10,
        )
        self.fitness_publisher = self.create_publisher(
            Float32,
            "/agent/fitness",
            10,
        )
        self.reset_publisher = self.create_publisher(
            Bool,
            "/agent/reset_episode",
            10,
        )
        self.status_publisher = self.create_publisher(
            String,
            "/episode/status",
            10,
        )

        self.screen_subscription = self.create_subscription(
            Image,
            "/vision/screen",
            self.on_screen,
            10,
        )
        self.detections_subscription = self.create_subscription(
            String,
            "/vision/detections",
            self.on_detections,
            10,
        )

        self.timer = self.create_timer(0.1, self.check_timeout)
        self.create_timer(0.5, self.start_first_episode)
        self.get_logger().info(
            "Supervisor preparado. Objetivo: fundido negro; "
            "limite: 60 segundos."
        )

    def start_first_episode(self):
        if self.active:
            return
        self.start_episode()

    def start_episode(self):
        self.active = True
        self.start_time = time.monotonic()
        self.black_count = 0
        self.max_progress = 0.0
        message = Bool()
        message.data = True
        self.start_publisher.publish(message)
        self.publish_status("episode_started")
        self.get_logger().info("Episodio iniciado")

    def on_detections(self, message):
        if not self.active:
            return

        try:
            import json
            detections = json.loads(message.data)
            hornet = detections.get("hornet")
            if hornet is not None:
                center = hornet.get("center")
                if center is not None:
                    hornet_x = float(center["x"])
                    progress = hornet_x / 320.0
                    if progress > self.max_progress:
                        self.max_progress = progress
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            return

    def on_screen(self, message):
        if not self.active:
            return
        try:
            image = self.bridge.imgmsg_to_cv2(message, desired_encoding="bgr8")
        except Exception as error:
            self.get_logger().warning(
                f"No se pudo leer la imagen del episodio: {error}"
            )
            return

        if is_black_frame(
            image,
            black_level=self.black_level,
            black_fraction=self.black_fraction,
        ):
            self.black_count += 1
        else:
            self.black_count = 0

        if self.black_count >= self.black_frames_needed:
            elapsed = time.monotonic() - self.start_time
            fitness = success_fitness(elapsed, self.timeout_seconds)
            self.end_episode("success", fitness)

    def check_timeout(self):
        if not self.active:
            return
        elapsed = time.monotonic() - self.start_time
        if elapsed >= self.timeout_seconds:
            fitness = timeout_fitness(
                self.max_progress,
                elapsed,
                self.timeout_seconds,
            )
            self.end_episode("timeout", fitness)

    def end_episode(self, reason, fitness):
        if not self.active:
            return
        elapsed = time.monotonic() - self.start_time
        self.active = False
        start_message = Bool()
        start_message.data = False
        self.start_publisher.publish(start_message)
        fitness_message = Float32()
        fitness_message.data = float(fitness)
        self.fitness_publisher.publish(fitness_message)

        reset_message = Bool()
        reset_message.data = True
        self.reset_publisher.publish(reset_message)
        self.publish_status(
            f"{reason}:fitness={fitness:.2f}:time={elapsed:.2f}"
        )
        self.get_logger().info(
            f"Episodio terminado: {reason}, fitness={fitness:.2f}"
        )

        restart_timer = self.create_timer(
            self.restart_delay,
            lambda: self.restart_episode(restart_timer),
        )

    def restart_episode(self, timer):
        timer.cancel()
        self.start_episode()

    def publish_status(self, status):
        message = String()
        message.data = status
        self.status_publisher.publish(message)


def main(args=None):
    rclpy.init(args=args)
    node = EpisodeManager()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == "__main__":
    main()