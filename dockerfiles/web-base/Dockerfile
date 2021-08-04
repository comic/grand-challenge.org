###################
#  Base Container #
###################
ARG PYTHON_VERSION

FROM python:${PYTHON_VERSION} as base

ARG GDCM_VERSION_TAG

# Build and install gdcm and install system dependencies
RUN apt-get update \
    && apt-get install -y \
        cmake \
        swig \
        python-openssl \
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
    && mkdir -p /opt/gdcm/build \
    && cd /opt/gdcm \
    && git clone --branch v${GDCM_VERSION_TAG} --depth 1 git://git.code.sf.net/p/gdcm/gdcm \
    && cd /opt/gdcm/build \
    && cmake \
        -DCMAKE_SKIP_RPATH:BOOL=YES \
        -DCMAKE_INSTALL_PREFIX:PATH=/usr \
        -DGDCM_BUILD_SHARED_LIBS:BOOL=ON \
        -DGDCM_DOCUMENTATION:BOOL=OFF \
        -DGDCM_BUILD_DOCBOOK_MANPAGES:BOOL=OFF \
        -DGDCM_BUILD_TESTING:BOOL=OFF \
        -DCMAKE_BUILD_TYPE=Release \
        -DGDCM_WRAP_PYTHON:BOOL=ON \
        -DGDCM_INSTALL_PYTHONMODULE_DIR=$(python -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())") \
        -DGDCM_USE_VTK:BOOL=OFF \
        -DGDCM_USE_JPEGLS:BOOL=ON \
        -DGDCM_USE_PVRG:BOOL=ON \
        -DGDCM_USE_SYSTEM_EXPAT:BOOL=ON \
        -DGDCM_USE_SYSTEM_ZLIB:BOOL=ON \
        -DGDCM_USE_SYSTEM_UUID:BOOL=ON \
        -DGDCM_USE_SYSTEM_OPENJPEG:BOOL=ON \
        -DGDCM_USE_SYSTEM_OPENSSL:BOOL=ON \
        -DCMAKE_C_FLAGS=-fPIC \
        -DCMAKE_CXX_FLAGS=-fPIC \
        /opt/gdcm/gdcm \
    && make -j $(nproc) \
    && make install \
    && ldconfig \
    && rm -r /opt/gdcm \
    && apt-get purge -y swig cmake

# Fetch and install crane for pushing containers
RUN mkdir -p /opt/crane \
    && wget https://github.com/google/go-containerregistry/releases/download/v0.5.1/go-containerregistry_Linux_x86_64.tar.gz -O /opt/crane/src.tar.gz \
    && tar -C /opt/crane/ -xzvf /opt/crane/src.tar.gz crane \
    && chmod a+x /opt/crane/crane \
    && mv /opt/crane/crane /usr/local/bin/ \
    && rm -r /opt/crane

ENV PYTHONUNBUFFERED=1\
    AWS_XRAY_SDK_ENABLED=false

RUN mkdir -p /opt/poetry /app /static /opt/static /mnt/aws-batch-nfs \
    && python -m pip install -U pip \
    && python -m pip install -U poetry \
    && groupadd -r django && useradd -m -r -g django django \
    && chown django:django /opt/poetry /app /static /opt/static /mnt/aws-batch-nfs

# Install base python packages
COPY poetry.toml /opt/poetry
COPY pyproject.toml /opt/poetry
COPY poetry.lock /opt/poetry

WORKDIR /opt/poetry
RUN poetry config virtualenvs.create false \
    && poetry install --no-dev --no-root

##################
# TEST CONTAINER #
##################
FROM base as test-base

# Add java and graphviz for plantuml documentation
RUN apt-get update && apt-get install -y default-jre graphviz
RUN poetry install --no-root
