FROM --platform=linux/amd64 pytorch/pytorch:2.13.0-cuda12.6-cudnn9-runtime AS example_algorithm_amd64
# Use a 'large' base container to show-case how to load pytorch and use the GPU (when enabled)
#
# Note on image selection:
#   - cuda12.6 is required for the T4 GPU instances used on Grand Challenge
#   - The 'runtime' image is sufficient for inference; 'devel' is only needed if you
#     compile custom CUDA kernels

# Ensures that Python output to stdout/stderr is not buffered: prevents missing information when terminating
ENV PYTHONUNBUFFERED=1

RUN groupadd -r user && useradd -m --no-log-init -r -g user user
USER user

WORKDIR /opt/app

# Create a virtualenv that inherits the system-site-packages (i.e. torch, cuda libs)
# This avoids PEP 668 externally-managed-environment errors on newer PyTorch images
# --without-pip is needed because the base image does not ship ensurepip;
# pip is inherited from system-site-packages instead.
RUN python -m venv --system-site-packages --without-pip /home/user/venv
# "Activate" the venv for all subsequent RUN, CMD, and ENTRYPOINT instructions.
# Each RUN is a fresh shell so source-based activation doesn't persist between layers.
ENV PATH="/home/user/venv/bin:$PATH"

COPY --chown=user:user requirements.txt /opt/app/

# You can add any Python dependencies to requirements.txt
RUN python -m pip install \
    --no-cache-dir \
    --no-color \
    --requirement /opt/app/requirements.txt

COPY --chown=user:user app.py /opt/app/
COPY --chown=user:user inference.py /opt/app/

# This label is required — Grand Challenge uses it to detect that the container
# implements the invoke API. Without it, the examples provided in this starter kit will not work.
LABEL org.grand-challenge.api-method="invoke"

ENTRYPOINT ["python", "app.py"]
