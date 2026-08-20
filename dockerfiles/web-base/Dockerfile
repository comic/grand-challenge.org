###################
#  Base Container #
###################
ARG PYTHON_VERSION

FROM --platform=linux/amd64 python:${PYTHON_VERSION}-slim-bookworm AS base

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
        # ruby3.1, rugged and nokogiri for licensee
        ruby3.1 \
        ruby-rugged \
        ruby-nokogiri \
        # git for CodeBuild integration
        git \
        # for dbshell
        postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Fetch and install licensee for checking licenses
# Separate install required as the bundled version does not include the --json flag
RUN gem install licensee -v 9.16.1

# Fetch and install crane for pushing containers
RUN mkdir -p /opt/crane \
    && wget https://github.com/google/go-containerregistry/releases/download/v0.21.1/go-containerregistry_Linux_x86_64.tar.gz -O /opt/crane/src.tar.gz \
    && echo "ffca5eafe0af8078f2c627fb852104f9d762fad1eb36c04e93ca14fce76d47d2  /opt/crane/src.tar.gz" | shasum -c - || exit 1 \
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

ENV PYTHONUNBUFFERED=1\
    AWS_XRAY_SDK_ENABLED=false\
    COMPONENTS_SAGEMAKER_SHIM_VERSION=0.8.2\
    PATH="/opt/grand-challenge/.venv/bin:/home/django/.local/bin:${PATH}"

RUN mkdir -p /opt/grand-challenge /app /static /opt/sagemaker-shim /opt/virtualenvs \
    && groupadd -r django && useradd -m -r -g django django \
    && chown django:django /opt/grand-challenge /app /static /opt/sagemaker-shim /opt/virtualenvs

USER django:django

# Fetch and install sagemaker shim for shimming containers
RUN mkdir -p /opt/sagemaker-shim \
    && wget "https://github.com/DIAGNijmegen/rse-sagemaker-shim/releases/download/v${COMPONENTS_SAGEMAKER_SHIM_VERSION}/sagemaker-shim-${COMPONENTS_SAGEMAKER_SHIM_VERSION}-Linux-x86_64.tar.gz" -P /opt/sagemaker-shim/ \
    && echo "285fa55a97bb3e8ffd3480ef675a17954f16bea5608c86d669a355d02a35bbbb  /opt/sagemaker-shim/sagemaker-shim-${COMPONENTS_SAGEMAKER_SHIM_VERSION}-Linux-x86_64.tar.gz" | shasum -c - || exit 1 \
    && tar -C /opt/sagemaker-shim/ -xzvf "/opt/sagemaker-shim/sagemaker-shim-${COMPONENTS_SAGEMAKER_SHIM_VERSION}-Linux-x86_64.tar.gz" \
    && rm "/opt/sagemaker-shim/sagemaker-shim-${COMPONENTS_SAGEMAKER_SHIM_VERSION}-Linux-x86_64.tar.gz" \
    && chmod -R a+rX /opt/sagemaker-shim

# Create virtual environments
RUN mkdir -p /opt/virtualenvs \
    && python -m venv /opt/virtualenvs/biom \
    && /opt/virtualenvs/biom/bin/python -m pip --no-cache-dir --no-color install biom-format biopython \
    && python -m venv /opt/virtualenvs/panimg \
    && /opt/virtualenvs/panimg/bin/python -m pip --no-cache-dir --no-color install panimg

WORKDIR /opt/grand-challenge

# Install base python packages
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev

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
USER django:django

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project
RUN playwright install
