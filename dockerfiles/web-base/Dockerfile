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
    && tar -C /opt/crane/ -xzvf /opt/crane/src.tar.gz crane \
    && chmod a+x /opt/crane/crane \
    && mv /opt/crane/crane /usr/local/bin/ \
    && rm -r /opt/crane

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
