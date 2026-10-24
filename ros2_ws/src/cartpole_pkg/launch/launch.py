import os
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import ExecuteProcess
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    #se obtiene la ruta del mundo webot
    pkg_dir = get_package_share_directory('cartpole_pkg')
    world_path = os.path.join(pkg_dir, 'world', 'cartpole_world.wbt')

    return LaunchDescription([ExecuteProcess(cmd=['webots', world_path], output='screen'),
        Node(package='cartpole_pkg', executable='cartpole_controller', name='cartpole_controller', output='screen')])
