import os
from glob import glob
from setuptools import setup
package_name = 'cartpole_pkg'
setup(
        name = package_name,
        version='0.0.0'
        packages=[package_name],
        data_files=[('share/ament_index/resource_index/packages', ['resource/' + package_name]), ('share/' + package_name, ['package.xml']),
            (os.path.join('share', package_name, 'launch'), glob(os.path.join('launch', '*'))),
            (os.path.join('share', package_name, 'workd'), glob(os.path.join('world', '*'))),
        ],
        install_requires=['setuptools'],
        zip_safe=True,
        maintainer='andrea',
        maintainer_email='',
        description='Practica robotica - cartpole con webots y ros2',
        license='Apache-2.0',
        test_require=['pytest'],
        entry_points={'console_scripts':['cartpole_controller = cartpole_pkg.cartpole_controller:main',],},
)
