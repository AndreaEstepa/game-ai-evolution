FROM docker.io/ros:lyrical

RUN DEBIAN_FRONTEND=noninteractive apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        python3-colcon-common-extensions \
        python3-mss \
        python3-numpy \
        python3-opencv \
        ros-lyrical-ament-index-python \
        ros-lyrical-cv-bridge \
        ros-lyrical-rclpy \
        ros-lyrical-rqt-image-view \
        ros-lyrical-sensor-msgs \
        ros-lyrical-std-msgs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace/project
COPY --chmod=555 ./entrypoint.sh /workspace/entrypoint.sh
COPY ./silksong_ws/ .

ENTRYPOINT ["/workspace/entrypoint.sh"]
