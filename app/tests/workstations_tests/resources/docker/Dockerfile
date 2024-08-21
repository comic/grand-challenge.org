FROM python:3.11-alpine

RUN addgroup -S app && adduser -S -G app app
USER app

ENTRYPOINT ["python", "-m", "http.server"]
