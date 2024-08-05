import json
import logging
import re
from datetime import timedelta
from json import JSONDecodeError
from pathlib import Path
from typing import NamedTuple

from celery import signature
from django import forms
from django.apps import apps
from django.conf import settings
from django.core.exceptions import (
    MultipleObjectsReturned,
    ObjectDoesNotExist,
    ValidationError,
)
from django.core.files import File
from django.core.files.base import ContentFile
from django.core.validators import (
    MaxValueValidator,
    MinValueValidator,
    RegexValidator,
)
from django.db import models, transaction
from django.db.models import Avg, F, IntegerChoices, QuerySet, Sum, TextChoices
from django.db.transaction import on_commit
from django.forms import ModelChoiceField
from django.forms.models import model_to_dict
from django.template.defaultfilters import truncatewords
from django.utils.functional import cached_property
from django.utils.module_loading import import_string
from django.utils.text import get_valid_filename
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from django_deprecate_fields import deprecate_field
from django_extensions.db.fields import AutoSlugField
from panimg.models import MAXIMUM_SEGMENTS_LENGTH

from grandchallenge.cases.models import Image, ImageFile, RawImageUploadSession
from grandchallenge.cases.widgets import FlexibleImageField
from grandchallenge.charts.specs import components_line
from grandchallenge.components.schemas import INTERFACE_VALUE_SCHEMA
from grandchallenge.components.tasks import (
    _repo_login_and_run,
    assign_docker_image_from_upload,
    deprovision_job,
    provision_job,
    validate_docker_image,
)
from grandchallenge.components.validators import (
    validate_no_slash_at_ends,
    validate_safe_path,
)
from grandchallenge.core.models import FieldChangeMixin, UUIDModel
from grandchallenge.core.storage import (
    private_s3_storage,
    protected_s3_storage,
)
from grandchallenge.core.validators import (
    ExtensionValidator,
    JSONSchemaValidator,
    JSONValidator,
    MimeTypeValidator,
)
from grandchallenge.uploads.models import UserUpload
from grandchallenge.uploads.validators import validate_gzip_mimetype
from grandchallenge.workstation_configs.models import (
    OVERLAY_SEGMENTS_SCHEMA,
    LookUpTable,
)

logger = logging.getLogger(__name__)


class InterfaceKindChoices(models.TextChoices):
    """Interface kind choices."""

    STRING = "STR", _("String")
    INTEGER = "INT", _("Integer")
    FLOAT = "FLT", _("Float")
    BOOL = "BOOL", _("Bool")
    ANY = "JSON", _("Anything")
    CHART = "CHART", _("Chart")

    # Annotation Types
    TWO_D_BOUNDING_BOX = "2DBB", _("2D bounding box")
    MULTIPLE_TWO_D_BOUNDING_BOXES = "M2DB", _("Multiple 2D bounding boxes")
    DISTANCE_MEASUREMENT = "DIST", _("Distance measurement")
    MULTIPLE_DISTANCE_MEASUREMENTS = (
        "MDIS",
        _("Multiple distance measurements"),
    )
    POINT = "POIN", _("Point")
    MULTIPLE_POINTS = "MPOI", _("Multiple points")
    POLYGON = "POLY", _("Polygon")
    MULTIPLE_POLYGONS = "MPOL", _("Multiple polygons")
    LINE = "LINE", _("Line")
    MULTIPLE_LINES = "MLIN", _("Multiple lines")
    ANGLE = "ANGL", _("Angle")
    MULTIPLE_ANGLES = "MANG", _("Multiple angles")
    ELLIPSE = "ELLI", _("Ellipse")
    MULTIPLE_ELLIPSES = "MELL", _("Multiple ellipses")
    THREE_POINT_ANGLE = "3ANG", _("Three-point angle")
    MULTIPLE_THREE_POINT_ANGLES = "M3AN", _("Multiple three-point angles")

    # Choice Types
    CHOICE = "CHOI", _("Choice")
    MULTIPLE_CHOICE = "MCHO", _("Multiple choice")

    # Image types
    IMAGE = "IMG", _("Image")
    SEGMENTATION = "SEG", _("Segmentation")
    HEAT_MAP = "HMAP", _("Heat Map")
    DISPLACEMENT_FIELD = "DSPF", _("Displacement field")

    # Registration types
    AFFINE_TRANSFORM_REGISTRATION = "ATRG", _("Affine transform registration")

    # File types
    PDF = "PDF", _("PDF file")
    SQREG = "SQREG", _("SQREG file")
    THUMBNAIL_JPG = "JPEG", _("Thumbnail jpg")
    THUMBNAIL_PNG = "PNG", _("Thumbnail png")
    OBJ = "OBJ", _("OBJ file")
    MP4 = "MP4", _("MP4 file")

    # Legacy support
    CSV = "CSV", _("CSV file")
    ZIP = "ZIP", _("ZIP file")


class InterfaceSuperKindChoices(models.TextChoices):
    IMAGE = "I", "Image"
    FILE = "F", "File"
    VALUE = "V", "Value"


