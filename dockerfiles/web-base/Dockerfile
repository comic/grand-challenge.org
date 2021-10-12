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
        libvips-dev \
        ruby-licensee

# Fetch and install crane for pushing containers
RUN mkdir -p /opt/crane \
    && wget https://github.com/google/go-containerregistry/releases/download/v0.5.1/go-containerregistry_Linux_x86_64.tar.gz -O /opt/crane/src.tar.gz \
    && echo "24f6a4d63086fb203489f7ce92610b98eff530c30afa19dceb182b511045dc2e  /opt/crane/src.tar.gz" | shasum -c - || exit 1 \
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
    AWS_XRAY_SDK_ENABLED=false

RUN mkdir -p /opt/poetry /app /static /opt/static \
    && python -m pip install -U pip \
    && python -m pip install -U poetry \
    && groupadd -r django && useradd -m -r -g django django \
    && chown django:django /opt/poetry /app /static /opt/static

# Install base python packages
COPY poetry.toml /opt/poetry
COPY pyproject.toml /opt/poetry
COPY poetry.lock /opt/poetry

WORKDIR /opt/poetry
RUN poetry config virtualenvs.create false \
    && poetry install --no-dev --no-root

# Apply patch to allow json SQS messages for celery (added in komby 5.1.0)
RUN cd /usr/local/lib/python3.8/site-packages \
    && apt-get install -y patchutils \
    && curl https://github.com/celery/kombu/commit/2a704e35856bda908f5f122d1aaabebc6b469b0c.patch | filterdiff -p1 -x "t/*" | patch -p1

##################
# TEST CONTAINER #
##################
FROM base as test-base

# Add java and graphviz for plantuml documentation
RUN apt-get update && apt-get install -y default-jre graphviz
RUN poetry install --no-root
