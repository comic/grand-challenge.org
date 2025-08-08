###################
#  Base Container #
###################
ARG PYTHON_VERSION

FROM python:${PYTHON_VERSION}-slim-bookworm AS base

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
        xz-utils \
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
        # ruby3.1, rugged and nokogiri for licensee
        ruby3.1 \
        ruby-rugged \
        ruby-nokogiri \
        # git for CodeBuild integration
        git \
        # for dbshell \
        postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Fetch and install licensee for checking licenses
# Separate install required as the bundled version does not include the --json flag
RUN gem install licensee -v 9.16.1

# Fetch and install crane for pushing containers
RUN mkdir -p /opt/crane \
    && wget https://github.com/google/go-containerregistry/releases/download/v0.19.0/go-containerregistry_Linux_x86_64.tar.gz -O /opt/crane/src.tar.gz \
    && echo "daa629648e1d1d10fc8bde5e6ce4176cbc0cd48a32211b28c3fd806e0fa5f29b  /opt/crane/src.tar.gz" | shasum -c - || exit 1 \
    && tar -C /opt/crane/ -xzvf /opt/crane/src.tar.gz crane \
    && chmod a+x /opt/crane/crane \
    && mv /opt/crane/crane /usr/local/bin/ \
    && rm -r /opt/crane

# Fetch and install git lfs for github integration
RUN mkdir -p /opt/git-lfs \
    && wget https://github.com/git-lfs/git-lfs/releases/download/v3.4.1/git-lfs-linux-amd64-v3.4.1.tar.gz -O /opt/git-lfs/src.tar.gz \
    && echo "1772dc260961db27958088740b7e9ecebf945abad8c2d504d412448f53faf147  /opt/git-lfs/src.tar.gz" | shasum --algorithm 256 -c - || exit 1 \
    && tar -C /opt/git-lfs/ -xzvf /opt/git-lfs/src.tar.gz \
    && bash /opt/git-lfs/git-lfs-3.4.1/install.sh \
    && rm -r /opt/git-lfs

# Get the minio client for development
RUN mkdir -p /opt/mc \
    && wget https://dl.min.io/client/mc/release/linux-amd64/archive/mc.RELEASE.2025-07-16T15-35-03Z -O /opt/mc/mc \
    && echo "a5c3695b6f76ed958c0f099795f32091fced0d748ddc749c8b24e07681bbfbb9  /opt/mc/mc" | shasum -c - || exit 1 \
    && chmod a+x /opt/mc/mc \
    && mv /opt/mc/mc /usr/local/bin/ \
    && rm -r /opt/mc

# Get the docker cli
RUN mkdir -p /opt/docker \
    && wget https://download.docker.com/linux/static/stable/x86_64/docker-27.1.1.tgz -O /opt/docker/docker.tgz \
    && echo "118da6b8fc8e8b6c086ab0dd5e64ee549376c3a3f963723bbc9a46db475bf21f  /opt/docker/docker.tgz" | shasum -c - || exit 1 \
    && tar -C /opt/docker/ -xzvf /opt/docker/docker.tgz \
    && chmod a+x /opt/docker/docker/docker \
    && mv /opt/docker/docker/docker /usr/local/bin/ \
    && rm -r /opt/docker

ENV PYTHONUNBUFFERED=1\
    AWS_XRAY_SDK_ENABLED=false\
    COMPONENTS_SAGEMAKER_SHIM_VERSION=0.3.5\
    PATH="/opt/grand-challenge/.venv/bin:/home/django/.local/bin:${PATH}"

RUN mkdir -p /opt/grand-challenge /app /static /opt/sagemaker-shim /opt/virtualenvs \
    && groupadd -r django && useradd -m -r -g django django \
    && chown django:django /opt/grand-challenge /app /static /opt/sagemaker-shim /opt/virtualenvs

USER django:django

# Fetch and install sagemaker shim for shimming containers
RUN mkdir -p /opt/sagemaker-shim \
    && wget "https://github.com/DIAGNijmegen/rse-sagemaker-shim/releases/download/v${COMPONENTS_SAGEMAKER_SHIM_VERSION}/sagemaker-shim-${COMPONENTS_SAGEMAKER_SHIM_VERSION}-Linux-x86_64.tar.gz" -P /opt/sagemaker-shim/ \
    && echo "a0f64b99ffea8faed65a23bf0f52ff1f2a20900ca8bc6a3d13a2ff7eff1d7eb7  /opt/sagemaker-shim/sagemaker-shim-${COMPONENTS_SAGEMAKER_SHIM_VERSION}-Linux-x86_64.tar.gz" | shasum -c - || exit 1 \
    && tar -C /opt/sagemaker-shim/ -xzvf "/opt/sagemaker-shim/sagemaker-shim-${COMPONENTS_SAGEMAKER_SHIM_VERSION}-Linux-x86_64.tar.gz" \
    && rm "/opt/sagemaker-shim/sagemaker-shim-${COMPONENTS_SAGEMAKER_SHIM_VERSION}-Linux-x86_64.tar.gz"

# Create virtual environments
RUN mkdir -p /opt/virtualenvs \
    && python -m venv /opt/virtualenvs/biom \
    && /opt/virtualenvs/biom/bin/python -m pip --no-cache-dir --no-color install biom-format

WORKDIR /opt/grand-challenge

# Install base python packages
COPY --chown=django:django pyproject.toml /opt/grand-challenge
COPY --chown=django:django uv.lock /opt/grand-challenge

RUN python -m pip install -U pip \
    && python -m pip install -U uv \
    && uv sync --no-progress --no-dev

##################
# TEST CONTAINER #
##################
FROM base AS test-base

USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        # Add java and graphviz for plantuml documentation
        default-jre \
        graphviz \
        # make for sphinx docs
        make \
        # playwright dependencies
        libatk1.0-0 \
        libatk-bridge2.0-0 \
        libatspi2.0-0 \
        libxcomposite1 \
        libxrandr2 \
        libgbm1 \
        libxkbcommon0 \
    && rm -rf /var/lib/apt/lists/*

ENV NODE_VERSION=22.17.1

# Install Node.js v22.17.1 (LTS)
RUN mkdir -p /opt/node \
    && wget https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-x64.tar.xz -O /opt/node/node.tar.xz \
    && echo "ff04bc7c3ed7699ceb708dbaaf3580d899ff8bf67f17114f979e83aa74fc5a49  /opt/node/node.tar.xz" | shasum -a 256 -c - || exit 1 \
    && tar -xJf /opt/node/node.tar.xz -C /usr/local --strip-components=1 \
    && rm /opt/node/node.tar.xz \
    && ln -s /usr/local/bin/node /usr/bin/node \
    && ln -s /usr/local/bin/npm /usr/bin/npm \
    && ln -s /usr/local/bin/npx /usr/bin/npx

USER django:django

RUN uv sync --no-progress
RUN playwright install
