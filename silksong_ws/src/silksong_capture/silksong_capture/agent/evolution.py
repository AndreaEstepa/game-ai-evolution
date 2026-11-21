import math

import numpy as np


class GeneticAlgorithm:
    def __init__(
        self,
        gene_count,
        population_size=50,
        elite_count=2,
        tournament_size=3,
        mutation_probability=0.1,
        mutation_sigma=0.15,
        seed=1,
    ):
        """
        Inicializa una poblacion reproducible de genomas de valores reales
        """
        if gene_count <= 0:
            raise ValueError("gene_count debe ser mayor que 0")
        if population_size < 2:
            raise ValueError("population_size debe ser al menos 2")
        if not 1 <= elite_count < population_size:
            raise ValueError("elite_count no es valido")
        if not 1 <= tournament_size <= population_size:
            raise ValueError("tournament_size fuera de rango")
        if not 0.0 <= mutation_probability <= 1.0:
            raise ValueError("mutation_probability debe estar entre 0 y 1")
        if mutation_sigma < 0.0 or not math.isfinite(mutation_sigma):
            raise ValueError("mutation_sigma debe ser finito y no negativo")

        self.gene_count = gene_count
        self.population_size = population_size
        self.elite_count = elite_count
        self.tournament_size = tournament_size
        self.mutation_probability = mutation_probability
        self.mutation_sigma = mutation_sigma

        self._random = np.random.default_rng(seed)

        #cada fila de population es un individuo formado porpesos dela red.
        self.population = self._random.normal(
            0.0,
            0.5,
            size=(population_size, gene_count),
        )

        self.fitnesses = [None] * self.population_size
        self.generation = 0
        self.individual_index = 0
        self.best_fitness = None
        self.best_genome = None
        self.best_generation = None
        self.best_individual_index = None

    @property
    def current_genome(self):
        """
        devuelcve una copia del genoma del individuo activo
        """
        return self.population[self.individual_index].copy()

    def submit_fitness(self, fitness):
        """
        Puntua al individuo activo. basicamente devuelve True cuando se avanza una generacion
        """
        try:
            score = float(fitness)
        except (TypeError, ValueError) as error:
            raise ValueError("fitness debe ser numerico") from error

        if not math.isfinite(score):
            raise ValueError("fitness debe ser finito")

        if self.fitnesses[self.individual_index] is not None:
            raise RuntimeError("El individuo activo ya tiene una puntuacion")

        self.fitnesses[self.individual_index] = score

        if self.best_fitness is None or score > self.best_fitness:
            self.best_fitness = score
            self.best_genome = self.current_genome
            self.best_generation = self.generation
            self.best_individual_index = self.individual_index

        if self.individual_index + 1 < self.population_size:
            self.individual_index += 1
            return False

        self._advance_generation()
        return True

    def _select_parent(self):
        # Elige varios individuos al azar y devuelve el que tiene mejor fitness.
        candidates = self._random.choice(
            self.population_size,
            size=self.tournament_size,
            replace=False,
        )

        best_index = candidates[0]
        for index in candidates:
            if self.fitnesses[index] > self.fitnesses[best_index]:
                best_index = index

        return self.population[best_index]

    def _advance_generation(self):
        #ordena los individuos de mejor a peor
        ranked = []
        for index in range(self.population_size):
            ranked.append((self.fitnesses[index], index))
        ranked.sort(reverse=True)

        #yyyyyy los mejores pasan directamente a la siguiente generacion.
        next_population = []
        for _, index in ranked[:self.elite_count]:
            next_population.append(self.population[index].copy())

        while len(next_population) < self.population_size:
            first_parent = self._select_parent()
            second_parent = self._select_parent()

            # Mezcla los pesos de los dos padres.
            child = []
            for gene_index in range(self.gene_count):
                if self._random.random() < 0.5:
                    child.append(first_parent[gene_index])
                else:
                    child.append(second_parent[gene_index])

            child = np.array(child)

            #cadapeso puede cambiar un poco por la mutacion.
            for gene_index in range(self.gene_count):
                if self._random.random() < self.mutation_probability:
                    change = self._random.normal(
                        0.0,
                        self.mutation_sigma,
                    )
                    child[gene_index] += change

            next_population.append(np.clip(child, -5.0, 5.0))

        self.population = np.array(next_population)
        self.fitnesses = [None] * self.population_size
        self.individual_index = 0
        self.generation += 1
