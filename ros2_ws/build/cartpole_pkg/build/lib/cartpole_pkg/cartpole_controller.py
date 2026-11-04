#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, Range
from geometry_msgs.msg import *
from cv_bridge import CvBridge
import numpy as np
import cv2

class CartpoleController(Node):
    def __init__(self):
        super().__init__('cartpole_controller')

		#inicializar el conversor de imágenes de ROS a OpenCV
        self.br = CvBridge()
		#se declaran aqui los subscriptores, es decir, los sensores de proximidad y cámara
        self.subscription_distance = self.create_subscription(Range, '/pole_robot/Distance1', self.distance_callback, 10)
        self.subscription_camera = self.create_subscription(Image, '/pole_robot/camera/image_raw', self.camera_callback, 10)
        #se declara el publicador para así mover por ejemplo las ruedas del robot
        self.publisher_cmd = self.create_publisher(Twist, '/cmd_vel', 10)
        self.get_logger().info('Cartpole Controller iniciado. Escuchando cámara y sensores')

        

    def distance_callback(self, msg):
        #aqui va la logiac para procesar la lectura del sensor de proximidad
        self.get_logger().info('lectura sensor distancia: {msg.range}')
        #aquí iría el algoritmo de control para decidir cúando mover al robot y publicarlo en twist
	    
        
    def camera_callback(self, msg):
        try:
    		#convertimos el mensaje de imagen de ros a opencv
            cv_image = self.br.imgmsg_to_cv2(msg, desired_encoding='bgr8')
            #procesamos la imagen en escala de grises para calcular el brillo a medida que nos acercamos a la pared
            gray_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
            mean_intensity = np.mean(gray_image)
            #estima la distancia con la heuristica, TODO ADAPTARLO
            distance = float(mean_intensity)
            self.get_logger().info('distancia a la pared: {distance:.2f}')
        except Exception as e:
            self.self.get_logger().error('error de imagen: {msg.range}')

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
