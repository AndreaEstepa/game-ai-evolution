import cv2
import numpy as np

def reduce_resolution(frame, config):
    """
    Recibe una imagen y reduce su resolución
    """ 
    
    width = config["resize_width"]
    height = config["resize_height"]
    
    small = cv2.resize(
        frame,
        (width, height),
        interpolation = cv2.INTER_AREA
    )

    return small

def process_image(frame, config):
    """
    Recibe una imagen BGR y devuelve:
    - Imagen binaria
    - Imagen de bordes
    """

    # Reducir resolución
    small = reduce_resolution(frame,config)

    # Convertir a escala de grises
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)

    # Reducir ruido
    blur_size = config["blur"]

    if blur_size >= 3:
        if blur_size % 2 == 0:
            blur_size += 1

        gray = cv2.GaussianBlur(
            gray,
            (blur_size, blur_size),
            0
        )

    # Umbralización binaria
    if config["adaptive_threshold"]:
        binary = cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11,
            2
        )
    else:
        _, binary = cv2.threshold(
            gray,
            config["threshold"],
            255,
            cv2.THRESH_BINARY
        )

    # Detectar bordes
    edges = cv2.Canny(
        gray, 
        config["canny_low"],
        config["canny_high"]
    )

    contours, _ = cv2.findContours(
        edges, 
        cv2.RETR_EXTERNAL, 
        cv2.CHAIN_APPROX_SIMPLE
    )

    min_area = config["min_area"]

    filtered_image = np.zeros_like(gray)

    for cnt in contours:
        if cv2.contourArea(cnt) >= min_area:
            cv2.drawContours(
                    filtered_image,
                    [cnt],
                    -1,
                    (256),
                    thickness=cv2.FILLED
            )

    return binary, filtered_image, gray

def detect_red(frame, config):
    """
    Detecta pixeles rojos y devuelve una máscara binaria.
    """

    # Reducir resolución
    small = reduce_resolution(frame,config)

    hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)

    red_config = config["red_detection"]
    
    saturation_min = red_config["saturation_min"]
    value_min = red_config["value_min"]

    lower_red_1 = np.array([0, saturation_min, value_min])
    upper_red_1 = np.array([10, 255, 255])

    lower_red_2 = np.array([170, saturation_min, value_min])
    upper_red_2 = np.array([179, 255, 255])

    msk1 = cv2.inRange(hsv, lower_red_1, upper_red_1)
    msk2 = cv2.inRange(hsv, lower_red_2, upper_red_2)

    red_mask =  cv2.bitwise_or(msk1, msk2)

    return red_mask
