import os
import launch
from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
from webots_ros2_driver.webots_launcher import WebotsLauncher
from webots_ros2_driver.webots_controller import WebotsController

def generate_launch_description():
    #se obtiene la ruta del mundo webot
    pkg_dir = get_package_share_directory('cartpole_pkg')
    world_path = os.path.join(pkg_dir, 'world', 'cartpole_world.wbt')
    webots = WebotsLauncher(
        world=world_path
    )
    
    cartpole_driver = WebotsController(
        robot_name='pole_robot',
        parameters=[
            {'use_sim_time': True}
        ]
    )
    
    cartpole_controller_node = Node(
        package='cartpole_pkg',
        executable='cartpole_controller',
        name='cartpole_controller',
        output='screen',
        parameters=[{'use_sim_time': True}]
    )

    return LaunchDescription([
        webots,
        cartpole_driver,
        cartpole_controller_node,
        launch.actions.RegisterEventHandler(
            event_handler=launch.event_handlers.OnProcessExit(
                target_action=webots,
                on_exit=[launch.actions.EmitEvent(event=launch.events.Shutdown())],
            )
        )
    ])
