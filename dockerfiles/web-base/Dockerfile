###################
#  Base Container #
###################
ARG PYTHON_VERSION

FROM python:${PYTHON_VERSION}-slim-bullseye as base

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpng-dev \
        libjpeg-dev \
        libjpeg62-turbo-dev \
        libfreetype6-dev \
        libxft-dev \
        libffi-dev \
        wget \
        gettext \
        # postgres packages for psycopg2
        libpq-dev \
        # curl and ssl for pycurl
        libcurl4-openssl-dev \
        libssl-dev \
        # for python-magic
        libmagic1 \
        # openslide and vips for image imports with panimg
        # gcc is required to compile the extensions
        libopenslide-dev \
        libvips-dev \
        gcc \
        # ruby2.7 and rugged for licensee
        ruby2.7 \
        ruby-rugged \
        # git for CodeBuild integration
        git \
    && rm -rf /var/lib/apt/lists/*

# Fetch and install licensee for checking licenses
RUN gem install licensee -v 9.15.1

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

# Get the minio client for development
RUN mkdir -p /opt/mc \
    && wget https://dl.min.io/client/mc/release/linux-amd64/archive/mc.RELEASE.2022-06-11T21-10-36Z -O /opt/mc/mc \
    && echo "77a784948c3bce2c169bf3f4d998ae1485c060193689268627ff896ddcf9f617  /opt/mc/mc" | shasum -c - || exit 1 \
    && chmod a+x /opt/mc/mc \
    && mv /opt/mc/mc /usr/local/bin/ \
    && rm -r /opt/mc

# Get the docker cli
RUN mkdir -p /opt/docker \
    && wget https://download.docker.com/linux/static/stable/x86_64/docker-20.10.17.tgz -O /opt/docker/docker.tgz \
    && echo "969210917b5548621a2b541caf00f86cc6963c6cf0fb13265b9731c3b98974d9  /opt/docker/docker.tgz" | shasum -c - || exit 1 \
    && tar -C /opt/docker/ -xzvf /opt/docker/docker.tgz \
    && chmod a+x /opt/docker/docker/docker \
    && mv /opt/docker/docker/docker /usr/local/bin/ \
    && rm -r /opt/docker

ENV PYTHONUNBUFFERED=1\
    AWS_XRAY_SDK_ENABLED=false\
    GRAND_CHALLENGE_SAGEMAKER_SHIM_VERSION=0.1.0\
    PATH="/opt/poetry/.venv/bin:/home/django/.local/bin:${PATH}"

RUN mkdir -p /opt/poetry /app /static /opt/static /opt/sagemaker-shim \
    && groupadd -r django && useradd -m -r -g django django \
    && chown django:django /opt/poetry /app /static /opt/static /opt/sagemaker-shim

USER django:django

# Fetch and install sagemaker shim for shimming containers
RUN mkdir -p /opt/sagemaker-shim \
    && wget "https://github.com/DIAGNijmegen/rse-sagemaker-shim/releases/download/v${GRAND_CHALLENGE_SAGEMAKER_SHIM_VERSION}/sagemaker-shim-${GRAND_CHALLENGE_SAGEMAKER_SHIM_VERSION}-Linux-x86_64.tar.gz" -P /opt/sagemaker-shim/ \
    && echo "352ec794b5f166ea53bc2d0628959c2fc19a53a7d61c02f1dbe3311995028177  /opt/sagemaker-shim/sagemaker-shim-${GRAND_CHALLENGE_SAGEMAKER_SHIM_VERSION}-Linux-x86_64.tar.gz" | shasum -c - || exit 1 \
    && tar -C /opt/sagemaker-shim/ -xzvf "/opt/sagemaker-shim/sagemaker-shim-${GRAND_CHALLENGE_SAGEMAKER_SHIM_VERSION}-Linux-x86_64.tar.gz" \
    && rm "/opt/sagemaker-shim/sagemaker-shim-${GRAND_CHALLENGE_SAGEMAKER_SHIM_VERSION}-Linux-x86_64.tar.gz"

WORKDIR /opt/poetry

# Install base python packages
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

USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        # Add java and graphviz for plantuml documentation
        default-jre \
        graphviz \
        # make for sphinx docs
        make \
    && rm -rf /var/lib/apt/lists/*
USER django:django

RUN poetry install --no-interaction --no-ansi --no-root
