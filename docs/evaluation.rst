Evaluation
==========

|project_name| has a system for automatically evaluating new submissions.
Challenge administrators upload their own Docker containers that will be
executed by Celery workers when a new submission in uploaded by a participant.

Evaluation Container Requirements
---------------------------------

The evaluation container must contain everything that is needed to perform the
evaluation on a new submission. This includes the reference standard, and the
code that will execute the evaluation on the new submission. An instance of the
evaluation container image is created for each submission.

Input
~~~~~

The participants submission will be extracted and mounted as a docker volume
on `/input/`.

Entrypoint
~~~~~~~~~~

The container will be run with the default arguments, so the entrypoint must
by default produce an evaluation for the data that will reside on `/input/`.
The container is responsible for loading all of the data, handling incorrect
filenames, incomplete submissions, duplicate folders, etc.

Errors
~~~~~~

If there is an error in the evaluation process |project_name| will parse
`stderr` and return the last non-empty line to the user. If your evaluation
script is in Python the best practice is to raise an exception and the message
will then be passed to the user, eg

    raise AttributeError('Expected to find 10 images, you submitted 5')


Output
~~~~~~

The container must produce the file `/output/metrics.json`. The structure
within must be valid json (ie. loadable with `json.loads()`) and will be stored
as a result in the database. The challenge administrator is free to define what
metrics are included. We recommend storing results in two objects - `case` for
the scores on individual cases (eg, scans), and `aggregates` for when there
is one number per evaluation. For example::

    {
      "case": {
        "dicecoefficient": {
          "0": 0.6461774875144065,
          "1": 0.7250400040547097,
          "2": 0.6747092236948878,
          "3": 0.6452332692745784,
          "4": 0.6839602948067993,
          "5": 0.6817807628480707,
          "6": 0.4715406247268339,
          "7": 0.5988810496224731,
          "8": 0.5475856316815167,
          "9": 0.32923801642370615
        },
        "jaccardcoefficient": {
          "0": 0.47729852440408627,
          "1": 0.5686766693547471,
          "2": 0.5091027839007266,
          "3": 0.47626890640360103,
          "4": 0.5197109875240358,
          "5": 0.5171983108978807,
          "6": 0.30850713624139353,
          "7": 0.4274305543159676,
          "8": 0.3770174983296798,
          "9": 0.1970585994056237
        },
        "alg_fname": {
          "0": "1.2.840.113704.1.111.2296.1199810886.7.mhd",
          "1": "1.2.276.0.28.3.0.14.4.0.20090213134050413.mhd",
          "2": "1.2.276.0.28.3.0.14.4.0.20090213134114792.mhd",
          "3": "1.2.840.113704.1.111.2004.1131987870.11.mhd",
          "4": "1.2.840.113704.1.111.2296.1199810941.11.mhd",
          "5": "1.2.840.113704.1.111.4400.1131982359.11.mhd",
          "6": "1.3.12.2.1107.5.1.4.50585.4.0.7023259421321855.mhd",
          "7": "1.0.000.000000.0.00.0.0000000000.0000.0000000000.000.mhd",
          "8": "1.2.392.200036.9116.2.2.2.1762676169.1080882991.2256.mhd",
          "9": "2.16.840.1.113669.632.21.3825556854.538251028.390606191418956020.mhd"
        },
        "gt_fname": {
          "0": "1.2.840.113704.1.111.2296.1199810886.7.mhd",
          "1": "1.2.276.0.28.3.0.14.4.0.20090213134050413.mhd",
          "2": "1.2.276.0.28.3.0.14.4.0.20090213134114792.mhd",
          "3": "1.2.840.113704.1.111.2004.1131987870.11.mhd",
          "4": "1.2.840.113704.1.111.2296.1199810941.11.mhd",
          "5": "1.2.840.113704.1.111.4400.1131982359.11.mhd",
          "6": "1.3.12.2.1107.5.1.4.50585.4.0.7023259421321855.mhd",
          "7": "1.0.000.000000.0.00.0.0000000000.0000.0000000000.000.mhd",
          "8": "1.2.392.200036.9116.2.2.2.1762676169.1080882991.2256.mhd",
          "9": "2.16.840.1.113669.632.21.3825556854.538251028.390606191418956020.mhd"
        }
      },
      "aggregates": {
        "dicecoefficient_mean": 0.6004146364647982,
        "dicecoefficient_std": 0.12096508479974993,
        "dicecoefficient_min": 0.32923801642370615,
        "dicecoefficient_max": 0.7250400040547097,
        "jaccardcoefficient_mean": 0.4378269970777743,
        "jaccardcoefficient_std": 0.11389145837530869,
        "jaccardcoefficient_min": 0.1970585994056237,
        "jaccardcoefficient_max": 0.5686766693547471,
      }
    }


Evaluation Options
~~~~~~~~~~~~~~~~~~

.. automodule:::: grandchallenge.evaluation.models.Config

.. autoclass:: grandchallenge.evaluation.models.Config
    :members:


Template Tags
-------------
.. py:module:: grandchallenge.evaluation.templatetags.evaluation_extras

.. autofunction:: get_jsonpath()
