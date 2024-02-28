FROM python:3.11-slim

ENV PYTHONUNBUFFERED 1

RUN useradd -ms /bin/bash myuser
RUN groupadd -r mygroup
RUN usermod -a -G mygroup myuser

WORKDIR /home/myuser

USER myuser

RUN python3 -m pip install pynvml psutil

ADD copy_io.py .

ENTRYPOINT ["python", "copy_io.py"]
