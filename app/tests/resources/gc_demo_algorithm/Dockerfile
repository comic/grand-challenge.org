FROM python:3.11-slim

RUN useradd -ms /bin/bash myuser
RUN groupadd -r mygroup
RUN usermod -a -G mygroup myuser

WORKDIR /home/myuser

USER myuser

RUN python3 -m pip install pynvml psutil

ADD copy_io.py .

ENV BUILD_TIME=${BUILD_TIME}

ENTRYPOINT ["python", "copy_io.py"]
