
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
from std_msgs.msg import String

from .image_processor import detect_red, process_image, reduce_resolution

CONFIG_PATH = Path(get_package_share_directory("silksong_capture")) / "config" / "config.json"
TEMPLATES_DIR = Path(get_package_share_directory("silksong_capture")) / "templates"

HORNET_TEMPLATE_PATHS = {
    "color": {
        "R": TEMPLATES_DIR / "standR.png",
        "L": TEMPLATES_DIR / "standL.png",
    },
    "edges_or_red": {
        "R": TEMPLATES_DIR / "standBinR.png",
        "L": TEMPLATES_DIR / "standBinL.png",
    },
}
FLOWER_TEMPLATE_PATHS = {
    "color": TEMPLATES_DIR / "flower.png",
    "edges_or_red": TEMPLATES_DIR / "flowerBin.png",
    "red": TEMPLATES_DIR / "flowerRed.png",
}
COMBINED_FLOWER_TEMPLATE_PATHS = {
    "color": TEMPLATES_DIR / "flower.png",
    "edges": TEMPLATES_DIR / "flowerBin.png",
    "red": TEMPLATES_DIR / "flowerRed.png",
}


def load_template(path):
    if not path.is_file():
        raise FileNotFoundError(f"Plantilla no encontrada: {path}")
    template = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if template is None:
        raise RuntimeError(f"No se pudo cargar la plantilla: {path}")
    return template


def resize_template(template, capture_region, vision_config):
    if template is None:
        return None
    template_width = max(
        1,
        int(template.shape[1] * vision_config["resize_width"] / capture_region["width"]),
    )
    template_height = max(
        1,
        int(template.shape[0] * vision_config["resize_height"] / capture_region["height"]),
    )
    return cv2.resize(
        template,
        (template_width, template_height),
        interpolation=cv2.INTER_AREA,
    )


def match_template(source, template, threshold):
    if source is None or template is None:
        return []

    source_gray = (
        source if len(source.shape) == 2
        else cv2.cvtColor(source, cv2.COLOR_BGR2GRAY)
    )
    template_gray = (
        template if len(template.shape) == 2
        else cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
    )
    if (
        template_gray.shape[1] >= source_gray.shape[1]
        or template_gray.shape[0] >= source_gray.shape[0]
    ):
        return []

    result = cv2.matchTemplate(source_gray, template_gray, cv2.TM_CCOEFF_NORMED)
    locations = np.argwhere(result >= threshold)
    return [
        (
            int(x),
            int(y),
            template_gray.shape[1],
            template_gray.shape[0],
            float(result[y, x]),
        )
        for y, x in locations
    ]


def suppress_overlaps(matches, overlap_threshold=0.4):
    if not matches:
        return []

    matches = sorted(matches, key=lambda match: match[4], reverse=True)
    kept = []
    for candidate in matches:
        cx, cy, cw, ch, candidate_score, _ = candidate
        keep = True
        for match in kept:
            x, y, w, h, _, _ = match
            intersection_x = max(0, min(cx + cw, x + w) - max(cx, x))
            intersection_y = max(0, min(cy + ch, y + h) - max(cy, y))
            intersection_area = intersection_x * intersection_y
            union_area = cw * ch + w * h - intersection_area
            iou = intersection_area / union_area if union_area > 0 else 0.0
            if iou >= overlap_threshold:
                keep = False
                break
        if keep:
            kept.append(candidate)
    return kept


def select_best_match(matches, previous_center, temporal_priority, distance_scale):
    if not matches:
        return []
    if previous_center is None or temporal_priority == 0.0:
        return [max(matches, key=lambda match: match[4])]

    confidence_weight = 1.0 - temporal_priority
    ranked_matches = []
    for match in matches:
        x, y, width, height, confidence, orientation = match
        center_x = x + width / 2.0
        center_y = y + height / 2.0
        distance = float(np.hypot(
            center_x - previous_center[0],
            center_y - previous_center[1],
        ))
        proximity = max(0.0, 1.0 - distance / distance_scale)
        final_score = confidence * confidence_weight + proximity * temporal_priority
        ranked_matches.append((final_score, match))
    return [max(ranked_matches, key=lambda item: item[0])[1]]


def intersection_over_union(match_a, match_b):
    ax, ay, aw, ah, _ = match_a
    bx, by, bw, bh, _ = match_b
    intersection_x = max(0, min(ax + aw, bx + bw) - max(ax, bx))
    intersection_y = max(0, min(ay + ah, by + bh) - max(ay, by))
    intersection_area = intersection_x * intersection_y
    union_area = aw * ah + bw * bh - intersection_area
    return intersection_area / union_area if union_area > 0 else 0.0


