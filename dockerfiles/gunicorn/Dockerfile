FROM ubuntu:xenial

RUN apt-get update && \
    apt-get install -y \
    python \
    python-pip \
    python-openssl \
    libpng-dev \
    libjpeg-dev \
    libjpeg8-dev \
    libfreetype6-dev \
    libxft-dev \
    libmysqlclient-dev \
    libffi-dev

WORKDIR /app

COPY ./django /app
COPY requirements.txt /app
RUN pip install -r /app/requirements.txt

EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]