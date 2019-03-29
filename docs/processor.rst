======================================
 Processor specification
======================================

*Version 1.0.1 - Date: 2019-03-29*

**Terms and definitions**

This documents follows the definitions for keywords layed out in `RFC 2119 <http://www.faqs.org/rfcs/rfc2119.html>`__.

What is a processor?
====================

A processor is a single or group of algorithms packaged in a docker container that can be applied to a set of files and produces some sort of output.

The processor container can be uploaded to the `algorithms page <https://grand-challenge.org/algorithms>`__. Then, it will be possible to upload some input files and the algorithm will be run on those files and produce an output.

Processor Inputs
================

Inputs to an algorithm are made a available to the processor in the directory ``/input``.  Valid inputs to an algorithm are files containing:


* MetaIO MHD/MHA files with accompanying zraw or raw files
* TIFF Images


The processor specification must describe which formats are supported.

MetaIO MHD/MHA files
--------------------

`MetaIO image files <https://itk.org/Wiki/ITK/MetaIO/Documentation>`__ can be placed at any location of the ``/input`` directory. Accepted MetaIO image formats are mhd+raw, mhd+zraw, or mha files. MetaIO files in subdirectories may be ignored by processors. mhd and mha files must use the corresponding file extension to disambiguate between the two file formats.

Other files
-----------

Processors must be resilient with regards to extra files found in the ``/input`` directory. Any file that does not follow the specifications laid out above should be ignored by a processor. However, algorithms may specify in their documentation that additional "other files" are required for correct functioning of an algorithm. These additional files must be specified in the processor documentation.

Execution
=========

A processor is a program that runs as main executable inside a Linux-based docker container implemented in any language. The algorithm must terminate by itself when it has finished processing data from the ``/input`` directory.

If an algorithm fails to process any items from the ``/input`` directory, it must terminate with and exitcode != 0. The algorithm should use stdout and stderr streams to explain the failure state. The contents of the ``/output`` directory shall be considered to be invalid in such a case. In all other cases, the algorithm must produce a valid ``/output/results.json`` file and finish with errorcode == 0.

If the algorithm fails to process some items from the ``/input`` directory, it must produce error messages for the given set of inputs as part of the results.json file that is described in the next section. Successful processing of input items must produce results that are written into the results.json for the given input items.

Processor Outputs
=================

Outputs of an algorithm must be stored in the directory ``/output/``. The output directory must consists of:

* A JSON file that contains the calculated results: ``/output/results.json``

* Optional: Image files at user specified locations in the ``/output/images/`` directory.

    * Images must be saved using MetaIO mha or mhd files (either using compressed zraw or uncompressed raw binary blobs).

    * All images should be referred to in the ``results.json`` file. Images are referred to by adding a string-value in the ``metrics`` section denoting the relative path from the ``results.json`` to the image mhd or mha file. The semantics of the image are algorithm specific, meaning that images can contain any type information an algorithm author wants to store. Paths to image files should be prefixed with ``filepath:``.

results.json
------------

The ``results.json`` file must be a json file that contains a single array of *result objects*. Each input image results in one *result object*. A *result object* is a json-object that must contain computed algorithm results, references to related input files, and, in case a result cannot be computed, error messages explaining why the result cannot be computed. To encode these information, the result object for a given input item must use the following three keys:

* ``entity``

* ``metrics``

* ``error_messages``

Result object sections
######################

``entity``: This section links a result to a set of input files that were found in the input directory.

* Add suggestions for simple filename references

* Any json structure

``metrics``: The metrics section contains algorithm results. The results may be stored using any json structure, but the structure must be specified by the processor documentation. Also, all external files (except for ``results.json`` and ``types.json``) must be listed in this section. Filepaths referring to external files should thereby be prefixed with the string ``filepath:``. Unlisted external files may be ignored by frameworks running processors and not be copied to a persistent data store.

``error_messages``: A json list of human-readable strings denoting algorithm failures. If processor execution for a given set of input files was successful (see entity), this list must be empty. If the processing failed for a given set of inputs, at least one human readable error message denoting the failure state must be added to this list. In this case, the metrics section may be set to null or, if the metrics section is not set to null while errors are listed, it must be assumed that the metrics section is incomplete.::

  [
    {
      "entity": ...,
      "metrics": ...,
      "error_messages": [
        ...
      ]
    },
    ...
  ]


Runtime requirements
====================

Algorithms require system resources to run. The amount and type of system resources required to run a processor should be specified as `docker labels <https://docs.docker.com/engine/reference/builder/#label>`__. The following docker container labels should be used for specifying the required system resources are required to run a processor.

**Docker container labels**

