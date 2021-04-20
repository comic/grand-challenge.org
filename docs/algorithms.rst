======================================
 Algorithms
======================================

What is an algorithm?
=====================

An algorithm is a container image that is executed on a set of inputs, producing a set of outputs. The inputs and outputs can be text, numbers, booleans, medical images or annotations.

Algorithm Inputs
================

Inputs to an algorithm are available in the container in the ``/input`` directory. 
You can add :ref:`component interfaces <components>` that will provide the inputs to your algorithm.
You can find a list of the `currently available interfaces`_ on grand challenge.

The ``relative_path`` property on the ``ComponentInterface`` is used to determine where the input value will be placed inside the container.

The most types get written to a json file, located in ``/input/{relative_path}`` in the container.
You can read and parse these with

.. code-block:: python

    import json
    
    with open("/input/{relative_path}") as f:
        val = json.loads(f.read())

When creating a new experiment for an algorithm, you can provide values for all ``ComponentInterfaces`` using the form provided.

Image files
-----------

Grand Challenge works with two image formats that will need to be read or written by your algorithm container image ``.mha`` and ``.tif``.

Execution
=========

A container will be created from the container image whenever you create an experiment for your algorithm.

Any output for both `stdout` and `stderr` is captured. The output for `stderr` gets marked as a warning in the experiment's result.

If an algorithm does not properly run, it should exit with a non zero exit code. The job for the algorithm then gets marked as failed.


Algorithm Outputs
=================

Outputs of an algorithm must be stored in the directory ``/output/``. 
As with the inputs, a ``ComponentInterface`` needs to be defined for each of the expected outputs.
You can find a list of the `currently available interfaces`_ on grand challenge.

results.json
------------

If one of the defined outputs for the algorithms is a ``results.json`` file, the contents of this file will be parsed and shown on the algorithm's result page. You can provide a jinja template to an algorithm for the rendering of these results.

Frequently Asked Questions
==========================

What resources are available?
-----------------------------

Currently algorithms are run with 1 NVidia T4 GPU with CUDA 10 and 16GB GPU memory.
Algorithms are allowed to use 200% CPU, 24GB system memory and 512 threads.
The algorithms are run without any access to the network.
All container privileges are dropped.

Where can I write data?
-----------------------

The container filesystem and output directories are writable, the input directory is read only.

Time limit exceeded errors with PyTorch
---------------------------------------

Algorithms have a wall time limit of 2 hours.
Sometimes, the algorithm will produce little to no output in the logs.
Often, this is due to using PyTorch ``DataLoaders``.
These require using shared memory, which is not enabled on grand-challenge.org.
To resolve this, set ``num_workers`` to ``0`` when initialising your ``DataLoader``.

.. _`currently available interfaces`: https://grand-challenge.org/algorithms/interfaces/
