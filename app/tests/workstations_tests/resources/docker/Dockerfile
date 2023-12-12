FROM --platform=linux/amd64 python:3.10-alpine

ENV PYTHONUNBUFFERED 1

RUN addgroup -S app && adduser -S -G app app
USER app

ENTRYPOINT ["python", "-m", "http.server"]
