###################
#  Base Container #
###################
ARG PYTHON_VERSION

FROM python:${PYTHON_VERSION} as base

# Install system dependencies
RUN apt-get update \
    && apt-get install -y \
        libpng-dev \
        libjpeg-dev \
        libjpeg62-turbo-dev \
        libfreetype6-dev \
        libxft-dev \
        libffi-dev \
        wget \
        gettext \
        libopenslide-dev \
        libvips-dev

# Fetch and install licensee for checking licenses
RUN apt-get install -y ruby2.7 ruby-rugged \
    && gem install licensee -v 9.15.1

# Fetch and install crane for pushing containers
RUN mkdir -p /opt/crane \
    && wget https://github.com/google/go-containerregistry/releases/download/v0.9.0/go-containerregistry_Linux_x86_64.tar.gz -O /opt/crane/src.tar.gz \
    && echo "1d2cf3fac0830dd8e5fb6e2829fdfc304a3d4a0f48f7e1df9ebb7e2921f28803  /opt/crane/src.tar.gz" | shasum -c - || exit 1 \
    && tar -C /opt/crane/ -xzvf /opt/crane/src.tar.gz crane \
    && chmod a+x /opt/crane/crane \
    && mv /opt/crane/crane /usr/local/bin/ \
    && rm -r /opt/crane

# Fetch and install git lfs for github integration
RUN mkdir -p /opt/git-lfs \
    && wget https://github.com/git-lfs/git-lfs/releases/download/v3.0.1/git-lfs-linux-amd64-v3.0.1.tar.gz -O /opt/git-lfs/src.tar.gz \
    && echo "29706bf26d26a4e3ddd0cad02a1d05ff4f332a2fab4ecab3bbffbb000d6a5797  /opt/git-lfs/src.tar.gz" | shasum --algorithm 256 -c - || exit 1 \
    && tar -C /opt/git-lfs/ -xzvf /opt/git-lfs/src.tar.gz \
    && bash /opt/git-lfs/install.sh \
    && rm -r /opt/git-lfs

ENV PYTHONUNBUFFERED=1\
    AWS_XRAY_SDK_ENABLED=false\
    GRAND_CHALLENGE_SAGEMAKER_SHIM_VERSION=0.0.3\
    PATH="/opt/poetry/.venv/bin:/home/django/.local/bin:${PATH}"

RUN mkdir -p /opt/poetry /app /static /opt/static /opt/sagemaker-shim \
    && groupadd -r django && useradd -m -r -g django django \
    && chown django:django /opt/poetry /app /static /opt/static /opt/sagemaker-shim

USER django:django

# Fetch and install sagemaker shim for shimming containers
RUN mkdir -p /opt/sagemaker-shim \
    && wget "https://github.com/DIAGNijmegen/rse-sagemaker-shim/releases/download/v${GRAND_CHALLENGE_SAGEMAKER_SHIM_VERSION}/sagemaker-shim-${GRAND_CHALLENGE_SAGEMAKER_SHIM_VERSION}-Linux-x86_64.tar.gz" -P /opt/sagemaker-shim/ \
    && echo "c12cef84b82ca58fff3d89ee0a3fbdf2a441796c21084627e69a084c988a2948  /opt/sagemaker-shim/sagemaker-shim-${GRAND_CHALLENGE_SAGEMAKER_SHIM_VERSION}-Linux-x86_64.tar.gz" | shasum -c - || exit 1 \
    && tar -C /opt/sagemaker-shim/ -xzvf "/opt/sagemaker-shim/sagemaker-shim-${GRAND_CHALLENGE_SAGEMAKER_SHIM_VERSION}-Linux-x86_64.tar.gz" \
    && rm "/opt/sagemaker-shim/sagemaker-shim-${GRAND_CHALLENGE_SAGEMAKER_SHIM_VERSION}-Linux-x86_64.tar.gz"

WORKDIR /opt/poetry

# Install base python packages
COPY --chown=django:django poetry.toml /opt/poetry
COPY --chown=django:django pyproject.toml /opt/poetry
COPY --chown=django:django poetry.lock /opt/poetry

RUN python -m pip install -U pip \
    && python -m pip install -U poetry \
    && poetry config virtualenvs.in-project true \
    && poetry install --no-interaction --no-ansi --no-root --no-dev

##################
# TEST CONTAINER #
##################
FROM base as test-base

# Add java and graphviz for plantuml documentation
USER root
RUN apt-get update && apt-get install -y default-jre graphviz
# Get the minio client (they do not provide sha256sums)
RUN mkdir -p /opt/mc \
    && wget https://dl.min.io/client/mc/release/linux-amd64/mc -P /opt/mc/ \
    && chmod a+x /opt/mc/mc \
    && mv /opt/mc/mc /usr/local/bin/ \
    && rm -r /opt/mc
USER django:django

RUN poetry install --no-interaction --no-ansi --no-root
