import cv2
import time
import numpy as np
import json

from pathlib import Path
from mss import MSS
from image_processor import process_image, detect_red

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config.json"

with open(CONFIG_PATH, "r", encoding="utf-8") as file:
          config = json.load(file)

monitor_id = config["monitor"]
region = config["region"]
window_name = config["window_name"]
fps_limit = config["fps_limit"]
vision_config = config["vision"]
red_detection = vision_config["red_detection"]

cv2.namedWindow("Original", cv2.WINDOW_NORMAL)
cv2.namedWindow("Binaria", cv2.WINDOW_NORMAL)
cv2.namedWindow("Bordes", cv2.WINDOW_NORMAL)
cv2.namedWindow("Gris", cv2.WINDOW_NORMAL)
cv2.namedWindow("Rojo", cv2.WINDOW_NORMAL)

try:
    with MSS() as sct:
        
        if monitor_id >= len(sct.monitors):
            print("Monitores detectados:")
            for i, monitor in enumerate(sct.monitors):
                print(i,monitor)

            raise ValueError(f"El monitor {monitor_id} no existe")

        monitor = sct.monitors[monitor_id]

        print("Iniciando captura...")

        while True:
            start = time.time()

            region = {
               "left": monitor["left"] + region["left"],
                "top": monitor["top"] + region["top"],
                "width": region["width"],
                "height": region["height"]
            }

            screenshot = sct.grab(region)

            frame = np.array(screenshot)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
            
            binary, edges, gray = process_image(
                frame,
                vision_config
            )

            cv2.imshow("Original", frame)
            cv2.imshow("Binaria", binary)
            cv2.imshow("Bordes", edges)
            cv2.imshow("Gris", gray)

            if red_detection["enabled"]:
                red_mask = detect_red(
                    frame,
                    vision_config
                )

                cv2.imshow("Rojo", cv2.bitwise_or(red_mask, edges))

            elapsed = time.time() - start
            wait_time = max(1, int(1000 / fps_limit - elapsed * 10000))         

            if cv2.waitKey(wait_time) & 0xFF == ord('q'):
                break
finally:
    cv2.destroyAllWindows()
