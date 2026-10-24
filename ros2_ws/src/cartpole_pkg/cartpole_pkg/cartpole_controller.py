#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, Range
from geometry_msgs.msg

class CartpoleController(Node):
    def __init__(self):
        super().__init__('cartpole_controller')
        #se declaran aqui los subscriptores, es decir, los sensores de proximidad y cámara
        self.subscription_distance = self.create_subscription(Range, 'cartpole/Distance1', self.distance_callback, 10)
        #se declara el publicador para así mover por ejemplo las ruedas del robot
        self.publisher_cmd = self.create_publisher(Twist, '/cmd_vel', 10)
        self.get_logger().info('Cartpole Controller iniciado')

        def distance_callback(self, msg):
            #aqui va la logiac para procesar la lectura del sensor de proximidad
            self.get_logger().info('lectura sensor distancia: {msg.range}')
            #aquí iría el algoritmo de control para decidir cúando mover al robot y publicarlo en twist

def main(args=None):
    rclpy.init(args=args)
    controller = CartpoleController()
    try:
        rclpy.spin(controller)
    except KeyboardInterrupt:
        pass
    finally:
        controller.destroy_node()
        rclpy.shutdown()
if __name__ == '__main__':
    main()