class InterfaceKind:
    """Interface kind."""

    InterfaceKindChoices = InterfaceKindChoices

    @staticmethod
    def interface_type_json():
        """Interface kinds that are json serializable:

        * String
        * Integer
        * Float
        * Bool
        * Anything that is JSON serializable (any object)
        * 2D bounding box
        * Multiple 2D bounding boxes
        * Distance measurement
        * Multiple distance measurements
        * Point
        * Multiple points
        * Polygon
        * Multiple polygons
        * Lines
        * Multiple lines
        * Angle
        * Multiple angles
        * Choice (string)
        * Multiple choice (array of strings)
        * Chart
        * Ellipse
        * Multiple ellipses
        * Affine transform registration

        Example json for 2D bounding box annotation
            required: "type", "corners", "version"
            optional: "name", "probability"

        .. code-block:: json

            {
                "name": "Region of interest",
                "type": "2D bounding box",
                "corners": [
                    [ 130.80001831054688, 148.86666870117188, 0.5009999871253967],
                    [ 69.73332977294922, 148.86666870117188, 0.5009999871253967],
                    [ 69.73332977294922, 73.13333129882812, 0.5009999871253967],
                    [ 130.80001831054688, 73.13333129882812, 0.5009999871253967]
                ],
                "probability": 0.95,
                "version": { "major": 1, "minor": 0 }
            }

        Example json for Multiple 2D bounding boxes annotation
            required: "type", "boxes", "version"
            optional: "name", "probability"

        .. code-block:: json

            {
                "name": "Regions of interest",
                "type": "Multiple 2D bounding boxes",
                "boxes": [
                    {
                        "name": "ROI 1",
                        "corners": [
                            [ 92.66666412353516, 136.06668090820312, 0.5009999871253967],
                            [ 54.79999923706055, 136.06668090820312, 0.5009999871253967],
                            [ 54.79999923706055, 95.53333282470703, 0.5009999871253967],
                            [ 92.66666412353516, 95.53333282470703, 0.5009999871253967]
                        ],
                        "probability": 0.95
                    },
                    {
                        "name": "ROI 2",
                        "corners": [
                            [ 92.66666412353516, 136.06668090820312, 0.5009999871253967],
                            [ 54.79999923706055, 136.06668090820312, 0.5009999871253967],
                            [ 54.79999923706055, 95.53333282470703, 0.5009999871253967],
                            [ 92.66666412353516, 95.53333282470703, 0.5009999871253967]
                        ],
                        "probability": 0.92
                    }
                ],
                "version": { "major": 1, "minor": 0 }
            }

        Example json for Distance measurement annotation
            required: "type", "start", "end", "version"
            optional: "name", "probability"

        .. code-block:: json

            {
                "name": "Distance between areas",
                "type": "Distance measurement",
                "start": [ 59.79176712036133, 78.76753997802734, 0.5009999871253967 ],
                "end": [ 69.38014221191406, 143.75546264648438, 0.5009999871253967 ],
                "probability": 0.92,
                "version": { "major": 1, "minor": 0 }
            }

        Example json for Multiple distance measurement annotation
            required: "type", "lines", "version"
            optional: "name", "probability"

        .. code-block:: json

            {
                "name": "Distances between areas",
                "type": "Multiple distance measurements",
                "lines": [
                    {
                        "name": "Distance 1",
                        "start": [ 49.733333587646484, 103.26667022705078, 0.5009999871253967 ],
                        "end": [ 55.06666564941406, 139.26666259765625, 0.5009999871253967 ],
                        "probability": 0.92
                    },
                    {
                        "name": "Distance 2",
                        "start": [ 49.733333587646484, 103.26667022705078, 0.5009999871253967 ],
                        "end": [ 55.06666564941406, 139.26666259765625, 0.5009999871253967 ],
                        "probability": 0.92
                    }
                ],
                "version": { "major": 1, "minor": 0 }
            }

        Example json for Point annotation
            required: "type", "point", "version"
            optional: "name", "probability"

        .. code-block:: json

            {
                "name": "Point of interest",
                "type": "Point",
                "point": [ 152.13333129882812, 111.0, 0.5009999871253967 ],
                "probability": 0.92,
                "version": { "major": 1, "minor": 0 }
            }

        Example json for Multiple points annotation
            required: "type", "points", "version"
            optional: "name", "probability"

        .. code-block:: json

            {
                "name": "Points of interest",
                "type": "Multiple points",
                "points": [
                    {
                        "name": "Point 1",
                        "point": [
                            96.0145263671875, 79.83292388916016, 0.5009999871253967
                        ],
                        "probability": 0.92
                    },
                    {
                        "name": "Point 2",
                        "point": [
                            130.10653686523438, 115.52300262451172, 0.5009999871253967
                        ],
                        "probability": 0.92
                    }
                ],
                "version": { "major": 1, "minor": 0 }
            }

        Example json for Polygon annotation
            required: "type", "seed_point", "path_points", "sub_type", "groups", "version"
            optional: "name", "probability"

        .. code-block:: json

            {
                "name": "Area of interest",
                "type": "Polygon",
                "seed_point": [ 76.413756408691, 124.014717102050, 0.5009999871253967 ],
                "path_points": [
                    [ 76.41375842260106, 124.01471710205078, 0.5009999871253967 ],
                    [ 76.41694876387268, 124.0511828696491, 0.5009999871253967 ],
                    [ 76.42642285078242, 124.0865406433515, 0.5009999871253967 ]
                ],
                "sub_type": "brush",
                "groups": [],
                "probability": 0.92,
                "version": { "major": 1, "minor": 0 }
            }

        Example json for Multiple polygon annotation
            required: "type", "polygons", "version"
            optional: "name", "probability"

        .. code-block:: json

            {
                "name": "Areas of interest",
                "type": "Multiple polygons",
                "polygons": [
                    {
                        "name": "Area 1",
                        "seed_point": [ 55.82666793823242, 90.46666717529297, 0.5009999871253967 ],
                        "path_points": [
                            [ 55.82667599387105, 90.46666717529297, 0.5009999871253967 ],
                            [ 55.93921357544119, 90.88666314747366, 0.5009999871253967 ],
                            [ 56.246671966051736, 91.1941215380842, 0.5009999871253967 ],
                            [ 56.66666793823242, 91.30665911965434, 0.5009999871253967 ]
                        ],
                        "sub_type": "brush",
                        "groups": [ "manual"],
                        "probability": 0.67
                    },
                    {
                        "name": "Area 2",
                        "seed_point": [ 90.22666564941406, 96.06666564941406, 0.5009999871253967 ],
                        "path_points": [
                            [ 90.22667370505269, 96.06666564941406, 0.5009999871253967 ],
                            [ 90.33921128662283, 96.48666162159475, 0.5009999871253967 ],
                            [ 90.64666967723338, 96.7941200122053, 0.5009999871253967 ]
                        ],
                        "sub_type": "brush",
                        "groups": [],
                        "probability": 0.92
                    }
                ],
                "version": { "major": 1, "minor": 0 }
            }

        Example json for Line annotation
            required: "type", "seed_points", "path_point_lists", "version"
            optional: "name", "probability"

        .. code-block:: json

            {
                "name": "Some annotation",
                "type": "Line",
                "seed_points": [[1, 2, 3], [1, 2, 3]],
                "path_point_lists": [
                    [[5, 6, 7], [8, 9, 10], [1, 0, 10], [2, 4, 2]],
                    [[5, 6, 7], [8, 9, 10], [1, 0, 10], [2, 4, 2]]
                ],
                "probability": 0.92
                "version": { "major": 1, "minor": 0 }
            }

        Example json for Multiple lines annotation
            required: "type", "lines", "version"
            optional: "name", "probability"

        .. code-block:: json

            {
                "name": "Some annotations",
                "type": "Multiple lines",
                "lines": [
                    {
                        "name": "Annotation 1",
                        "seed_points": [[1, 2, 3], [1, 2, 3]],
                        "path_point_lists": [
                            [[5, 6, 7], [8, 9, 10], [1, 0, 10], [2, 4, 2]],
                            [[5, 6, 7], [8, 9, 10], [1, 0, 10], [2, 4, 2]],
                        ],
                        "probability": 0.78
                    },
                    {
                        "name": "Annotation 2",
                        "seed_points": [[1, 2, 3], [1, 2, 3]],
                        "path_point_lists": [
                            [[5, 6, 7], [8, 9, 10], [1, 0, 10], [2, 4, 2]],
                            [[5, 6, 7], [8, 9, 10], [1, 0, 10], [2, 4, 2]],
                        ],
                        "probability": 0.92
                    }
                ],
                "version": { "major": 1, "minor": 0 }
            }

        Example json for Angle annotation
            required: "type", "lines", "version"
            optional: "name", "probability"

        .. code-block:: json

            {
                "name": "Some angle",
                "type": "Angle",
                "lines": [[[180, 10, 0.5], [190, 10, 0.5]],[[180, 25, 0.5], [190, 15, 0.5]]],
                "probability": 0.92,
                "version": {"major": 1, "minor": 0}
            }

        Example json for Multiple angles annotation
            required: "type", "angles", "version"
            optional: "name", "probability"

        .. code-block:: json

            {
                "name": "Some angles",
                "type": "Multiple angles",
                "angles": [
                    {
                        "name": "First angle",
                        "lines": [[[110, 135, 0.5], [60, 165, 0.5]],[[70, 25, 0.5], [85, 65, 0.5]]],
                        "probability": 0.82
                    },
                    {
                        "name": "Second angle",
                        "lines": [[[130, 210, 0.5], [160, 130, 0.5]], [[140, 40, 0.5], [180, 75, 0.5]]],
                        "probability": 0.52
                    },
                    {
                        "name": "Third angle",
                        "lines": [[[20, 30, 0.5], [20, 100, 0.5]], [[180, 200, 0.5], [210, 200, 0.5]]],
                        "probability": 0.98
                    }
                ],
                "version": {"major": 1, "minor": 0}
            }

        Example json for Ellipse annotation
            required: "type", "major_axis", "minor_axis", "version"
            optional: "name", "probability"

        .. code-block:: json

            {
                "name": "Some ellipse",
                "type": "Ellipse",
                "major_axis": [[-10, 606, 0.5], [39, 559, 0.5]],
                "minor_axis": [[2, 570, 0.5], [26, 595, 0.5]],
                "probability": 0.92,
                "version": {"major": 1, "minor": 0}
            }

        Example json for Multiple ellipse annotation
            required: "type", "ellipses", "version"
            optional: "name", "probability"

        .. code-block:: json

            {
                "name": "Some ellipse",
                "type": "Multiple ellipses",
                "ellipses": [
                    {
                        "major_axis": [[-44, 535, 0.5], [-112, 494, 0.5]],
                        "minor_axis": [[-88, 532, 0.5], [-68, 497, 0.5]],
                        "probability": 0.69
                    },
                    {
                        "major_axis": [[-17, 459, 0.5], [-94, 436, 0.5]],
                        "minor_axis": [[-61, 467, 0.5], [-50, 428, 0.5]],
                        "probability": 0.92
                    }
                ],
                "version": {"major": 1, "minor": 0}
            }

        Example json for Three-point angle annotation
            required: "type", "angle", "version"
            optional: "name", "probability"

        .. code-block:: json

            {
                "name": "Some 3-point angle",
                "type": "Three-point angle",
                "angle": [[177, 493, 0.5], [22, 489, 0.5], [112, 353, 0.5]],
                "probability": 0.003,
                "version": {"major": 1, "minor": 0}
            }

        Example json for Three-point angle annotation
            required: "type", "angles", "version"
            optional: "name", "probability"

        .. code-block:: json

            {
                "name": "Multiple 3-point angles",
                "type": "Multiple three-point angles",
                "angles": [
                    {
                        "name": "first",
                        "angle": [[300, 237, 0.5], [263, 282, 0.5], [334, 281, 0.5]],
                        "probability": 0.92
                    },
                    {
                        "name": "second",
                        "angle": [[413, 237, 0.5], [35, 160, 0.5], [367, 293, 0.5]],
                        "probability": 0.69
                    }
                ],
                "version": {"major": 1, "minor": 0}
            }

        Example json for Chart (for more examples, see `here<https://vega.github.io/vega-lite/examples/>` and `here<https://grand-challenge.org/blogs/visualisations-for-challenges/>`)

        .. code-block:: json

            {
               "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
               "width": 300,
               "height": 300,
               "data": {
                  "values": [
                     {
                        "target": "Negative",
                        "prediction": "Negative",
                        "value": 198
                     },
                     {
                        "target": "Negative",
                        "prediction": "Positive",
                        "value": 9
                     },
                     {
                        "target": "Positive",
                        "prediction": "Negative",
                        "value": 159
                     },
                     {
                        "target": "Positive",
                        "prediction": "Positive",
                        "value": 376
                     }
                  ],
                  "format": {
                     "type": "json"
                  }
               },
               "layer": [
                  {
                     "mark": "rect",
                     "encoding": {
                        "y": {
                           "field": "target",
                           "type": "ordinal"
                        },
                        "x": {
                           "field": "prediction",
                           "type": "ordinal"
                        },
                        "color": {
                           "field": "value",
                           "type": "quantitative",
                           "title": "Count of Records",
                           "legend": {
                              "direction": "vertical",
                              "gradientLength": 300
                           }
                        }
                     }
                  },
                  {
                     "mark": "text",
                     "encoding": {
                        "y": {
                           "field": "target",
                           "type": "ordinal"
                        },
                        "x": {
                           "field": "prediction",
                           "type": "ordinal"
                        },
                        "text": {
                           "field": "value",
                           "type": "quantitative"
                        },
                        "color": {
                           "condition": {
                              "test": "datum['value'] < 40",
                              "value": "black"
                           },
                           "value": "white"
                        }
                     }
                  }
               ],
               "config": {
                  "axis": {
                     "grid": true,
                     "tickBand": "extent"
                  }
               }
            }

        Example json for Ellipse annotation
            required: "type", "major_axis, "minor_axis" "version"
            optional: "name", "probability"

        .. code-block:: json

            {
                "name": "an Ellipse",
                "type": "Ellipse",
                "major_axis": [[ 130, 148.86, 0.50], [10, 10, 0]],
                "minor_axis": [[ 69.73, 148.86, 0.50], [10, 0, 0]],
                "probability": 0.95,
                "version": { "major": 1, "minor": 0 }
            }

        Example json for Multiple ellipses annotation
            required: "type", "ellipses", "version"
            optional: "name", "probability"

        .. code-block:: json

            {
                "name": "Some Ellipses",
                "type": "Multiple ellipses",
                "ellipses": [
                    {
                        "name": "First Ellipse",
                        "major axis": [[10, 10, 0.5], [10, 20, 0]],
                        "minor_axis": [[10, 20, 0.5], [10.6, 0, 0]],
                        "probability": 0.82
                    },
                    {
                        "name": "Second Ellipse",
                        "major axis": [[10, 10, 0.5], [10, 20, 0]],
                        "minor_axis": [[10, 20, 0.5], [10.6, 0, 0]],
                        "probability": 0.52
                    },
                    {
                        "name": "Third Ellipse",
                        "major axis": [[10, 10, 0.5], [10, 20, 0]],
                        "minor_axis": [[10, 20, 0.5], [10.6, 0, 0]],
                        "probability": 0.98
                    }
                ],
                "version": {"major": 1, "minor": 0}
            }

        Example json for an Affine Transform Registration
            required: "3d_affine_transform"

        .. code-block:: json

            {
                "3d_affine_transform": [
                    [1, 0, 0, 0],
                    [0, 1, 0, 0],
                    [0, 0, 1, 0],
                    [0, 0, 0, 1]
                ]
            }

        """
        return {
            InterfaceKind.InterfaceKindChoices.STRING,
            InterfaceKind.InterfaceKindChoices.INTEGER,
            InterfaceKind.InterfaceKindChoices.FLOAT,
            InterfaceKind.InterfaceKindChoices.BOOL,
            InterfaceKind.InterfaceKindChoices.TWO_D_BOUNDING_BOX,
            InterfaceKind.InterfaceKindChoices.MULTIPLE_TWO_D_BOUNDING_BOXES,
            InterfaceKind.InterfaceKindChoices.DISTANCE_MEASUREMENT,
            InterfaceKind.InterfaceKindChoices.MULTIPLE_DISTANCE_MEASUREMENTS,
            InterfaceKind.InterfaceKindChoices.POINT,
            InterfaceKind.InterfaceKindChoices.MULTIPLE_POINTS,
            InterfaceKind.InterfaceKindChoices.POLYGON,
            InterfaceKind.InterfaceKindChoices.MULTIPLE_POLYGONS,
            InterfaceKind.InterfaceKindChoices.CHOICE,
            InterfaceKind.InterfaceKindChoices.MULTIPLE_CHOICE,
            InterfaceKind.InterfaceKindChoices.ANY,
            InterfaceKind.InterfaceKindChoices.CHART,
            InterfaceKind.InterfaceKindChoices.LINE,
            InterfaceKind.InterfaceKindChoices.MULTIPLE_LINES,
            InterfaceKind.InterfaceKindChoices.ANGLE,
            InterfaceKind.InterfaceKindChoices.MULTIPLE_ANGLES,
            InterfaceKind.InterfaceKindChoices.ELLIPSE,
            InterfaceKind.InterfaceKindChoices.MULTIPLE_ELLIPSES,
            InterfaceKind.InterfaceKindChoices.THREE_POINT_ANGLE,
            InterfaceKind.InterfaceKindChoices.MULTIPLE_THREE_POINT_ANGLES,
            InterfaceKind.InterfaceKindChoices.AFFINE_TRANSFORM_REGISTRATION,
        }

    @staticmethod
    def interface_type_image():
        """Interface kinds that are images:

        * Image
        * Heat Map
        * Segmentation
        """
        return {
            InterfaceKind.InterfaceKindChoices.IMAGE,
            InterfaceKind.InterfaceKindChoices.HEAT_MAP,
            InterfaceKind.InterfaceKindChoices.SEGMENTATION,
            InterfaceKind.InterfaceKindChoices.DISPLACEMENT_FIELD,
        }

    @staticmethod
    def interface_type_file():
        """Interface kinds that are files:

        * CSV file
        * ZIP file
        * PDF file
        * SQREG file
        * Thumbnail JPG
        * Thumbnail PNG
        * OBJ file
        * MP4 file
        """
        return {
            InterfaceKind.InterfaceKindChoices.CSV,
            InterfaceKind.InterfaceKindChoices.ZIP,
            InterfaceKind.InterfaceKindChoices.PDF,
            InterfaceKind.InterfaceKindChoices.SQREG,
            InterfaceKind.InterfaceKindChoices.THUMBNAIL_JPG,
            InterfaceKind.InterfaceKindChoices.THUMBNAIL_PNG,
            InterfaceKind.InterfaceKindChoices.OBJ,
            InterfaceKind.InterfaceKindChoices.MP4,
        }

    @staticmethod
    def interface_type_mandatory_isolation():
        """Interfaces that can only be displayed in isolation."""
        return {
            InterfaceKind.InterfaceKindChoices.CHART,
            InterfaceKind.InterfaceKindChoices.PDF,
            InterfaceKind.InterfaceKindChoices.THUMBNAIL_JPG,
            InterfaceKind.InterfaceKindChoices.THUMBNAIL_PNG,
            InterfaceKind.InterfaceKindChoices.MP4,
        }

    @staticmethod
    def interface_type_undisplayable():
        """Interfaces that cannot be displayed."""
        return {
            InterfaceKind.InterfaceKindChoices.CSV,
            InterfaceKind.InterfaceKindChoices.ZIP,
            InterfaceKind.InterfaceKindChoices.OBJ,
        }


