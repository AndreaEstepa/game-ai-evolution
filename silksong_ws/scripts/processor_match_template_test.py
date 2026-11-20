import json
import time
from pathlib import Path

import cv2
import numpy as np
from mss import MSS

from image_processor import detect_red, process_image, reduce_resolution


BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config.json"
HORNET_TEMPLATE_PATHS = {
    "color": {
        "R": BASE_DIR / "templates" / "standR.png",
        "L": BASE_DIR / "templates" / "standL.png",
    },
    "edges_or_red": {
        "R": BASE_DIR / "templates" / "standBinR.png",
        "L": BASE_DIR / "templates" / "standBinL.png",
    },
}
FLOWER_TEMPLATE_PATHS = {
    "color": BASE_DIR / "templates" / "flower.png",
    "edges_or_red": BASE_DIR / "templates" / "flowerBin.png",
    "red": BASE_DIR / "templates" / "flowerRed.png",
}
COMBINED_FLOWER_TEMPLATE_PATHS = {
    "color": BASE_DIR / "templates" / "flower.png",
    "edges": BASE_DIR / "templates" / "flowerBin.png",
    "red": BASE_DIR / "templates" / "flowerRed.png",
}


def load_template(path):
    if not path.is_file():
        print(f"Plantilla no encontrada: {path}")
        return None

    template = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if template is None:
        print(f"No se pudo cargar la plantilla: {path}")
        return None

    print(f"Plantilla cargada: {path}")
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
    resized = cv2.resize(
        template,
        (template_width, template_height),
        interpolation=cv2.INTER_AREA,
    )
    return resized


def match_template(source, template, threshold):
    if source is None or template is None:
        return []

    if len(source.shape) == 2:
        source_gray = source
    else:
        source_gray = cv2.cvtColor(source, cv2.COLOR_BGR2GRAY)

    if len(template.shape) == 2:
        template_gray = template
    else:
        template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)

    if (
        template_gray.shape[1] >= source_gray.shape[1]
        or template_gray.shape[0] >= source_gray.shape[0]
    ):
        return []

    result = cv2.matchTemplate(source_gray, template_gray, cv2.TM_CCOEFF_NORMED)
    locations = np.argwhere(result >= threshold)

    matches = []
    for y, x in locations:
        matches.append(
            (int(x), int(y), template_gray.shape[1], template_gray.shape[0],
             float(result[y, x]))
        )
    return matches


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
            candidate_area = cw * ch
            kept_area = w * h
            union_area = candidate_area + kept_area - intersection_area
            iou = intersection_area / union_area if union_area > 0 else 0.0

            if iou >= overlap_threshold:
                keep = False
                break

        if keep:
            kept.append(candidate)

    return kept


