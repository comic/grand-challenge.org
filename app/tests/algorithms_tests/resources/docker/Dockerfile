FROM python:3.10-alpine

ENV PYTHONUNBUFFERED 1

WORKDIR /tmp

RUN addgroup -S app && adduser -S -G app app
USER app

ADD run_algorithm.py /tmp

ENTRYPOINT ["python", "run_algorithm.py"]
