FROM python:3.9-alpine

ENV PYTHONUNBUFFERED 1

RUN addgroup -S app && adduser -S -G app app
USER app

ENTRYPOINT ["python", "-m", "http.server"]