def combine_flower_matches(match_groups, weights, overlap_threshold, min_score):
    red_matches = match_groups.get("red", [])
    combined = []
    for red_match in red_matches:
        matched_groups = {"red": red_match}
        for system in ("color", "edges"):
            overlapping = [
                match
                for match in match_groups.get(system, [])
                if intersection_over_union(red_match, match) >= overlap_threshold
            ]
            if overlapping:
                matched_groups[system] = max(overlapping, key=lambda match: match[4])

        if len(matched_groups) < 2:
            continue
        weight_sum = sum(weights[system] for system in matched_groups if weights[system] > 0)
        if weight_sum <= 0:
            continue

        totals = [0.0, 0.0, 0.0, 0.0, 0.0]
        for system, match in matched_groups.items():
            x, y, width, height, score = match
            weight = weights[system]
            if weight <= 0:
                continue
            totals[0] += x * weight
            totals[1] += y * weight
            totals[2] += width * weight
            totals[3] += height * weight
            totals[4] += score * weight
        final_score = float(totals[4] / weight_sum)
        if final_score >= min_score:
            combined.append((
                int(round(totals[0] / weight_sum)),
                int(round(totals[1] / weight_sum)),
                int(round(totals[2] / weight_sum)),
                int(round(totals[3] / weight_sum)),
                final_score,
            ))
    return suppress_overlaps([
        (x, y, width, height, score, "F")
        for x, y, width, height, score in combined
    ])


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
        self.screen_publisher = self.create_publisher(Image, "/vision/screen", 10)
        self.detections_publisher_ = self.create_publisher(String, "/vision/detections", 10)
        self.bridge = CvBridge()
        if self.fps_limit <= 0:
            raise ValueError("fps_limit debe ser mayor que 0")
        self.previous_center = None
        self._load_detection_config()
        self._load_templates()
        self.timer = self.create_timer(1.0 / float(self.fps_limit), self.publish_vision)

        self.sct = MSS()
        self.monitor = self.sct.monitors[self.monitor_id]

        self.get_logger().info(f"Captura iniciada en monitor {self.monitor_id}")

    def _load_detection_config(self):
        vision = self.vision_config
        self.hornet_threshold = float(vision["hornet_threshold"])
        self.hornet_search_mode = vision["hornet_search_mode"]
        self.temporal_priority = float(vision["temporal_priority"])
        self.temporal_distance_scale = float(vision["temporal_distance_scale"])
        self.detect_flowers = bool(vision["detect_flowers"])
        self.flower_threshold = float(vision["flower_threshold"])
        self.flower_search_mode = vision["flower_search_mode"]
        self.combined_weights = vision.get(
            "combined_flower_weights",
            {"color": 1.0, "edges": 1.0, "red": 1.0},
        )
        self.combined_overlap_threshold = float(
            vision.get("combined_flower_overlap", 0.3)
        )
        self.combined_min_score = float(
            vision.get("combined_flower_min_score", 0.5)
        )

        if self.hornet_search_mode not in HORNET_TEMPLATE_PATHS:
            raise ValueError(
                f"Modo de busqueda no valido: {self.hornet_search_mode}"
            )
        if not 0.0 <= self.temporal_priority <= 1.0:
            raise ValueError("temporal_priority debe estar entre 0.0 y 1.0")
        if self.temporal_distance_scale <= 0.0:
            raise ValueError("temporal_distance_scale debe ser mayor que 0")

        supported_flower_modes = set(FLOWER_TEMPLATE_PATHS) | {"combined"}
        if self.flower_search_mode not in supported_flower_modes:
            raise ValueError(
                f"Modo de flores no valido: {self.flower_search_mode}"
            )

    def _load_templates(self):
        self.hornet_templates = {}
        for orientation, template_path in HORNET_TEMPLATE_PATHS[
            self.hornet_search_mode
        ].items():
            template = resize_template(
                load_template(template_path),
                self.region,
                self.vision_config,
            )
            if template is not None:
                self.hornet_templates[orientation] = template

        self.flower_template = None
        self.combined_flower_templates = {}
        if self.detect_flowers:
            if self.flower_search_mode == "combined":
                for system, template_path in COMBINED_FLOWER_TEMPLATE_PATHS.items():
                    template = resize_template(
                        load_template(template_path),
                        self.region,
                        self.vision_config,
                    )
                    if template is not None:
                        self.combined_flower_templates[system] = template
            else:
                self.flower_template = resize_template(
                    load_template(FLOWER_TEMPLATE_PATHS[self.flower_search_mode]),
                    self.region,
                    self.vision_config,
                )

    def publish_vision(self):
        region = {
            "left": self.monitor["left"] + self.region["left"],
            "top": self.monitor["top"] + self.region["top"],
            "width": self.region["width"],
            "height": self.region["height"],
        }

        screenshot = self.sct.grab(region)
        frame = np.array(screenshot)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
        processed_screen = reduce_resolution(frame, self.vision_config)

        screen_msg = self.bridge.cv2_to_imgmsg(processed_screen, encoding="bgr8")
        screen_msg.header.stamp = self.get_clock().now().to_msg()
        screen_msg.header.frame_id = "game_screen"
        self.screen_publisher.publish(screen_msg)

        binary, edges, gray = process_image(frame, self.vision_config)
        processed = reduce_resolution(frame, self.vision_config)

        red_mask = np.zeros_like(gray)
        if self.vision_config["red_detection"]["enabled"]:
            red_mask = detect_red(frame, self.vision_config)
        red_mask = cv2.bitwise_or(red_mask, edges)

        red_msg = self.bridge.cv2_to_imgmsg(red_mask, encoding="mono8")
        red_msg.header.stamp = self.get_clock().now().to_msg()
        red_msg.header.frame_id = "screen_red_mask"
        self.publisher_.publish(red_msg)

        hornet_matches = []
        if self.hornet_search_mode == "color":
            hornet_source = processed
        else:
            raw_red_mask = (
                detect_red(frame, self.vision_config)
                if self.vision_config["red_detection"]["enabled"]
                else np.zeros_like(gray)
            )
            hornet_source = cv2.bitwise_or(edges, raw_red_mask)

        for orientation, template in self.hornet_templates.items():
            orientation_matches = match_template(
                hornet_source,
                template,
                self.hornet_threshold,
            )
            hornet_matches.extend(
                (x, y, width, height, score, orientation)
                for x, y, width, height, score in orientation_matches
            )

        hornet_matches = suppress_overlaps(hornet_matches)
        hornet_matches = select_best_match(
            hornet_matches,
            self.previous_center,
            self.temporal_priority,
            self.temporal_distance_scale,
        )
        if hornet_matches:
            x, y, width, height, _, _ = hornet_matches[0]
            self.previous_center = (x + width / 2.0, y + height / 2.0)

        flower_matches = []
        raw_red_mask = (
            detect_red(frame, self.vision_config)
            if self.vision_config["red_detection"]["enabled"]
            else np.zeros_like(gray)
        )
        if self.detect_flowers and self.flower_template is not None:
            if self.flower_search_mode == "color":
                flower_source = processed
            elif self.flower_search_mode == "edges_or_red":
                flower_source = cv2.bitwise_or(edges, raw_red_mask)
            else:
                flower_source = raw_red_mask
            flower_matches = match_template(
                flower_source,
                self.flower_template,
                self.flower_threshold,
            )
            flower_matches = suppress_overlaps([
                (x, y, width, height, score, "F")
                for x, y, width, height, score in flower_matches
            ])
            flower_matches = [
                (x, y, width, height, score)
                for x, y, width, height, score, _ in flower_matches
            ]
        elif (
            self.detect_flowers
            and self.flower_search_mode == "combined"
            and len(self.combined_flower_templates) == 3
        ):
            match_groups = {
                "color": match_template(
                    processed,
                    self.combined_flower_templates["color"],
                    self.flower_threshold,
                ),
                "edges": match_template(
                    edges,
                    self.combined_flower_templates["edges"],
                    self.flower_threshold,
                ),
                "red": match_template(
                    raw_red_mask,
                    self.combined_flower_templates["red"],
                    self.flower_threshold,
                ),
            }
            combined = combine_flower_matches(
                match_groups,
                self.combined_weights,
                self.combined_overlap_threshold,
                self.combined_min_score,
            )
            flower_matches = [
                (x, y, width, height, score)
                for x, y, width, height, score, _ in combined
            ]

        hornet_data = None
        if hornet_matches:
            x, y, width, height, score, orientation = hornet_matches[0]
            hornet_data = {
                "x": int(x),
                "y": int(y),
                "width": int(width),
                "height": int(height),
                "center": {
                    "x": int(round(x + width / 2.0)),
                    "y": int(round(y + height / 2.0)),
                },
                "orientation": orientation,
                "score": round(float(score), 6),
            }

        detections = {
            "hornet": hornet_data,
            "flowers": [
                {
                    "x": int(x),
                    "y": int(y),
                    "width": int(width),
                    "height": int(height),
                    "center": {
                        "x": int(round(x + width / 2.0)),
                        "y": int(round(y + height / 2.0)),
                    },
                    "score": round(float(score), 6),
                }
                for x, y, width, height, score in flower_matches
            ],
        }
        detections_msg = String()
        detections_msg.data = json.dumps(detections, ensure_ascii=False)
        self.detections_publisher_.publish(detections_msg)


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
