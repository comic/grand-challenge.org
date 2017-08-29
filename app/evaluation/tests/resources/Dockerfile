FROM python:3.6

ENV PYTHONUNBUFFERED 1

RUN pip install scikit-learn numpy scipy

RUN mkdir /input
RUN mkdir /output
WORKDIR /tmp

ADD ground_truth.csv /tmp
ADD evaluate_submission.py /tmp

ADD submission.csv /input

ENTRYPOINT ["python", "evaluate_submission.py"]
