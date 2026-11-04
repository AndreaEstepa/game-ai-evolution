import sys
if sys.prefix == '/usr':
    sys.real_prefix = sys.prefix
    sys.prefix = sys.exec_prefix = '/media/pegaso/4C22A6E222A6D06E2/I.Computadores/Robótica/Robotics/ros2_ws/install/cartpole_pkg'
