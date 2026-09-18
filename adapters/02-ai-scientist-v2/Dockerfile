# Runtime image for framework 02 (AI-Scientist-v2). Shared by ALL 02 topics
# (arc/babylm/psydef/tdc/topic2/gave2/mcar all point here), so it must serve
# both CPU-only topics (ARC estimator/scorer are numpy) AND GPU training
# (babylm 02 runs with --gpus all and trains a language model).
#
# WHY THIS RECIPE (two facts, both verified):
# 1. Upstream SakanaAI/AI-Scientist-v2 (pinned 96bd516) ships NO Dockerfile
#    (GitHub contents API) -- the recurring "Dockerfile not found" in
#    build_docker.sh. Version-controlled here so the image is reproducible.
# 2. launch_scientist_bfts.py hard-imports torch, and babylm needs REAL GPU
#    training on this host's RTX PRO 5000 Blackwell (sm_120 / CUDA 13.x).
#    A pip CPU/stock CUDA torch does NOT support sm_120 (same trap hit on 01).
#    So we base on the NGC-25.11 image whose torch is compiled for sm_120
#    (verified: torch 2.10 nv25.11, torch.cuda.get_arch_list() includes
#    sm_120/compute_120, a real cuda matmul succeeds). We do NOT reinstall
#    torch here -- that would clobber the sm_120 build.
#
# The framework source is mounted in at run time by the wrapper.
FROM dawei-claude-image:blackwell

USER root
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

# 02's own deps (no torch in the list). legacy-resolver avoids the pip
# backtracking blow-up seen with the 2024+ resolver on this set.
COPY requirements.txt /tmp/requirements.txt
RUN pip install --use-deprecated=legacy-resolver -r /tmp/requirements.txt

# BFTS agent experiment code commonly uses these; keep them explicit.
RUN pip install --use-deprecated=legacy-resolver scikit-learn scipy

WORKDIR /workspace
ENTRYPOINT []
CMD ["/bin/bash"]
