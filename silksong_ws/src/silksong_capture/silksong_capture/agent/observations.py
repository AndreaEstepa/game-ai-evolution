import json
import math

import numpy as np


OBSERVATION_SIZE = 10


def _number(value, name):
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{name} debe ser numerico") from error
    if not math.isfinite(number):
        raise ValueError(f"{name} debe ser finito")
    return number


def _center(detection, name):
    center = detection.get("center")
    if center is not None:
        if not isinstance(center, dict):
            raise ValueError(f"{name}.center debe ser un objeto")
        x = _number(center.get("x"), f"{name}.center.x")
        y = _number(center.get("y"), f"{name}.center.y")
    else:
        x = _number(detection.get("x"), f"{name}.x")
        y = _number(detection.get("y"), f"{name}.y")
        width = _number(detection.get("width"), f"{name}.width")
        height = _number(detection.get("height"), f"{name}.height")
        x += width / 2.0
        y += height / 2.0
    return x, y


def _score(detection, name):
    score = _number(detection.get("score", 0.0), f"{name}.score")
    return float(np.clip(score, 0.0, 1.0))


def encode_detections(payload, image_width=320, image_height=180):
    """
    Emcodea las detecciones JSON en una observacion normalizada de tamaño fijo
    """
    # Lee el mensaje y comprueba que sea un objeto JSON.
    try:
        detections = json.loads(payload)
    except (json.JSONDecodeError, TypeError) as error:
        raise ValueError("El mensaje de detecciones no contiene JSON valido") from error

    if not isinstance(detections, dict):
        raise ValueError("El mensaje de detecciones debe ser un objeto JSON")

    image_width = _number(image_width, "image_width")
    image_height = _number(image_height, "image_height")

    if image_width <= 0 or image_height <= 0:
        raise ValueError("image_width e image_height deben ser mayores que 0")

    # Posicion normalizada de Hornet.
    hornet = detections.get("hornet")
    if hornet is None:
        hornet_x = image_width / 2.0
        hornet_y = image_height / 2.0
        hornet_present = 0.0
        orientation = 0.0
        hornet_score = 0.0
    else:
        if not isinstance(hornet, dict):
            raise ValueError("hornet debe ser un objeto o null")
        hornet_x, hornet_y = _center(hornet, "hornet")
        hornet_present = 1.0
        orientation_name = hornet.get("orientation")
        if orientation_name not in (None, "L", "R"):
            raise ValueError("hornet.orientation debe ser L, R o null")
        orientation = {"L": -1.0, "R": 1.0}.get(orientation_name, 0.0)
        hornet_score = _score(hornet, "hornet")

    # Busca la flor mas cercana a Hornet.
    flowers = detections.get("flowers", [])
    if not isinstance(flowers, list):
        raise ValueError("flowers debe ser una lista")

    nearest_flower = None
    nearest_distance = math.inf

    for index, flower in enumerate(flowers):
        if not isinstance(flower, dict):
            raise ValueError(f"flowers[{index}] debe ser un objeto")

        flower_x, flower_y = _center(flower, f"flowers[{index}]")
        distance = math.hypot(flower_x - hornet_x, flower_y - hornet_y)

        if distance < nearest_distance:
            nearest_distance = distance
            nearest_flower = (flower, flower_x, flower_y, index)

    if nearest_flower is None:
        flower_dx = 0.0
        flower_dy = 0.0
        flower_distance = 0.0
        flower_present = 0.0
        flower_score = 0.0
    else:
        flower, flower_x, flower_y, index = nearest_flower
        flower_dx = (flower_x - hornet_x) / image_width
        flower_dy = (flower_y - hornet_y) / image_height
        flower_dx = float(max(-1.0, min(1.0, flower_dx)))
        flower_dy = float(max(-1.0, min(1.0, flower_dy)))
        flower_distance = math.hypot(flower_dx, flower_dy)
        flower_distance = min(flower_distance / math.sqrt(2.0), 1.0)
        flower_present = 1.0
        flower_score = _score(flower, f"flowers[{index}]")

    hornet_x_normalized = hornet_x / image_width
    hornet_y_normalized = hornet_y / image_height
    hornet_x_normalized = max(0.0, min(1.0, hornet_x_normalized))
    hornet_y_normalized = max(0.0, min(1.0, hornet_y_normalized))

    return np.array([
        hornet_x_normalized,
        hornet_y_normalized,
        hornet_present,
        orientation,
        hornet_score,
        flower_dx,
        flower_dy,
        flower_distance,
        flower_present,
        flower_score,
    ])
