FROM docker.io/ros:lyrical

RUN apt-get update
RUN DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    libevdev2 \
    openjdk-21-jdk
RUN rm -rf /var/lib/apt/lists/*

RUN mkdir -p /workspace
COPY . /workspace

WORKDIR /workspace

ENTRYPOINT ["/workspace/start.sh"]
