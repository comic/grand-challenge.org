Design decisions
================

This section contains extra information about design decisions that have
been made during the development of grand-challenge.org. This section is 
intended for software developers who want to contribute to the codebase. It is
a summary of large scale decisions made by the development team and will help
(we hope) to guide future developments so that all the overall design of
grand-challenge remains consistent.

Definitions
-----------

This document uses sentences written in *italic text* to denote design decisions
that were decided upon during previous design meetings. These are choices
that should discussed within the development team should it become necessary to
diverege from them.

Image database objects
----------------------

The app "cases" contains two types of database objects to store a single image
in database:

- :class:`cases.models.Image`
- :class:`cases.models.ImageFile`

In the current design, the Image-object denotes a container object for an image.
This image can have one or more *representations*. A representation consists of one
or more files with a given data type, which are stored as ImageFile objects
that belong to a given Image object. A data type might thereby consist of
more than one file, like for example is the case for multislice-dicom files.
Therefore, an application must enumerate all ImageFiles with a given type to
access all the full image data that uses the given data type. It can safely be
assumed that:

* *An Image will only include a single set of ImageFile objects for a given data type.*
* *The data type is stored for each ImageFile in the image_type field.*

Abstract, descriptive information about an image can typically be queried on the
Image object directly. Examples are: resolution of the image, color space,
modality, and more. However, in the future it might become necessary to move
some of these descriptors to the ImageFile-level, in case we include data
types that constrain the possible values of any of these descriptors. Therefore:

* *Generally, we should not include image types in grand-challenge that limit the choice of values for any of the Image-object descriptor fields.*

However, in case, we ever need to include a restrictive data representation to
our database:

* *We will move Image-level descriptive fields to ImageFile-fields.*
* *This will be decided upon on a case-by-case basis.*
* *Only required fields will be moved (most descriptive fields should remain on the Image object).*

At the moment of writing (2019-08) all image types that are supported by
grand-challenge can encode images with any combination of Image-fields. So
data type compatibility between different image representations is currently not
an issue.
