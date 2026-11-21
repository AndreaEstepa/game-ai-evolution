import numpy as np


ACTION_BUTTONS = {
    "neutral": [],
    "left": ["left"],
    "right": ["right"],
    "jump": ["jump"],
    "left_jump": ["left", "jump"],
    "right_jump": ["right", "jump"],
    "attack": ["attack"],
    "dash": ["dash"],
}
ACTION_NAMES = tuple(ACTION_BUTTONS)


class MLPPolicy:
    def __init__(self, input_size=10, hidden_size=16, action_names=ACTION_NAMES):
        """
        Crea una politica con el tamaño de entrada, oculta y de accion configurado
        """
        if input_size <= 0 or hidden_size <= 0 or not action_names:
            raise ValueError("La red debe tener capas y acciones no vacias")

        self.input_size = int(input_size)
        self.hidden_size = int(hidden_size)
        self.action_names = tuple(action_names)

    @property
    def parameter_count(self):
        """
        Devuelve el numero de pesos y sesgos en la politica
        """
        return (
            self.hidden_size * self.input_size
            + self.hidden_size
            + len(self.action_names) * self.hidden_size
            + len(self.action_names)
        )

    def forward(self, genome, observation):
        """
        Computa la salida de la rd neuronal para un genoma yuna observacion dados
        """
        parameters = np.asarray(genome, dtype=np.float64)
        inputs = np.asarray(observation, dtype=np.float64)

        if parameters.shape != (self.parameter_count,):
            raise ValueError(
                f"El genoma debe contener {self.parameter_count} parametros"
            )
        if inputs.shape != (self.input_size,):
            raise ValueError(f"La observacion debe contener {self.input_size} valores")

        if not np.all(np.isfinite(parameters)) or not np.all(np.isfinite(inputs)):
            raise ValueError("El genoma y la observacion deben ser finitos")

        position = 0

        hidden_weights = []
        for _ in range(self.hidden_size):
            row = parameters[position:position + self.input_size]
            hidden_weights.append(row)
            position += self.input_size

        hidden_biases = parameters[position:position + self.hidden_size]
        position += self.hidden_size

        hidden = []
        for neuron_index in range(self.hidden_size):
            value = np.dot(hidden_weights[neuron_index], inputs)
            value += hidden_biases[neuron_index]
            hidden.append(np.tanh(value))

        output_scores = []
        for _ in self.action_names:
            weights = parameters[position:position + self.hidden_size]
            position += self.hidden_size
            score = np.dot(weights, hidden)
            output_scores.append(score)

        for action_index in range(len(self.action_names)):
            output_scores[action_index] += parameters[position]
            position += 1

        return np.array(output_scores)

    def choose_action(self, genome, observation):
        """
        Devuelve la acción con mayor puntuacion para un genoma
        """
        outputs = self.forward(genome, observation)
        action_index = int(np.argmax(outputs))
        return self.action_names[action_index]
