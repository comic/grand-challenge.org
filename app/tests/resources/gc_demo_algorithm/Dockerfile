FROM python:3.9-alpine

ENV PYTHONUNBUFFERED 1

WORKDIR /tmp

RUN addgroup -S app && adduser -S -G app app
USER app

ADD copy_io.py /tmp

ENTRYPOINT ["python", "copy_io.py"]
