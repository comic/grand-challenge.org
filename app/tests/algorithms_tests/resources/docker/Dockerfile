FROM python:3.10-alpine

ENV PYTHONUNBUFFERED 1

RUN addgroup -S app && adduser -S -G app app
USER app

COPY run_algorithm.py .

ENTRYPOINT ["python", "run_algorithm.py"]
