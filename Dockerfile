FROM docker.io/ros:lyrical

RUN apt-get update
RUN DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    python3-colcon-common-extensions \
    python3-numpy \
    python3-opencv \
    python3-pip \
    ros-lyrical-ament-index-python \
    ros-lyrical-cv-bridge \
    ros-lyrical-rclpy \
    ros-lyrical-rqt-image-view \
    ros-lyrical-sensor-msgs \
    ros-lyrical-std-msgs
RUN rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --break-system-packages --no-cache-dir mss

WORKDIR /workspace/project
COPY --chmod=555 ./entrypoint.sh /workspace/entrypoint.sh
COPY ./silksong_ws/ .

ENTRYPOINT ["/workspace/entrypoint.sh"]