def draw_matches(frame, matches, color):
    for x, y, width, height, score, orientation in matches:
        cv2.rectangle(frame, (x, y), (x + width, y + height), color, 2)
        cv2.putText(
            frame,
            f"Hornet {orientation}: {score:.2f}",
            (x, max(y - 8, 12)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            color,
            1,
            cv2.LINE_AA,
        )


def draw_flower_matches(frame, matches, color):
    for x, y, width, height, score in matches:
        cv2.rectangle(frame, (x, y), (x + width, y + height), color, 2)
        cv2.putText(
            frame,
            f"Flor: {score:.2f}",
            (x, max(y - 8, 12)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            color,
            1,
            cv2.LINE_AA,
        )


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
        distance = float(
            np.hypot(
                center_x - previous_center[0],
                center_y - previous_center[1],
            )
        )
        proximity = max(0.0, 1.0 - distance / distance_scale)
        final_score = (
            confidence * confidence_weight
            + proximity * temporal_priority
        )
        ranked_matches.append((final_score, match))

    best_match = max(ranked_matches, key=lambda item: item[0])[1]
    return [best_match]


def intersection_over_union(match_a, match_b):
    ax, ay, aw, ah, _ = match_a
    bx, by, bw, bh, _ = match_b
    intersection_x = max(0, min(ax + aw, bx + bw) - max(ax, bx))
    intersection_y = max(0, min(ay + ah, by + bh) - max(ay, by))
    intersection_area = intersection_x * intersection_y
    union_area = aw * ah + bw * bh - intersection_area
    return intersection_area / union_area if union_area > 0 else 0.0


def combine_flower_matches(
    match_groups,
    weights,
    overlap_threshold,
    min_score,
):
    red_matches = match_groups.get("red", [])
    if not red_matches:
        return []

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
                matched_groups[system] = max(
                    overlapping,
                    key=lambda match: match[4],
                )

        if len(matched_groups) < 2:
            continue

        weight_sum = sum(
            weights[system]
            for system in matched_groups
            if weights[system] > 0.0
        )
        if weight_sum <= 0.0:
            continue

        weighted_x = 0.0
        weighted_y = 0.0
        weighted_width = 0.0
        weighted_height = 0.0
        weighted_score = 0.0

        for system, match in matched_groups.items():
            x, y, width, height, score = match
            weight = weights[system]
            if weight <= 0.0:
                continue
            weighted_x += x * weight
            weighted_y += y * weight
            weighted_width += width * weight
            weighted_height += height * weight
            weighted_score += score * weight

        final_score = float(weighted_score / weight_sum)
        if final_score < min_score:
            continue

        combined.append(
            (
                int(round(weighted_x / weight_sum)),
                int(round(weighted_y / weight_sum)),
                int(round(weighted_width / weight_sum)),
                int(round(weighted_height / weight_sum)),
                final_score,
            )
        )

    return suppress_overlaps(
        [
            (x, y, width, height, score, "F")
            for x, y, width, height, score in combined
        ]
    )


def main():
    with open(CONFIG_PATH, "r", encoding="utf-8") as file:
        config = json.load(file)

    monitor_id = config["monitor"]
    capture_region = config["region"]
    fps_limit = config["fps_limit"]
    vision_config = config["vision"]
    red_detection = vision_config["red_detection"]
    hornet_threshold = vision_config["hornet_threshold"]
    hornet_search_mode = vision_config["hornet_search_mode"]
    temporal_priority = float(vision_config["temporal_priority"])
    temporal_distance_scale = float(vision_config["temporal_distance_scale"])
    detect_flowers = bool(vision_config["detect_flowers"])
    flower_threshold = float(vision_config["flower_threshold"])
    flower_search_mode = vision_config["flower_search_mode"]
    combined_weights = vision_config.get(
        "combined_flower_weights",
        {"color": 1.0, "edges": 1.0, "red": 1.0},
    )
    combined_overlap_threshold = float(
        vision_config.get("combined_flower_overlap", 0.3)
    )
    combined_min_score = float(
        vision_config.get("combined_flower_min_score", 0.5)
    )

    if not 0.0 <= temporal_priority <= 1.0:
        raise ValueError("temporal_priority debe estar entre 0.0 y 1.0")
    if temporal_distance_scale <= 0.0:
        raise ValueError("temporal_distance_scale debe ser mayor que 0")

    if hornet_search_mode not in HORNET_TEMPLATE_PATHS:
        supported_modes = ", ".join(HORNET_TEMPLATE_PATHS)
        raise ValueError(
            f"Modo de busqueda no valido: {hornet_search_mode}. "
            f"Modos admitidos: {supported_modes}"
        )

    if not 0.0 <= flower_threshold <= 1.0:
        raise ValueError("flower_threshold debe estar entre 0.0 y 1.0")

    supported_flower_modes = set(FLOWER_TEMPLATE_PATHS) | {"combined"}
    if flower_search_mode not in supported_flower_modes:
        supported_modes = ", ".join(sorted(supported_flower_modes))
        raise ValueError(
            f"Modo de flores no valido: {flower_search_mode}. "
            f"Modos admitidos: {supported_modes}"
        )

    if not 0.0 <= combined_overlap_threshold <= 1.0:
        raise ValueError(
            "combined_flower_overlap debe estar entre 0.0 y 1.0"
        )
    if not 0.0 <= combined_min_score <= 1.0:
        raise ValueError(
            "combined_flower_min_score debe estar entre 0.0 y 1.0"
        )

    normalized_combined_weights = {}
    for system in ("color", "edges", "red"):
        weight = float(combined_weights.get(system, 0.0))
        if weight < 0.0:
            raise ValueError(
                f"combined_flower_weights.{system} debe ser mayor o igual que 0"
            )
        normalized_combined_weights[system] = weight

    if sum(normalized_combined_weights.values()) <= 0.0:
        raise ValueError(
            "combined_flower_weights debe tener al menos un peso mayor que 0"
        )

    hornet_templates = {}
    for orientation, template_path in HORNET_TEMPLATE_PATHS[hornet_search_mode].items():
        template = load_template(template_path)
        template = resize_template(template, capture_region, vision_config)
        if template is not None:
            hornet_templates[orientation] = template
            print(
                f"Plantilla {orientation} adaptada a la resolucion procesada: "
                f"{template.shape[1]}x{template.shape[0]}"
            )

    flower_template = None
    combined_flower_templates = {}
    if detect_flowers:
        if flower_search_mode == "combined":
            for system, template_path in COMBINED_FLOWER_TEMPLATE_PATHS.items():
                template = load_template(template_path)
                template = resize_template(template, capture_region, vision_config)
                if template is not None:
                    combined_flower_templates[system] = template
                    print(
                        f"Plantilla combinada {system} adaptada a la resolucion "
                        f"procesada: {template.shape[1]}x{template.shape[0]}"
                    )
        else:
            flower_template = load_template(
                FLOWER_TEMPLATE_PATHS[flower_search_mode]
            )
            flower_template = resize_template(
                flower_template,
                capture_region,
                vision_config,
            )

    cv2.namedWindow("Original", cv2.WINDOW_NORMAL)
    cv2.namedWindow("Binaria", cv2.WINDOW_NORMAL)
    cv2.namedWindow("Bordes", cv2.WINDOW_NORMAL)
    cv2.namedWindow("Gris", cv2.WINDOW_NORMAL)
    cv2.namedWindow("Rojo", cv2.WINDOW_NORMAL)
    cv2.namedWindow("Mascara roja", cv2.WINDOW_NORMAL)
    cv2.namedWindow("Coincidencias", cv2.WINDOW_NORMAL)
    previous_center = None

    try:
        with MSS() as sct:
            if monitor_id >= len(sct.monitors):
                print("Monitores detectados:")
                for i, monitor in enumerate(sct.monitors):
                    print(i, monitor)
                raise ValueError(f"El monitor {monitor_id} no existe")

            monitor = sct.monitors[monitor_id]
            print("Iniciando captura...")

            while True:
                start = time.time()
                region = {
                    "left": monitor["left"] + capture_region["left"],
                    "top": monitor["top"] + capture_region["top"],
                    "width": capture_region["width"],
                    "height": capture_region["height"],
                }

                screenshot = sct.grab(region)
                frame = np.array(screenshot)
                frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

                binary, edges, gray = process_image(frame, vision_config)
                processed = reduce_resolution(frame, vision_config)

                red_mask = np.zeros_like(gray)
                if red_detection["enabled"]:
                    red_mask = detect_red(frame, vision_config)

                if hornet_search_mode == "color":
                    search_source = processed
                elif hornet_search_mode == "edges_or_red":
                    search_source = cv2.bitwise_or(edges, red_mask)
                else:
                    raise ValueError(
                        f"Modo de busqueda no implementado: {hornet_search_mode}"
                    )

                if flower_search_mode == "color":
                    flower_search_source = processed
                elif flower_search_mode == "edges_or_red":
                    flower_search_source = cv2.bitwise_or(edges, red_mask)
                elif flower_search_mode == "red":
                    flower_search_source = red_mask
                else:
                    flower_search_source = None

                hornet_matches = []
                for orientation, hornet_template in hornet_templates.items():
                    orientation_matches = match_template(
                        search_source,
                        hornet_template,
                        hornet_threshold,
                    )
                    hornet_matches.extend(
                        (x, y, width, height, score, orientation)
                        for x, y, width, height, score in orientation_matches
                    )

                hornet_matches = suppress_overlaps(hornet_matches)
                hornet_matches = select_best_match(
                    hornet_matches,
                    previous_center,
                    temporal_priority,
                    temporal_distance_scale,
                )

                if hornet_matches:
                    x, y, width, height, _, _ = hornet_matches[0]
                    previous_center = (
                        x + width / 2.0,
                        y + height / 2.0,
                    )

                flower_matches = []
                if detect_flowers and flower_template is not None:
                    flower_matches = match_template(
                        flower_search_source,
                        flower_template,
                        flower_threshold,
                    )
                    flower_matches = suppress_overlaps(
                        [
                            (x, y, width, height, score, "F")
                            for x, y, width, height, score in flower_matches
                        ]
                    )
                    flower_matches = [
                        (x, y, width, height, score)
                        for x, y, width, height, score, _ in flower_matches
                    ]
                elif (
                    detect_flowers
                    and flower_search_mode == "combined"
                    and len(combined_flower_templates) == 3
                ):
                    flower_sources = {
                        "color": processed,
                        "edges": edges,
                        "red": red_mask,
                    }
                    match_groups = {
                        system: match_template(
                            flower_sources[system],
                            combined_flower_templates[system],
                            flower_threshold,
                        )
                        for system in ("color", "edges", "red")
                    }
                    combined_matches = combine_flower_matches(
                        match_groups,
                        normalized_combined_weights,
                        combined_overlap_threshold,
                        combined_min_score,
                    )
                    flower_matches = [
                        (x, y, width, height, score)
                        for x, y, width, height, score, _ in combined_matches
                    ]

                match_frame = processed.copy()
                draw_matches(match_frame, hornet_matches, (255, 0, 0))
                draw_flower_matches(match_frame, flower_matches, (0, 255, 0))

                cv2.imshow("Original", frame)
                cv2.imshow("Binaria", binary)
                cv2.imshow("Bordes", edges)
                cv2.imshow("Gris", gray)
                cv2.imshow("Rojo", cv2.bitwise_or(red_mask, edges))
                cv2.imshow("Mascara roja", red_mask)
                cv2.imshow("Coincidencias", match_frame)

                elapsed = time.time() - start
                wait_time = max(1, int(1000.0 / fps_limit - elapsed * 1000.0))

                if cv2.waitKey(wait_time) & 0xFF == ord("q"):
                    break
    finally:
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