+-----------------------------------+--------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Label                             | Values                         | Description                                                                                                                                                                                                                                                                            |
+===================================+================================+========================================================================================================================================================================================================================================================================================+
| processor.cpus                    | Integer >= 1,                  | The number of cpus the processor requires to finish computation in a reasonable amount of time                                                                                                                                                                                         |
|                                   | Default: 1                     |                                                                                                                                                                                                                                                                                        |
+-----------------------------------+--------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| processor.cpu.capabilities        | null or Stringlist             | An optional list of processor capabilities that the used CPU must support to successfully run the processor. Can be an arbitrary list of flags, but at the moment of writing the following flags are supported: ``avx``, ``sse1``, ``see2``, ``sse3``, ``sse4_1``, ``sse4_2``, ``mmx`` |
+-----------------------------------+--------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| processor.memory                  | Size > 0,                      | The amount of memory to assign to the processor. This is the minimum amount of memory required with which the processor will successfully run.                                                                                                                                         |
|                                   | Default: 1G                    |                                                                                                                                                                                                                                                                                        |
+-----------------------------------+--------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| processor.gpu_count               | Integer >= 0                   | The number of CUDA-capable GPUs that are required to run the processor.                                                                                                                                                                                                                |
|                                   | Default: 0                     |                                                                                                                                                                                                                                                                                        |
+-----------------------------------+--------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| processor.gpu.compute_capability  | null or Version,               | Allows characterizing the required gpus in terms of supported `CUDA compute capabilities <https://developer.nvidia.com/cuda-gpus>`__. If specified, it must be a valid compute capability version.                                                                                     |
|                                   | Default: null                  |                                                                                                                                                                                                                                                                                        |
+-----------------------------------+--------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| processor.gpu.memory              | null or Size,                  | The amount of gpu memory that must available on the type of graphics card that is made available to the container.                                                                                                                                                                     |
|                                   | Default: null                  |                                                                                                                                                                                                                                                                                        |
+-----------------------------------+--------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

**Value type descriptions**

+------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Type       | Description                                                                                                                                                                                                                                                                                                                                                                                                      |
+============+==================================================================================================================================================================================================================================================================================================================================================================================================================+
| null       | The string "null" (case insensitive). Represents none/nothing.                                                                                                                                                                                                                                                                                                                                                   |
+------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Integer    | A whole number - no size limit. Valid examples:                                                                                                                                                                                                                                                                                                                                                                  |
|            |                                                                                                                                                                                                                                                                                                                                                                                                                  |
|            | ``-1``, ``10``, ``20222``, ``4e1000``                                                                                                                                                                                                                                                                                                                                                                            |
+------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Size       | A size string. A size string consists of a positive Integer value combined with an optional size-character. Examples:                                                                                                                                                                                                                                                                                            |
|            |                                                                                                                                                                                                                                                                                                                                                                                                                  |
|            | ``1000``, ``5k``, ``10G``, ``100P``                                                                                                                                                                                                                                                                                                                                                                              |
|            |                                                                                                                                                                                                                                                                                                                                                                                                                  |
|            |                                                                                                                                                                                                                                                                                                                                                                                                                  |
|            | The size characters represent 1000-based unit prefixes for the unit "bytes". Size characters are case insensitive and the following associations are defined:                                                                                                                                                                                                                                                    |
|            |                                                                                                                                                                                                                                                                                                                                                                                                                  |
|            | k = kilo = 1000,                                                                                                                                                                                                                                                                                                                                                                                                 |
|            |                                                                                                                                                                                                                                                                                                                                                                                                                  |
|            | g = giga = 1000\ :sup:`3`,                                                                                                                                                                                                                                                                                                                                                                                       |
|            |                                                                                                                                                                                                                                                                                                                                                                                                                  |
|            | t = tera = 1000\ :sup:`4`,                                                                                                                                                                                                                                                                                                                                                                                       |
|            |                                                                                                                                                                                                                                                                                                                                                                                                                  |
|            | p = peta = 1000\ :sup:`5`,                                                                                                                                                                                                                                                                                                                                                                                       |
|            |                                                                                                                                                                                                                                                                                                                                                                                                                  |
|            | e = exa = 1000\ :sup:`6`                                                                                                                                                                                                                                                                                                                                                                                         |
+------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Version    | A version represents a version string. A version must start with at least one positive integer value. An arbitrary number of "."-separated additional positive integer values can follow. Examples:                                                                                                                                                                                                              |
|            |                                                                                                                                                                                                                                                                                                                                                                                                                  |
|            | ``3``, ``3.2``, ``0.0``, ``3.0.0.0``, ``0.1.0``                                                                                                                                                                                                                                                                                                                                                                  |
+------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Stringlist | A comma-separated list of arbitrary strings. Strings cannot contain commas themselves: Example:                                                                                                                                                                                                                                                                                                                  |
|            |                                                                                                                                                                                                                                                                                                                                                                                                                  |
|            | ``one,two,third string,four``                                                                                                                                                                                                                                                                                                                                                                                    |
+------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