class OverlaySegmentsMixin(models.Model):
    overlay_segments = models.JSONField(
        blank=True,
        default=list,
        help_text=(
            "The schema that defines how categories of values in the overlay "
            "images are differentiated."
        ),
        validators=[JSONValidator(schema=OVERLAY_SEGMENTS_SCHEMA)],
    )
    look_up_table = models.ForeignKey(
        to=LookUpTable,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        help_text="The look-up table that is applied when an overlay image is first shown",
    )

    @property
    def overlay_segments_allowed_values(self):
        allowed_values = {x["voxel_value"] for x in self.overlay_segments}
        # An implicit background value of 0 is always allowed, this saves the
        # user having to declare it and the annotator mark it
        allowed_values.add(0)

        return allowed_values

    @property
    def overlay_segments_is_contiguous(self):
        values = sorted(list(self.overlay_segments_allowed_values))
        return all(
            values[i] - values[i - 1] == 1 for i in range(1, len(values))
        )

    def _validate_voxel_values(self, image):
        if not self.overlay_segments:
            return

        if image.segments is None:
            raise ValidationError(
                "Image segments could not be determined, ensure the voxel values "
                "are integers and that it contains no more than "
                f"{MAXIMUM_SEGMENTS_LENGTH} segments. Ensure the image has the "
                "minimum and maximum voxel values set as tags if the image is a TIFF "
                "file."
            )

        invalid_values = (
            set(image.segments) - self.overlay_segments_allowed_values
        )
        if invalid_values:
            raise ValidationError(
                f"The valid voxel values for this segmentation are: "
                f"{self.overlay_segments_allowed_values}. This segmentation is "
                f"invalid as it contains the voxel values: {invalid_values}."
            )

    def _validate_vector_field(self, image: Image):
        if len(image.shape) != 4:
            raise ValidationError(
                "Deformation and displacement must be 4D images."
            )
        if image.shape_without_color != image.shape:
            raise ValidationError(
                "Deformation and displacement fields cannot have a color component."
            )
        if image.shape[0] != 3:
            raise ValidationError(
                "Deformation and displacement field's 4th dimension "
                "must be a 3-component vector."
            )

    class Meta:
        abstract = True


