FROM python:3.8 as base

RUN apt-get update \
    && apt-get install -y cmake swig \
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
    && make \
    && make install \
    && ldconfig \
    && rm -r /opt/gdcm

# If this work this next line should output something like
#   (7fe0,0010)     ??      0
RUN python -c "import gdcm; print(gdcm.DataElement(gdcm.Tag(0x7fe0, 0x0010)))"
