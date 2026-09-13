# Runtime image for framework 02 (AI-Scientist-v2).
#
# Upstream SakanaAI/AI-Scientist-v2 (pinned 96bd516) ships NO Dockerfile
# (verified via GitHub contents API) -- the recurring "Dockerfile not found"
# in build_docker.sh. This recipe is version-controlled here so the image is
# reproducible independent of the clone.
#
# Base: a local python:3.11 research image (evoscientist:runtime-ready) to
# avoid pulling python:3.11-slim from Docker Hub, which is unreachable on this
# host (the earlier build hung for 12min at the FROM pull, never reaching pip;
# host pip itself reaches PyPI fine). 02 is CPU/LLM-bound (no torch/cuda).
# The framework source is mounted in at run time by the wrapper.
FROM evoscientist:runtime-ready

USER root
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
COPY AI-Scientist-v2/requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt
WORKDIR /workspace
ENTRYPOINT []
CMD ["/bin/bash"]