class ComponentInterface(OverlaySegmentsMixin):
    Kind = InterfaceKind.InterfaceKindChoices
    SuperKind = InterfaceSuperKindChoices

    title = models.CharField(
        max_length=255,
        help_text="Human readable name of this input/output field.",
        unique=True,
    )
    slug = AutoSlugField(populate_from="title")
    description = models.TextField(
        blank=True, help_text="Description of this input/output field."
    )
    default_value = models.JSONField(
        blank=True,
        null=True,
        default=None,
        help_text="Default value for this field, only valid for inputs.",
    )
    schema = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Additional JSON schema that the values for this interface must "
            "satisfy. See https://json-schema.org/. "
            "Only Draft 7, 6, 4 or 3 are supported."
        ),
        validators=[JSONSchemaValidator()],
    )
    kind = models.CharField(
        blank=False,
        max_length=5,
        choices=Kind.choices,
        help_text=(
            "What is the type of this interface? Used to validate interface "
            "values and connections between components."
        ),
    )
    relative_path = models.CharField(
        max_length=255,
        help_text=(
            "The path to the entity that implements this interface relative "
            "to the input or output directory."
        ),
        unique=True,
        validators=[
            validate_safe_path,
            validate_no_slash_at_ends,
            # No uuids in path
            RegexValidator(
                regex=r".*[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}.*",
                inverse_match=True,
                flags=re.IGNORECASE,
            ),
        ],
    )
    store_in_database = models.BooleanField(
        default=True,
        editable=True,
        help_text=(
            "Should the value be saved in a database field, "
            "only valid for outputs."
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._overlay_segments_orig = self.overlay_segments

    def __str__(self):
        return f"{self.title} ({self.get_kind_display()})"

    @property
    def is_image_kind(self):
        return self.kind in InterfaceKind.interface_type_image()

    @property
    def is_json_kind(self):
        return self.kind in InterfaceKind.interface_type_json()

    @property
    def is_file_kind(self):
        return self.kind in InterfaceKind.interface_type_file()

    @property
    def is_thumbnail_kind(self):
        return self.kind in [
            InterfaceKindChoices.THUMBNAIL_JPG,
            InterfaceKindChoices.THUMBNAIL_PNG,
        ]

    @property
    def is_previewable(self):
        return self.store_in_database and self.kind in [
            InterfaceKindChoices.BOOL,
            InterfaceKindChoices.FLOAT,
            InterfaceKindChoices.INTEGER,
            InterfaceKindChoices.STRING,
        ]

    @property
    def super_kind(self):
        if self.saved_in_object_store:
            if self.is_image_kind:
                return InterfaceSuperKindChoices.IMAGE
            else:
                return InterfaceSuperKindChoices.FILE
        else:
            return InterfaceSuperKindChoices.VALUE

    @property
    def saved_in_object_store(self):
        # files and images should always be saved to S3, others are optional
        return (
            self.is_image_kind
            or self.is_file_kind
            or not self.store_in_database
        )

    @property
    def requires_file(self):
        return (
            self.is_file_kind
            or self.is_json_kind
            and not self.store_in_database
        )

    @property
    def default_field(self):
        if self.requires_file:
            return ModelChoiceField
        elif self.is_image_kind:
            return FlexibleImageField
        elif self.kind in {
            InterfaceKind.InterfaceKindChoices.STRING,
            InterfaceKind.InterfaceKindChoices.CHOICE,
        }:
            return forms.CharField
        elif self.kind == InterfaceKind.InterfaceKindChoices.INTEGER:
            return forms.IntegerField
        elif self.kind == InterfaceKind.InterfaceKindChoices.FLOAT:
            return forms.FloatField
        elif self.kind == InterfaceKind.InterfaceKindChoices.BOOL:
            return forms.BooleanField
        else:
            return forms.JSONField

    @property
    def file_mimetypes(self):
        if self.kind == InterfaceKind.InterfaceKindChoices.CSV:
            return (
                "application/csv",
                "application/vnd.ms-excel",
                "text/csv",
                "text/plain",
            )
        elif self.kind == InterfaceKind.InterfaceKindChoices.ZIP:
            return ("application/zip", "application/x-zip-compressed")
        elif self.kind == InterfaceKind.InterfaceKindChoices.PDF:
            return ("application/pdf",)
        elif self.kind == InterfaceKind.InterfaceKindChoices.THUMBNAIL_JPG:
            return ("image/jpeg",)
        elif self.kind == InterfaceKind.InterfaceKindChoices.THUMBNAIL_PNG:
            return ("image/png",)
        elif self.kind == InterfaceKind.InterfaceKindChoices.SQREG:
            return (
                "application/octet-stream",
                "application/x-sqlite3",
                "application/vnd.sqlite3",
            )
        elif self.kind == InterfaceKind.InterfaceKindChoices.OBJ:
            return ("text/plain", "application/octet-stream")
        elif self.kind in InterfaceKind.interface_type_json():
            return (
                "text/plain",
                "application/json",
            )
        elif self.kind == InterfaceKind.InterfaceKindChoices.MP4:
            return ("video/mp4",)
        else:
            raise RuntimeError(f"Unknown kind {self.kind}")

    def create_instance(self, *, image=None, value=None, fileobj=None):
        civ = ComponentInterfaceValue.objects.create(interface=self)

        if image:
            civ.image = image
        elif fileobj:
            container = File(fileobj)
            civ.file.save(Path(self.relative_path).name, container)
        elif self.saved_in_object_store:
            civ.file = ContentFile(
                json.dumps(value).encode("utf-8"),
                name=Path(self.relative_path).name,
            )
        else:
            civ.value = value

        civ.full_clean()
        civ.save()

        return civ

    def clean(self):
        super().clean()
        self._clean_overlay_segments()
        self._clean_store_in_database()
        self._clean_relative_path()

    def _clean_overlay_segments(self):
        if (
            self.kind == InterfaceKindChoices.SEGMENTATION
            and not self.overlay_segments
        ):
            raise ValidationError(
                "Overlay segments must be set for this interface"
            )

        if (
            self.kind != InterfaceKindChoices.SEGMENTATION
            and self.overlay_segments
        ):
            raise ValidationError(
                "Overlay segments should only be set for segmentations"
            )

        if not self.overlay_segments_is_contiguous:
            raise ValidationError(
                "Voxel values for overlay segments must be contiguous."
            )

        Question = apps.get_model("reader_studies", "question")  # noqa: N806
        if (
            self.pk is not None
            and self._overlay_segments_orig != self.overlay_segments
            and (
                ComponentInterfaceValue.objects.filter(interface=self).exists()
                or Question.objects.filter(interface=self).exists()
            )
        ):
            raise ValidationError(
                "Overlay segments cannot be changed, as values or questions "
                "for this ComponentInterface exist."
            )

    def _clean_relative_path(self):
        if self.is_json_kind:
            if not self.relative_path.endswith(".json"):
                raise ValidationError("Relative path should end with .json")
        elif self.is_file_kind and not self.relative_path.endswith(
            f".{self.kind.lower()}"
        ):
            raise ValidationError(
                f"Relative path should end with .{self.kind.lower()}"
            )

        if self.is_image_kind:
            if not self.relative_path.startswith("images/"):
                raise ValidationError(
                    "Relative path should start with images/"
                )
            if Path(self.relative_path).name != Path(self.relative_path).stem:
                # Maybe not in the future
                raise ValidationError("Images should be a directory")
        else:
            if self.relative_path.startswith("images/"):
                raise ValidationError(
                    "Relative path should not start with images/"
                )

    def _clean_store_in_database(self):
        object_store_required = self.kind in {
            *InterfaceKind.interface_type_image(),
            *InterfaceKind.interface_type_file(),
            # These values can be large, so for any new interfaces of this
            # type always add them to the object store
            InterfaceKind.InterfaceKindChoices.MULTIPLE_TWO_D_BOUNDING_BOXES,
            InterfaceKind.InterfaceKindChoices.MULTIPLE_DISTANCE_MEASUREMENTS,
            InterfaceKind.InterfaceKindChoices.MULTIPLE_POINTS,
            InterfaceKind.InterfaceKindChoices.MULTIPLE_POLYGONS,
            InterfaceKind.InterfaceKindChoices.MULTIPLE_LINES,
            InterfaceKind.InterfaceKindChoices.MULTIPLE_ANGLES,
            InterfaceKind.InterfaceKindChoices.MULTIPLE_ELLIPSES,
            InterfaceKind.InterfaceKindChoices.MULTIPLE_THREE_POINT_ANGLES,
        }

        if object_store_required and self.store_in_database:
            raise ValidationError(
                f"Interface {self.kind} objects cannot be stored in the database"
            )

    def validate_against_schema(self, *, value):
        """Validates values against both default and custom schemas"""
        JSONValidator(
            schema={
                **INTERFACE_VALUE_SCHEMA,
                "anyOf": [{"$ref": f"#/definitions/{self.kind}"}],
            }
        )(value=value)

        if self.schema:
            JSONValidator(schema=self.schema)(value=value)

    @cached_property
    def value_required(self):
        value_required = True
        if not self.is_image_kind and not self.requires_file:
            try:
                self.validate_against_schema(value=None)
                value_required = False
            except ValidationError:
                pass
        elif self.kind == InterfaceKindChoices.BOOL:
            value_required = False
        return value_required

    class Meta:
        ordering = ("pk",)


def component_interface_value_path(instance, filename):
    # Convert the pk to a hex, padded to 4 chars with zeros
    pk_as_padded_hex = f"{instance.pk:04x}"

    return (
        f"{instance._meta.app_label.lower()}/"
        f"{instance._meta.model_name.lower()}/"
        f"{pk_as_padded_hex[-4:-2]}/{pk_as_padded_hex[-2:]}/{instance.pk}/"
        f"{get_valid_filename(filename)}"
    )


class ComponentInterfaceValue(models.Model):
    """Encapsulates the value of an interface at a certain point in the graph."""

    id = models.BigAutoField(primary_key=True)
    interface = models.ForeignKey(
        to=ComponentInterface, on_delete=models.PROTECT
    )
    value = models.JSONField(null=True, blank=True, default=None)
    file = models.FileField(
        null=True,
        blank=True,
        upload_to=component_interface_value_path,
        storage=protected_s3_storage,
        validators=[
            ExtensionValidator(
                allowed_extensions=(
                    ".json",
                    ".zip",
                    ".csv",
                    ".png",
                    ".jpg",
                    ".jpeg",
                    ".pdf",
                    ".sqreg",
                    ".obj",
                    ".mp4",
                )
            ),
            MimeTypeValidator(
                allowed_types=(
                    "application/json",
                    "application/zip",
                    "text/plain",
                    "application/csv",
                    "text/csv",
                    "application/pdf",
                    "image/png",
                    "image/jpeg",
                    "application/octet-stream",
                    "application/x-sqlite3",
                    "application/vnd.sqlite3",
                    "video/mp4",
                )
            ),
        ],
    )
    image = models.ForeignKey(
        to=Image, null=True, blank=True, on_delete=models.PROTECT
    )

    storage_cost_per_year_usd_millicents = deprecate_field(
        models.PositiveIntegerField(
            # We store usd here as the exchange rate regularly changes
            editable=False,
            null=True,
            default=None,
            help_text="The storage cost per year for this image in USD Cents, excluding Tax",
        )
    )
    size_in_storage = models.PositiveBigIntegerField(
        editable=False,
        default=0,
        help_text="The number of bytes stored in the storage backend",
    )

    _user_upload_validated = False

    @property
    def title(self):
        if self.value is not None:
            return str(self.value)
        if self.file:
            return Path(self.file.name).name
        if self.image:
            return self.image.name
        return ""

    @property
    def has_value(self):
        return self.value is not None or self.image or self.file

    @property
    def decompress(self):
        """
        Should the CIV be decompressed?

        This is only for legacy support of zip file submission for
        prediction evaluation. We should not support this anywhere
        else as it clobbers the input directory.
        """
        return self.interface.kind == InterfaceKindChoices.ZIP

    @cached_property
    def image_file(self):
        """The single image file for this interface"""
        return (
            self.image.files.filter(
                image_type__in=[
                    ImageFile.IMAGE_TYPE_MHD,
                    ImageFile.IMAGE_TYPE_TIFF,
                ]
            )
            .get()
            .file
        )

    @property
    def relative_path(self):
        """
        Where should the file be located?

        Images need special handling as their names are fixed.
        """
        path = Path(self.interface.relative_path)

        if self.image:
            path /= Path(self.image_file.name).name

        return path

    def __str__(self):
        if self.value is None:
            return self.title
        else:
            return f"Component Interface Value {self.pk} for {self.interface}"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._value_orig = self.value
        self._image_orig = self._dict["image"]
        self._file_orig = self.file

    @property
    def _dict(self):
        return model_to_dict(
            self, fields=[field.name for field in self._meta.fields]
        )

    def save(self, *args, **kwargs):
        if (
            (
                self._value_orig not in (None, self.interface.default_value)
                and self.value is not None
                and self._value_orig != self.value
            )
            or (self._image_orig and self._image_orig != self.image.pk)
            or (
                self._file_orig.name not in (None, "")
                and self._file_orig != self.file
            )
        ):
            raise ValidationError(
                "You cannot change the value, file or image of an existing CIV. "
                "Please create a new CIV instead."
            )

        if self._file_orig != self.file:
            self.update_size_in_storage()

        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        attributes = [
            attribute
            for attribute in [self.value, self.image, self.file.name]
            if attribute is not None
            if attribute != ""
        ]
        if len(attributes) > 1:
            raise ValidationError(
                "Only one of image, value and file can be defined."
            )

        if self.interface.is_image_kind:
            self._validate_image_only()
            if self.interface.kind == InterfaceKindChoices.SEGMENTATION:
                self.interface._validate_voxel_values(self.image)
            if self.interface.kind == InterfaceKindChoices.DISPLACEMENT_FIELD:
                self.interface._validate_vector_field(self.image)
        elif self.interface.is_file_kind:
            self._validate_file_only()
        else:
            self._validate_value()

    def _validate_image_only(self):
        if not self.image:
            raise ValidationError("Image must be set")
        if self.file or self.value is not None:
            raise ValidationError(
                f"File ({self.file}) or value should not be set for images"
            )

    def _validate_file_only(self):
        if not self._user_upload_validated and not self.file:
            raise ValidationError("File must be set")
        if self.image or self.value is not None:
            raise ValidationError(
                f"Image ({self.image}) or value must not be set for files"
            )

    def _validate_value_only(self):
        # Do not check self.value here, it can be anything including None.
        # This is checked later with interface.validate_against_schema.
        if self.image or self.file:
            raise ValidationError(
                f"Image ({self.image}) or file ({self.file}) must not be set for values"
            )

    def _validate_value(self):
        if self._user_upload_validated:
            return
        if self.interface.saved_in_object_store:
            self._validate_file_only()
            with self.file.open("r") as f:
                try:
                    value = json.loads(f.read().decode("utf-8"))
                except JSONDecodeError as e:
                    raise ValidationError(e)
        else:
            self._validate_value_only()
            value = self.value

        self.interface.validate_against_schema(value=value)

    def validate_user_upload(self, user_upload):
        if not user_upload.is_completed:
            raise ValidationError("User upload is not completed.")
        if self.interface.is_json_kind:
            try:
                value = json.loads(user_upload.read_object())
            except JSONDecodeError as e:
                raise ValidationError(e)
            self.interface.validate_against_schema(value=value)
        self._user_upload_validated = True

    def update_size_in_storage(self):
        if self.file:
            self.size_in_storage = self.file.size
        else:
            raise NotImplementedError

    class Meta:
        ordering = ("pk",)


class ComponentJobManager(models.QuerySet):
    def with_duration(self):
        """Annotate the queryset with the duration of completed jobs"""
        return self.annotate(duration=F("completed_at") - F("started_at"))

    def average_duration(self):
        """Calculate the average duration that completed jobs ran for"""
        return (
            self.with_duration()
            .exclude(duration=None)
            .aggregate(Avg("duration"))["duration__avg"]
        )

    def total_duration(self):
        return (
            self.with_duration()
            .exclude(duration=None)
            .aggregate(Sum("duration"))["duration__sum"]
        )

    def active(self):
        return self.exclude(
            status__in=[
                ComponentJob.SUCCESS,
                ComponentJob.CANCELLED,
                ComponentJob.FAILURE,
            ]
        )


class ComponentJob(models.Model):
    # The job statuses come directly from celery.result.AsyncResult.status:
    # http://docs.celeryproject.org/en/latest/reference/celery.result.html
    PENDING = 0
    STARTED = 1
    RETRY = 2
    FAILURE = 3
    SUCCESS = 4
    CANCELLED = 5
    PROVISIONING = 6
    PROVISIONED = 7
    EXECUTING = 8
    EXECUTED = 9
    PARSING = 10
    EXECUTING_PREREQUISITES = 11

    STATUS_CHOICES = (
        (PENDING, "Queued"),
        (STARTED, "Started"),
        (RETRY, "Re-Queued"),
        (FAILURE, "Failed"),
        (SUCCESS, "Succeeded"),
        (CANCELLED, "Cancelled"),
        (PROVISIONING, "Provisioning"),
        (PROVISIONED, "Provisioned"),
        (EXECUTING, "Executing"),
        (EXECUTED, "Executed"),
        (PARSING, "Parsing Outputs"),
        (EXECUTING_PREREQUISITES, "Executing Algorithm"),
    )

    status = models.PositiveSmallIntegerField(
        choices=STATUS_CHOICES, default=PENDING, db_index=True
    )
    attempt = models.PositiveSmallIntegerField(editable=False, default=0)
    stdout = models.TextField()
    stderr = models.TextField(default="")
    runtime_metrics = models.JSONField(default=dict, editable=False)
    error_message = models.CharField(max_length=1024, default="")
    detailed_error_message = models.JSONField(
        blank=True, null=True, default=None
    )
    started_at = models.DateTimeField(null=True)
    completed_at = models.DateTimeField(null=True)
    compute_cost_euro_millicents = models.PositiveIntegerField(
        # We store euro here as the costs were incurred at a time when
        # the exchange rate may have been different
        editable=False,
        null=True,
        default=None,
        help_text="The total compute cost for this job in Euro Cents, including Tax",
    )
    input_prefixes = models.JSONField(
        default=dict,
        editable=False,
        help_text=(
            "Map of the ComponentInterfaceValue id to the path prefix to use "
            "for this input, e.g. {'1': 'foo/bar/'} will place CIV 1 at "
            "/input/foo/bar/<relative_path>"
        ),
    )
    task_on_success = models.JSONField(
        default=None,
        null=True,
        editable=False,
        help_text="Serialized task that is run on job success",
    )
    task_on_failure = models.JSONField(
        default=None,
        null=True,
        editable=False,
        help_text="Serialized task that is run on job failure",
    )
    time_limit = models.PositiveIntegerField(
        help_text="Time limit for the job in seconds",
        validators=[
            MinValueValidator(
                limit_value=settings.COMPONENTS_MINIMUM_JOB_DURATION
            ),
            MaxValueValidator(
                limit_value=settings.COMPONENTS_MAXIMUM_JOB_DURATION
            ),
        ],
    )

    inputs = models.ManyToManyField(
        to=ComponentInterfaceValue,
        related_name="%(app_label)s_%(class)ss_as_input",
    )
    outputs = models.ManyToManyField(
        to=ComponentInterfaceValue,
        related_name="%(app_label)s_%(class)ss_as_output",
    )

    objects = ComponentJobManager.as_manager()

    def update_status(  # noqa: C901
        self,
        *,
        status: STATUS_CHOICES,
        stdout: str = "",
        stderr: str = "",
        error_message="",
        detailed_error_message=None,
        duration: timedelta | None = None,
        compute_cost_euro_millicents=None,
        runtime_metrics=None,
    ):
        self.status = status

        if stdout:
            self.stdout = stdout

        if stderr:
            self.stderr = stderr

        if error_message:
            self.error_message = error_message[:1024]

        if detailed_error_message:
            self.detailed_error_message = {
                str(key): value
                for key, value in detailed_error_message.items()
            }

        if (
            status in [self.STARTED, self.EXECUTING]
            and self.started_at is None
        ):
            self.started_at = now()
        elif (
            status
            in [self.EXECUTED, self.SUCCESS, self.FAILURE, self.CANCELLED]
            and self.completed_at is None
        ):
            self.completed_at = now()
            if duration and self.started_at:
                # TODO: maybe add separate timings for provisioning, executing, parsing and total
                self.started_at = self.completed_at - duration

        if compute_cost_euro_millicents is not None:
            self.compute_cost_euro_millicents = compute_cost_euro_millicents

        if runtime_metrics is not None:
            self.runtime_metrics = runtime_metrics

        self.save()

        if self.status == self.SUCCESS:
            on_commit(self.execute_task_on_success)
        elif self.status in [self.FAILURE, self.CANCELLED]:
            on_commit(self.execute_task_on_failure)

    @property
    def executor_kwargs(self):
        return {
            "job_id": f"{self._meta.app_label}-{self._meta.model_name}-{self.pk}-{self.attempt:02}",
            "exec_image_repo_tag": self.container.shimmed_repo_tag,
            "memory_limit": self.container.requires_memory_gb,
            "time_limit": self.time_limit,
            "requires_gpu": self.container.requires_gpu,
            "desired_gpu_type": self.container.desired_gpu_type,
        }

    def get_executor(self, *, backend):
        Executor = import_string(backend)  # noqa: N806
        return Executor(**self.executor_kwargs)

    @property
    def container(self) -> "ComponentImage":
        """
        Returns the container object associated with this instance, which
        should be a foreign key to an object that is a subclass of
        ComponentImage
        """
        raise NotImplementedError

    @property
    def output_interfaces(self) -> QuerySet:
        """Returns an unevaluated QuerySet for the output interfaces"""
        raise NotImplementedError

    @property
    def signature_kwargs(self):
        return {
            "kwargs": {
                "job_pk": str(self.pk),
                "job_app_label": self._meta.app_label,
                "job_model_name": self._meta.model_name,
                "backend": settings.COMPONENTS_DEFAULT_BACKEND,
            },
            "immutable": True,
        }

    def execute(self):
        return provision_job.signature(**self.signature_kwargs).apply_async()

    def execute_task_on_success(self):
        deprovision_job.signature(**self.signature_kwargs).apply_async()
        if self.task_on_success:
            signature(self.task_on_success).apply_async()

    def execute_task_on_failure(self):
        deprovision_job.signature(**self.signature_kwargs).apply_async()
        if self.task_on_failure:
            signature(self.task_on_failure).apply_async()

    @property
    def animate(self):
        return self.status in {
            self.STARTED,
            self.PROVISIONING,
            self.PROVISIONED,
            self.EXECUTING,
            self.EXECUTED,
            self.PARSING,
            self.EXECUTING_PREREQUISITES,
        }

    @property
    def status_context(self):
        if self.status == self.SUCCESS:
            if self.stderr:
                return "warning"
            else:
                return "success"
        elif self.status in {self.FAILURE, self.CANCELLED}:
            return "danger"
        elif self.status in {
            self.PENDING,
            self.STARTED,
            self.RETRY,
            self.PROVISIONING,
            self.PROVISIONED,
            self.EXECUTING,
            self.EXECUTED,
            self.PARSING,
            self.EXECUTING_PREREQUISITES,
        }:
            return "info"
        else:
            return "secondary"

    @property
    def runtime_metrics_chart(self):
        instance_metrics = self.runtime_metrics["instance"]
        cpu_limit = 100 * instance_metrics["cpu"]

        if instance_metrics["gpus"]:
            gpu_str = (
                f"{instance_metrics['gpus']}x {instance_metrics['gpu_type']}"
            )
        else:
            gpu_str = "No"
        title = f"{instance_metrics['name']} / {instance_metrics['cpu']} CPU / {instance_metrics['memory']} GB Memory / {gpu_str} GPU"

        return components_line(
            values=[
                {
                    "Metric": metric["label"],
                    "Timestamp": timestamp,
                    "Percent": value / 100.0,
                }
                for metric in self.runtime_metrics["metrics"]
                for timestamp, value in zip(
                    metric["timestamps"], metric["values"], strict=True
                )
            ],
            title=title,
            cpu_limit=cpu_limit,
            tooltip=[
                {
                    "field": metric["label"],
                    "type": "quantitative",
                    "format": ".2%",
                }
                for metric in self.runtime_metrics["metrics"]
            ],
        )

    class Meta:
        abstract = True


def docker_image_path(instance, filename):
    return (
        f"docker/"
        f"images/"
        f"{instance._meta.app_label.lower()}/"
        f"{instance._meta.model_name.lower()}/"
        f"{instance.pk}/"
        f"{get_valid_filename(filename)}"
    )


class ImportStatusChoices(IntegerChoices):
    INITIALIZED = 0, "Initialized"
    QUEUED = 1, "Queued"
    RETRY = 2, "Re-Queued"
    STARTED = 3, "Started"
    CANCELLED = 4, "Cancelled"
    FAILED = 5, "Failed"
    COMPLETED = 6, "Completed"


class ComponentImageManager(models.Manager):
    def executable_images(self):
        return self.filter(is_manifest_valid=True, is_in_registry=True)

    def active_images(self):
        return self.executable_images().filter(is_desired_version=True)


class GPUTypeChoices(TextChoices):
    A100 = "A100"
    A10G = "A10G"
    V100 = "V100"
    K80 = "K80"
    T4 = "T4"


class ComponentImage(FieldChangeMixin, models.Model):
    SHIM_IMAGE = True

    ImportStatusChoices = ImportStatusChoices
    GPUTypeChoices = GPUTypeChoices

    objects = ComponentImageManager()

    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL
    )
    user_upload = models.ForeignKey(
        UserUpload, blank=True, null=True, on_delete=models.SET_NULL
    )
    image = models.FileField(
        blank=True,
        upload_to=docker_image_path,
        validators=[
            ExtensionValidator(
                allowed_extensions=(".tar", ".tar.gz", ".tar.xz")
            )
        ],
        help_text=(
            ".tar.gz archive of the container image produced from the command "
            "'docker save IMAGE | gzip -c > IMAGE.tar.gz'. See "
            "https://docs.docker.com/engine/reference/commandline/save/"
        ),
        storage=private_s3_storage,
    )
    image_sha256 = models.CharField(editable=False, max_length=71)
    latest_shimmed_version = models.CharField(
        editable=False, max_length=8, default=""
    )

    import_status = models.PositiveSmallIntegerField(
        choices=ImportStatusChoices.choices,
        default=ImportStatusChoices.INITIALIZED,
        db_index=True,
    )
    is_manifest_valid = models.BooleanField(
        default=None,
        null=True,
        editable=False,
        help_text="Is this image's manifest valid?",
    )
    is_in_registry = models.BooleanField(
        default=False,
        editable=False,
        help_text="Is this image in the container registry?",
    )
    status = models.TextField(editable=False)

    storage_cost_per_year_usd_millicents = deprecate_field(
        models.PositiveIntegerField(
            # We store usd here as the exchange rate regularly changes
            editable=False,
            null=True,
            default=None,
            help_text="The storage cost per year for this image in USD Cents, excluding Tax",
        )
    )

    size_in_storage = models.PositiveBigIntegerField(
        editable=False,
        default=0,
        help_text="The number of bytes stored in the storage backend",
    )
    size_in_registry = models.PositiveBigIntegerField(
        editable=False,
        default=0,
        help_text="The number of bytes stored in the registry",
    )

    requires_gpu = models.BooleanField(default=False)
    desired_gpu_type = models.CharField(
        max_length=4,
        choices=GPUTypeChoices.choices,
        default=GPUTypeChoices.T4,
        help_text="If this image requires a GPU, what GPU type would it like to use?",
    )
    requires_memory_gb = models.PositiveIntegerField(default=4)

    comment = models.TextField(
        blank=True,
        default="",
        help_text="Add any information (e.g. version ID) about this image here.",
    )
    is_desired_version = models.BooleanField(default=False, editable=False)

    def __str__(self):
        out = f"{self._meta.verbose_name.title()} {self.pk}"

        if self.comment:
            out += f" ({truncatewords(self.comment, 4)})"

        return out

    @cached_property
    def can_execute(self):
        return (
            self.__class__.objects.executable_images()
            .filter(pk=self.pk)
            .exists()
        )

    @property
    def linked_file(self):
        return self.image

    def clear_can_execute_cache(self):
        try:
            del self.can_execute
        except AttributeError:
            pass

    def save(self, *args, **kwargs):
        image_needs_validation = (
            self.import_status == ImportStatusChoices.INITIALIZED
            and self.is_manifest_valid is None
        )
        validate_image_now = False

        if self.initial_value("image"):
            if self.has_changed("image"):
                raise RuntimeError("The image cannot be changed")
            if image_needs_validation:
                self.import_status = ImportStatusChoices.QUEUED
                validate_image_now = True
        elif self.image and image_needs_validation:
            self.import_status = ImportStatusChoices.QUEUED
            validate_image_now = True

        if self.has_changed("image") or self.has_changed("is_in_registry"):
            self.update_size_in_storage()

        super().save(*args, **kwargs)

        if validate_image_now:
            on_commit(
                validate_docker_image.signature(
                    kwargs={
                        "app_label": self._meta.app_label,
                        "model_name": self._meta.model_name,
                        "pk": self.pk,
                        "mark_as_desired": True,
                    },
                    immutable=True,
                ).apply_async
            )

    def assign_docker_image_from_upload(self):
        on_commit(
            assign_docker_image_from_upload.signature(
                kwargs={
                    "app_label": self._meta.app_label,
                    "model_name": self._meta.model_name,
                    "pk": self.pk,
                }
            ).apply_async
        )

    def get_peer_images(self):
        raise NotImplementedError

    @transaction.atomic
    def mark_desired_version(self):
        self.clear_can_execute_cache()
        if self.is_manifest_valid and self.can_execute:
            images = self.get_peer_images()

            for image in images:
                if image == self:
                    image.is_desired_version = True
                else:
                    image.is_desired_version = False

            self.__class__.objects.bulk_update(images, ["is_desired_version"])

        else:
            raise RuntimeError(
                "Tried to mark invalid image as desired version."
            )

    @property
    def original_repo_tag(self):
        """The tag of this image in the container repository"""
        return (
            f"{settings.COMPONENTS_REGISTRY_URL}/"
            f"{settings.COMPONENTS_REGISTRY_PREFIX}/"
            f"{self._meta.app_label}/{self._meta.model_name}:{self.pk}"
        )

    @property
    def shimmed_repo_tag(self):
        return f"{self.original_repo_tag}-{self.latest_shimmed_version}"

    class Meta:
        abstract = True

    @property
    def animate(self):
        return self.import_status == self.ImportStatusChoices.STARTED

    @property
    def import_status_context(self):
        if self.import_status == self.ImportStatusChoices.COMPLETED:
            return "success"
        elif self.import_status in {
            self.ImportStatusChoices.FAILED,
            self.ImportStatusChoices.CANCELLED,
        }:
            return "danger"
        elif self.import_status in {
            self.ImportStatusChoices.INITIALIZED,
            self.ImportStatusChoices.QUEUED,
            self.ImportStatusChoices.RETRY,
            self.ImportStatusChoices.STARTED,
        }:
            return "info"
        else:
            return "secondary"

    def calculate_size_in_registry(self):
        if self.is_in_registry:
            command = _repo_login_and_run(
                command=["crane", "manifest", self.original_repo_tag]
            )
            manifest = json.loads(command.stdout)
            return (
                sum(layer["size"] for layer in manifest["layers"])
                + manifest["config"]["size"]
            )
        else:
            return 0

    def update_size_in_storage(self):
        if not self.image:
            self.size_in_storage = 0
            self.size_in_registry = 0
        else:
            self.size_in_storage = self.image.size
            self.size_in_registry = self.calculate_size_in_registry()


class CIVSetStringRepresentationMixin:
    def __str__(self):
        result = [str(self.pk)]

        if self.title:
            result.append(f"{self.title!r}")

        result.append(self.__content_str)
        return ", ".join(result)

    @property
    def __content_str(self):
        civs = self.values.all()
        nr = len(civs)
        if nr == 0:
            return "No content"

        if nr > 5:
            return "5+ items"

        content = [f"{civ.interface.title}: {civ.title[:30]}" for civ in civs]
        return ", ".join(content)


class CIVSetObjectPermissionsMixin:
    @property
    def view_perm(self):
        return f"view_{self._meta.model_name}"

    @property
    def change_perm(self):
        return f"change_{self._meta.model_name}"

    @property
    def delete_perm(self):
        return f"delete_{self._meta.model_name}"

    def save(self, *args, **kwargs):
        adding = self._state.adding
        super().save(*args, **kwargs)

        if adding:
            self.assign_permissions()

    def assign_permissions(self):
        raise NotImplementedError


class CIVForObjectMixin:
    def create_civ(self, *, ci_slug, new_value, user=None):
        ci = ComponentInterface.objects.get(slug=ci_slug)
        try:
            current_civ = self.values.filter(interface=ci).get()
        except ObjectDoesNotExist:
            current_civ = None
        except MultipleObjectsReturned as e:
            raise e

        if ci.is_json_kind and not ci.requires_file:
            return self.create_civ_for_value(
                ci=ci, current_civ=current_civ, new_value=new_value
            )
        elif ci.is_image_kind:
            return self.create_civ_for_image(
                ci=ci, current_civ=current_civ, new_value=new_value, user=user
            )
        elif ci.requires_file:
            return self.create_civ_for_file(
                ci=ci, current_civ=current_civ, new_value=new_value
            )
        else:
            NotImplementedError(f"CIV creation for {ci} not handled.")

    def create_civ_for_value(self, *, ci, current_civ, new_value):
        current_value = current_civ.value if current_civ else None
        civ = ComponentInterfaceValue(interface=ci, value=new_value)
        if current_value != new_value or (
            current_civ is None and new_value is None
        ):
            try:
                civ.full_clean()
                civ.save()
                self.values.remove(current_civ)
                self.values.add(civ)
            except ValidationError as e:
                if new_value:
                    raise e
                else:
                    self.values.remove(current_civ)

    def create_civ_for_image(self, *, ci, current_civ, new_value, user):
        current_image = current_civ.image if current_civ else None
        if isinstance(new_value, Image) and current_image != new_value:
            self.values.remove(current_civ)
            civ, created = ComponentInterfaceValue.objects.get_or_create(
                interface=ci, image=new_value
            )
            if created:
                civ.full_clean()
            self.values.add(civ)
        elif isinstance(new_value, (QuerySet, RawImageUploadSession)):
            # Local import to avoid circular dependency
            from grandchallenge.components.tasks import add_image_to_object

            if isinstance(new_value, RawImageUploadSession):
                upload_session = new_value
            else:
                upload_session = RawImageUploadSession.objects.create(
                    creator=user
                )
                upload_session.user_uploads.set(new_value)

            upload_session.process_images(
                linked_task=add_image_to_object.signature(
                    kwargs={
                        "app_label": self._meta.app_label,
                        "model_name": self._meta.model_name,
                        "object_pk": self.pk,
                        "interface_pk": str(ci.pk),
                    },
                    immutable=True,
                )
            )

    def create_civ_for_file(self, *, ci, current_civ, new_value):
        if (
            isinstance(new_value, ComponentInterfaceValue)
            and current_civ != new_value
        ):
            self.values.remove(current_civ)
            self.values.add(new_value)
        elif isinstance(new_value, UserUpload):
            from grandchallenge.components.tasks import add_file_to_object

            transaction.on_commit(
                add_file_to_object.signature(
                    kwargs={
                        "app_label": self._meta.app_label,
                        "model_name": self._meta.model_name,
                        "user_upload_pk": str(new_value.pk),
                        "interface_pk": str(ci.pk),
                        "object_pk": self.pk,
                        "civ_pk": current_civ.pk if current_civ else None,
                    }
                ).apply_async
            )
        elif not new_value:
            # if no new value is provided (user selects '---' in dropdown)
            # delete old CIV
            self.values.remove(current_civ)


class InterfacesAndValues(NamedTuple):
    interfaces: set
    values: dict


class ValuesForInterfacesMixin:
    @property
    def civ_sets_related_manager(self):
        raise NotImplementedError

    @cached_property
    def interfaces_and_values(self):
        vals = list(
            self.civ_sets_related_manager.select_related(
                "values", "values__interface", "values__image"
            )
            .filter(values__interface__slug__isnull=False)
            .values(
                "values__interface__slug",
                "values__id",
            )
            .order_by("values__id")
            .distinct()
        )
        interfaces = [x["values__interface__slug"] for x in vals]
        return InterfacesAndValues(interfaces=set(interfaces), values=vals)

    @cached_property
    def values_for_interfaces(self):
        interfaces_and_values = self.interfaces_and_values
        values_for_interfaces = {
            interface: [
                x["values__id"]
                for x in interfaces_and_values.values
                if x["values__interface__slug"] == interface
            ]
            for interface in interfaces_and_values.interfaces
        }
        return values_for_interfaces


class Tarball(UUIDModel):
    ImportStatusChoices = ImportStatusChoices

    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL
    )
    import_status = models.PositiveSmallIntegerField(
        choices=ImportStatusChoices.choices,
        default=ImportStatusChoices.INITIALIZED,
        db_index=True,
    )
    status = models.TextField(editable=False)
    user_upload = models.ForeignKey(
        UserUpload,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        validators=[validate_gzip_mimetype],
    )
    sha256 = models.CharField(editable=False, max_length=71)
    size_in_storage = models.PositiveBigIntegerField(
        editable=False,
        default=0,
        help_text="The number of bytes stored in the storage backend",
    )
    comment = models.TextField(
        blank=True,
        default="",
        help_text="Add any information (e.g. version ID) about this object here.",
    )
    is_desired_version = models.BooleanField(default=False, editable=False)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        adding = self._state.adding

        super().save(*args, **kwargs)

        if adding:
            self.assign_permissions()

    def assign_permissions(self):
        raise NotImplementedError

    def get_absolute_url(self):
        raise NotImplementedError

    def get_peer_tarballs(self):
        raise NotImplementedError

    @property
    def linked_file(self):
        raise NotImplementedError

    @transaction.atomic
    def mark_desired_version(self, peer_tarballs=None):
        peer_tarballs = list(peer_tarballs or self.get_peer_tarballs())
        for tb in peer_tarballs:
            tb.is_desired_version = False
        self.is_desired_version = True
        peer_tarballs.append(self)
        self.__class__.objects.bulk_update(
            peer_tarballs, ["is_desired_version"]
        )

    @property
    def import_status_context(self):
        if self.import_status == ImportStatusChoices.COMPLETED:
            return "success"
        elif self.import_status in {
            ImportStatusChoices.FAILED,
            ImportStatusChoices.CANCELLED,
        }:
            return "danger"
        else:
            return "info"

    @property
    def import_in_progress(self):
        return self.import_status == ImportStatusChoices.INITIALIZED
