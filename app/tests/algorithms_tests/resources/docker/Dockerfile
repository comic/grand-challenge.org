FROM python:3.11-slim

ENV PYTHONUNBUFFERED 1

RUN useradd -ms /bin/bash myuser
RUN groupadd -r mygroup
RUN usermod -a -G mygroup myuser

WORKDIR /home/myuser

USER myuser

COPY run_algorithm.py .

ENTRYPOINT ["python", "run_algorithm.py"]
