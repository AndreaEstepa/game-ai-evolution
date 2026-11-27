#!/usr/bin/env bash

set -e

source /opt/ros/lyrical/setup.bash
cd /workspace/project

colcon build --packages-select silksong_capture
source install/setup.bash

if (($#)); then
    exec "$@"
fi

ros2 run silksong_capture screen_publisher &
publisher_pid=$!

ros2 run silksong_capture evolutionary_agent &
agent_pid=$!

cleanup() {
    kill "${publisher_pid}" "${agent_pid}" 2>/dev/null || true
    wait "${publisher_pid}" "${agent_pid}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

if wait -n "${publisher_pid}" "${agent_pid}"; then
    status=0
else
    status=$?
fi
exit "${status}"
