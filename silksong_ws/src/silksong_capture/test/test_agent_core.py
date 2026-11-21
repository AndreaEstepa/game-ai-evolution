import json
import unittest

import numpy as np

from silksong_capture.agent.evolution import GeneticAlgorithm
from silksong_capture.agent.network import MLPPolicy
from silksong_capture.agent.observations import OBSERVATION_SIZE, encode_detections


class ObservationTests(unittest.TestCase):
    def test_encodes_hornet_and_nearest_flower(self):
        payload = json.dumps(
            {
                "hornet": {
                    "center": {"x": 100, "y": 90},
                    "orientation": "R",
                    "score": 0.9,
                },
                "flowers": [
                    {"center": {"x": 290, "y": 90}, "score": 0.8},
                    {"center": {"x": 120, "y": 108}, "score": 0.7},
                ],
            }
        )

        observation = encode_detections(payload)

        self.assertEqual(observation.shape, (OBSERVATION_SIZE,))
        self.assertEqual(observation[2], 1.0)
        self.assertEqual(observation[3], 1.0)
        self.assertAlmostEqual(observation[5], 20 / 320)
        self.assertAlmostEqual(observation[6], 18 / 180)
        self.assertEqual(observation[8], 1.0)
        self.assertEqual(observation[9], 0.7)

    def test_missing_detections_have_presence_flags_off(self):
        observation = encode_detections('{"hornet":null,"flowers":[]}')

        self.assertEqual(observation.shape, (OBSERVATION_SIZE,))
        self.assertEqual(observation[2], 0.0)
        self.assertEqual(observation[8], 0.0)

    def test_rejects_malformed_detection(self):
        with self.assertRaises(ValueError):
            encode_detections('{"hornet": [], "flowers":[]}')


class NetworkTests(unittest.TestCase):
    def test_network_has_fixed_output_shape(self):
        policy = MLPPolicy(hidden_size=4)
        outputs = policy.forward(
            np.zeros(policy.parameter_count),
            np.zeros(policy.input_size),
        )

        self.assertEqual(outputs.shape, (len(policy.action_names),))
        self.assertEqual(policy.choose_action(
            np.zeros(policy.parameter_count),
            np.zeros(policy.input_size),
        ), "neutral")


class EvolutionTests(unittest.TestCase):
    def test_scoring_population_advances_generation(self):
        evolution = GeneticAlgorithm(
            gene_count=3,
            population_size=4,
            elite_count=1,
            tournament_size=2,
            seed=7,
        )

        for score in (1.0, 2.0, 3.0):
            self.assertFalse(evolution.submit_fitness(score))
        self.assertTrue(evolution.submit_fitness(4.0))

        self.assertEqual(evolution.generation, 1)
        self.assertEqual(evolution.individual_index, 0)
        self.assertEqual(evolution.population.shape, (4, 3))
        self.assertEqual(evolution.best_fitness, 4.0)
        self.assertTrue(all(score is None for score in evolution.fitnesses))

    def test_rejects_non_finite_fitness(self):
        evolution = GeneticAlgorithm(
            gene_count=2,
            population_size=2,
            elite_count=1,
            tournament_size=2,
        )
        with self.assertRaises(ValueError):
            evolution.submit_fitness(float("nan"))


if __name__ == "__main__":
    unittest.main()
