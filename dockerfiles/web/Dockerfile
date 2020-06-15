###################
#  Base Container #
###################
FROM python:3.8 as base

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
    && git clone --branch v3.0.6 --depth 1 git://git.code.sf.net/p/gdcm/gdcm \
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

ENV PYTHONUNBUFFERED 1

RUN mkdir -p /opt/poetry /app /static /opt/static
RUN python -m pip install -U "pip!=20.0" setuptools==45
RUN python -m pip install -U poetry

RUN groupadd -g 2001 -r django && useradd -m -u 2001 -r -g django django
RUN chown django:django /opt/poetry /app /static /opt/static

# Install base python packages
WORKDIR /opt/poetry
COPY poetry.toml /opt/poetry
COPY pyproject.toml /opt/poetry
COPY poetry.lock /opt/poetry
RUN poetry config virtualenvs.create false \
    && poetry install --no-dev --no-root

###################
#  Webpack        #
###################
FROM node:11-alpine as npm
RUN mkdir /src
COPY package.json /src/
COPY ./app/grandchallenge/core/static/css/base.scss /src/base.scss
WORKDIR /src

RUN npm install && npm run build

###################
#  Test Container #
###################
FROM base as test

# Add java and graphviz for plantuml documentation
RUN apt-get update && apt-get install -y default-jre graphviz
RUN poetry install --no-root

COPY --chown=django:django setup.cfg /home/django

USER django:django
WORKDIR /app
COPY --chown=django:django ./app/ /app/
COPY --from=npm --chown=django:django /src/dist/ /opt/static/vendor/
RUN python manage.py collectstatic --noinput

##################
# Dist Container #
##################
FROM base as dist

USER django:django
WORKDIR /app
COPY --chown=django:django ./app/ /app/
COPY --from=npm --chown=django:django /src/dist/ /opt/static/vendor/
RUN python manage.py collectstatic --noinput

ARG COMMIT_ID=unknown
ENV COMMIT_ID=$COMMIT_ID
