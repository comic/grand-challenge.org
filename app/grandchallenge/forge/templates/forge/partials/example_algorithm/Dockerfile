FROM --platform=linux/amd64 pytorch/pytorch:2.9.1-cuda12.6-cudnn9-runtime AS example_algorithm_amd64
# Use a 'large' base container to show-case how to load pytorch and use the GPU (when enabled)

# Ensures that Python output to stdout/stderr is not buffered: prevents missing information when terminating
ENV PYTHONUNBUFFERED=1

RUN groupadd -r user && useradd -m --no-log-init -r -g user user
USER user

WORKDIR /opt/app

COPY --chown=user:user requirements.txt /opt/app/

# You can add any Python dependencies to requirements.txt
RUN python -m pip install \
    --user \
    --no-cache-dir \
    --no-color \
    --requirement /opt/app/requirements.txt

COPY --chown=user:user app.py /opt/app/
COPY --chown=user:user inference.py /opt/app/

# This label is required — Grand Challenge uses it to detect that the container
# implements the invoke API. Without it, the examples provided in this starter kit will not work.
LABEL org.grand-challenge.api-method="invoke"

ENTRYPOINT ["python", "app.py"]
