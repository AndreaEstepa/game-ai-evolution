#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Range
from geometry_msgs.msg import Twist


class CartpoleController(Node):
    def __init__(self):
        super().__init__('cartpole_controller')
        self.declare_parameter('use_sim_time', True)

        self.subscription_distance = self.create_subscription(
            Range,
            '/pole_robot/Distance1',
            self.distance_callback,
            10
        )
        self.publisher_cmd = self.create_publisher(Twist, '/cmd_vel', 10)
        self.get_logger().info('Cartpole Controller iniciado. Esperando conexión con Webots.')

    def distance_callback(self, msg):
        self.get_logger().info(f'lectura sensor distancia: {msg.range}')
        twist = Twist()
        twist.linear.x = 0.0
        twist.angular.z = 0.0
        self.publisher_cmd.publish(twist)


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
