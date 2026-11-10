
import json
from pathlib import Path

import cv2
import numpy as np
import rclpy
from ament_index_python.packages import get_package_share_directory
from cv_bridge import CvBridge
from mss import MSS
from rclpy.node import Node
from sensor_msgs.msg import Image

from .image_processor import process_image, detect_red

CONFIG_PATH = Path(get_package_share_directory("silksong_capture")) / "config" / "config.json"


class ScreenPublisher(Node):
    def __init__(self):
        super().__init__("screen_publisher")

        with open(CONFIG_PATH, "r", encoding="utf-8") as file:
            config = json.load(file)

        self.monitor_id = config["monitor"]
        self.region = config["region"]
        self.fps_limit = config["fps_limit"]
        self.vision_config = config["vision"]

        self.publisher_ = self.create_publisher(Image, "/vision/red_mask", 10)
        self.bridge = CvBridge()
        if self.fps_limit <= 0:
            raise ValueError("fps_limit debe ser mayor que 0")
        self.timer = self.create_timer(1.0 / float(self.fps_limit), self.publish_red_mask)

        self.sct = MSS()
        self.monitor = self.sct.monitors[self.monitor_id]

        self.get_logger().info(f"Captura iniciada en monitor {self.monitor_id}")

    def publish_red_mask(self):
        region = {
            "left": self.monitor["left"] + self.region["left"],
            "top": self.monitor["top"] + self.region["top"],
            "width": self.region["width"],
            "height": self.region["height"],
        }

        screenshot = self.sct.grab(region)
        frame = np.array(screenshot)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

        red_mask = detect_red(frame, self.vision_config)
        binary, edges, gray = process_image(frame, self.vision_config)

        red_mask = cv2.bitwise_or(red_mask, edges)

        red_msg = self.bridge.cv2_to_imgmsg(red_mask, encoding="mono8")
        red_msg.header.stamp = self.get_clock().now().to_msg()
        red_msg.header.frame_id = "screen_red_mask"
        self.publisher_.publish(red_msg)


def main(args=None):
    rclpy.init(args=args)
    node = ScreenPublisher()

    try:
        rclpy.spin(node)
    finally:
        node.sct.close()
        cv2.destroyAllWindows()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
