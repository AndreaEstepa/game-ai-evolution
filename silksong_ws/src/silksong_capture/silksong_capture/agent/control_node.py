import ctypes
import json
import sys

import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, String


KEY_CODES = {
    "left": 0x25,
    "right": 0x27,
    "up": 0x26,
    "down": 0x28,
    "jump": 0x5A,
    "attack": 0x58,
    "dash": 0x43,
    "heal": 0x44,
    "interact": 0x45,
    "escape": 0x1B,
}


def read_buttons(message_text):
    """
    Convierte el texto JSON recibido en una lista de botonessss
    """
    try:
        message = json.loads(message_text)
    except (json.JSONDecodeError, TypeError):
        return []

    if not isinstance(message, dict):
        return []

    buttons = message.get("buttons", [])
    if not isinstance(buttons, list):
        return []

    result = []
    for button in buttons:
        if button in KEY_CODES and button not in result:
            result.append(button)
    return result


class GameControl(Node):
    """
    Convierte las acciones de /agent/action en teclas y los envia eal juego
    """
    def __init__(self):
        super().__init__("game_control")

        self.declare_parameter("reset_keys", [])
        self.reset_keys = list(
            self.get_parameter("reset_keys").value
        )

        self.active_keys = set()
        self.action_subscription = self.create_subscription(
            String,
            "/agent/action",
            self.on_action,
            10,
        )
        self.reset_subscription = self.create_subscription(
            Bool,
            "/agent/reset_episode",
            self.on_reset,
            10,
        )

        self.get_logger().info(
            "Control preparado "
            "Teclas defecto: flechas, Z, X, C, D y E"
        )

    def press_key(self, key_name, hold_seconds=0.08):
        if sys.platform != "win32":
            self.get_logger().warning("Las teclas solo se enviaran en Windows")
            return
        key_code = KEY_CODES.get(key_name)
        if key_code is None:
            return
        ctypes.windll.user32.keybd_event(key_code, 0, 0, 0)
        ctypes.windll.user32.keybd_event(key_code, 0, 2, 0)

    def on_action(self, message):
        buttons = read_buttons(message.data)
        new_keys = set(buttons)

        for key_name in self.active_keys - new_keys:
            if sys.platform == "win32":
                key_code = KEY_CODES[key_name]
                ctypes.windll.user32.keybd_event(key_code, 0, 2, 0)
        for key_name in new_keys - self.active_keys:
            if sys.platform == "win32":
                key_code = KEY_CODES[key_name]
                ctypes.windll.user32.keybd_event(key_code, 0, 0, 0)
        self.active_keys = new_keys

    def on_reset(self, message):
        if not message.data:
            return
        for key_name in self.reset_keys:
            if key_name in KEY_CODES:
                self.press_key(key_name)
        self.active_keys.clear()

    def stop_keys(self):
        if sys.platform != "win32":
            return
        for key_name in self.active_keys:
            key_code = KEY_CODES[key_name]
            ctypes.windll.user32.keybd_event(key_code, 0, 2, 0)
        self.active_keys.clear()

def main(args=None):
    rclpy.init(args=args)
    node = GameControl()
    try:
        rclpy.spin(node)
    finally:
        node.stop_keys()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == "__main__":
    main()