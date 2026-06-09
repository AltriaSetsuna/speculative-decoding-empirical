# docker run --gpus all --rm -d --privileged --name dcgm_monitor \
#   --entrypoint nv-hostengine \
#   hub.rat.dev/nvidia/dcgm:4.4.2-1-ubuntu22.04 \
#   -n



docker exec dcgm_monitor dcgmi dmon -e 1005 -i 1,5 -d 100 > ./log/eagle3.log