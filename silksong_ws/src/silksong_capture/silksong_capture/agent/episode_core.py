import math


def is_black_frame(image, black_level=25.0, black_fraction=0.75):
    """
    Comprueba si una imagen esta suficientemente oscura para ser un fundido o no
    """
    if image is None or image.size == 0:
        return False
    if len(image.shape) == 3:
        blue = image[:, :, 0].astype(float)
        green = image[:, :, 1].astype(float)
        red = image[:, :, 2].astype(float)
        brightness = (blue + green + red) / 3.0
    else:
        brightness = image.astype(float)
    black_pixels = brightness < black_level
    fraction = float(black_pixels.mean())
    return fraction >= black_fraction


def timeout_fitness(max_progress, elapsed_seconds, timeout_seconds):
    """
    Calcula una puntuacion para los episodios que terminan por tiempo eseora
    """
    if elapsed_seconds < 0:
        elapsed_seconds = 0.0
    if timeout_seconds <= 0:
        timeout_seconds = 1.0
    progress = max(0.0, min(1.0, float(max_progress)))
    elapsed = max(0.0, min(float(elapsed_seconds), timeout_seconds))
    return float(progress * 100.0 - elapsed / timeout_seconds * 20.0)

def success_fitness(elapsed_seconds, timeout_seconds):
    """
    Da una bonificacion grande si el jugador llega al fundido negro y asi aprenda
    """
    elapsed = max(0.0, float(elapsed_seconds))
    timeout = max(1.0, float(timeout_seconds))
    remaining = max(0.0, timeout - elapsed)
    return float(1000.0 + remaining * 10.0)

def finite_fitness(value):
    """
    Comprueba que la puntuacion sepueda enviarrr por ROS
    """
    number = float(value)
    return math.isfinite(number)