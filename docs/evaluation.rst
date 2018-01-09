Evaluation
==========

|project_name| has a system for automatically evaluating new submissions.
Challenge administrators upload their own Docker containers that will be
executed by Celery workers when a new submission in uploaded by a participant.

Evaluation Container Requirements
---------------------------------

The evaluation container must contain everything that is needed to perform the
evaluation on a new submission. This includes the reference standard, and the
code that will execute the evaluation on the new submission.

Input
~~~~~

The input will be extracted and mounted as a docker volume on `/input/`.

Output
~~~~~~

The container must produce the file `/output/metrics.json`. The structure
within must be valid json (ie. loadable with `json.loads()`) and will be stored
as a result in the database. The challenge administrator is free to define what
metrics are included. Aggregate metrics should be stored in a separate object
named `aggregates`. For example::

    {
      "aggregates": {
        "accuracy": 0.5
      }
    }


Template Tags
-------------
.. py:module:: evaluation.templatetags.evaluation_extras

.. autofunction:: get()
