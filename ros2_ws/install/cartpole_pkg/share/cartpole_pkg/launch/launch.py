import os
import launch
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
from webots_ros2_driver.webots_launcher import WebotsLauncher
from webots_ros2_driver.webots_controller import WebotsController
from webots_ros2_driver.wait_for_controller_connection import WaitForControllerConnection


def generate_launch_description():
    pkg_dir = get_package_share_directory('cartpole_pkg')
    world_path = os.path.join(pkg_dir, 'world', 'cartpole_world.wbt')
    use_sim_time = LaunchConfiguration('use_sim_time', default=True)

    webots = WebotsLauncher(
        world=world_path,
        ros2_supervisor=True,
    )

    cartpole_driver = WebotsController(
        robot_name='pole_robot',
        parameters=[
            {'robot_description': '<robot name=""><link name=""/></robot>'},
            {'use_sim_time': use_sim_time},
            {'set_robot_state_publisher': True}
        ],
        respawn=True,
    )

    cartpole_controller_node = Node(
        package='cartpole_pkg',
        executable='cartpole_controller',
        name='cartpole_controller',
        output='screen',
        parameters=[{'use_sim_time': use_sim_time}]
    )

    waiting_node = WaitForControllerConnection(
        target_driver=cartpole_driver,
        nodes_to_start=[cartpole_controller_node]
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='true',
            description='If true, use the Webots simulation clock.'
        ),
        webots,
        webots._supervisor,
        cartpole_driver,
        waiting_node,
        launch.actions.RegisterEventHandler(
            event_handler=launch.event_handlers.OnProcessExit(
                target_action=webots,
                on_exit=[launch.actions.EmitEvent(event=launch.events.Shutdown())],
            )
        )
    ])
