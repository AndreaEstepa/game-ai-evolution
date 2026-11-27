FROM docker.io/ros:lyrical

RUN apt-get update
RUN DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    python3-colcon-common-extensions \
    python3-mss \
    python3-numpy \
    python3-opencv \
    ros-lyrical-ament-index-python \
    ros-lyrical-cv-bridge \
    ros-lyrical-rclpy \
    ros-lyrical-rqt-image-view \
    ros-lyrical-sensor-msgs \
    ros-lyrical-std-msgs
RUN rm -rf /var/lib/apt/lists/*

WORKDIR /workspace
COPY ./entrypoint.sh /workspace/entrypoint.sh
RUN chmod 555 /workspace/entrypoint.sh

WORKDIR /workspace/project
COPY ./silksong_ws /workspace/project

ENTRYPOINT ["/workspace/entrypoint.sh"]
