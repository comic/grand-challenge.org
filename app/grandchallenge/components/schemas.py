ANSWER_TYPE_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "definitions": {
        "null": {"type": "null"},
        "TEXT": {"type": "string"},
        "STXT": {"type": "string"},
        "MTXT": {"type": "string"},
        "BOOL": {"type": "boolean"},
        "NUMB": {"type": "number"},
        "HEAD": {"type": "null"},
        "CHOI": {"type": "number"},
        "MCHO": {"type": "array", "items": {"type": "number"}},
        "MCHD": {"type": "array", "items": {"type": "number"}},
        "2DBB": {
            "type": "object",
            "properties": {
                "type": {"enum": ["2D bounding box"]},
                "corners": {
                    "type": "array",
                    "items": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 3,
                        "maxItems": 3,
                    },
                    "minItems": 4,
                    "maxItems": 4,
                },
                "name": {"type": "string"},
                "version": {"$ref": "#/definitions/version-object"},
                "probability": {"type": "number", "minimum": 0, "maximum": 1},
            },
            "required": ["version", "type", "corners"],
            "additionalProperties": False,
        },
        "line-object": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "type": {"enum": ["Distance measurement"]},
                "start": {
                    "type": "array",
                    "items": {"type": "number"},
                    "minItems": 3,
                    "maxItems": 3,
                },
                "end": {
                    "type": "array",
                    "items": {"type": "number"},
                    "minItems": 3,
                    "maxItems": 3,
                },
                "probability": {"type": "number", "minimum": 0, "maximum": 1},
            },
            "required": ["start", "end"],
            "additionalProperties": False,
        },
        "point-object": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "type": {"enum": ["Point"]},
                "point": {
                    "type": "array",
                    "items": {"type": "number"},
                    "minItems": 3,
                    "maxItems": 3,
                },
                "probability": {"type": "number", "minimum": 0, "maximum": 1},
            },
            "required": ["point"],
            "additionalProperties": False,
        },
        "polygon-object": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "type": {"enum": ["Polygon"]},
                "seed_point": {
                    "type": "array",
                    "items": {"type": "number"},
                    "minItems": 3,
                    "maxItems": 3,
                },
                "path_points": {
                    "type": "array",
                    "items": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 3,
                        "maxItems": 3,
                    },
                },
                "sub_type": {"type": "string"},
                "groups": {"type": "array", "items": {"type": "string"}},
                "probability": {"type": "number", "minimum": 0, "maximum": 1},
            },
            "required": ["seed_point", "path_points", "sub_type", "groups"],
            "additionalProperties": False,
        },
        "spline-object": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "type": {"enum": ["Line"]},
                "seed_points": {
                    "type": "array",
                    "items": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 3,
                        "maxItems": 3,
                    },
                },
                "path_point_lists": {
                    "type": "array",
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "array",
                            "items": {"type": "number"},
                            "minItems": 3,
                            "maxItems": 3,
                        },
                    },
                },
                "probability": {"type": "number", "minimum": 0, "maximum": 1},
            },
            "required": ["seed_points", "path_point_lists"],
            "additionalProperties": False,
        },
        "angle-object": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "type": {"enum": ["Angle"]},
                "lines": {
                    "type": "array",
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "array",
                            "items": {"type": "number"},
                            "minItems": 3,
                            "maxItems": 3,
                        },
                        "minItems": 2,
                        "maxItems": 2,
                    },
                    "minItems": 2,
                    "maxItems": 2,
                },
                "probability": {"type": "number", "minimum": 0, "maximum": 1},
            },
            "required": ["lines"],
            "additionalProperties": False,
        },
        "DIST": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "type": {"enum": ["Distance measurement"]},
                "start": {
                    "type": "array",
                    "items": {"type": "number"},
                    "minItems": 3,
                    "maxItems": 3,
                },
                "end": {
                    "type": "array",
                    "items": {"type": "number"},
                    "minItems": 3,
                    "maxItems": 3,
                },
                "version": {"$ref": "#/definitions/version-object"},
                "probability": {"type": "number", "minimum": 0, "maximum": 1},
            },
            "required": ["version", "type", "start", "end"],
            "additionalProperties": False,
        },
        "MDIS": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "type": {"enum": ["Multiple distance measurements"]},
                "lines": {
                    "type": "array",
                    "items": {
                        "allOf": [{"$ref": "#/definitions/line-object"}]
                    },
                },
                "version": {"$ref": "#/definitions/version-object"},
            },
            "required": ["version", "type", "lines"],
            "additionalProperties": False,
        },
        "POIN": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "type": {"enum": ["Point"]},
                "point": {
                    "type": "array",
                    "items": {"type": "number"},
                    "minItems": 3,
                    "maxItems": 3,
                },
                "version": {"$ref": "#/definitions/version-object"},
                "probability": {"type": "number", "minimum": 0, "maximum": 1},
            },
            "required": ["version", "type", "point"],
            "additionalProperties": False,
        },
        "MPOI": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "type": {"enum": ["Multiple points"]},
                "points": {
                    "type": "array",
                    "items": {
                        "allOf": [{"$ref": "#/definitions/point-object"}]
                    },
                },
                "version": {"$ref": "#/definitions/version-object"},
            },
            "required": ["version", "type", "points"],
            "additionalProperties": False,
        },
        "POLY": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "type": {"enum": ["Polygon"]},
                "seed_point": {
                    "type": "array",
                    "items": {"type": "number"},
                    "minItems": 3,
                    "maxItems": 3,
                },
                "path_points": {
                    "type": "array",
                    "items": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 3,
                        "maxItems": 3,
                    },
                },
                "sub_type": {"type": "string"},
                "groups": {"type": "array", "items": {"type": "string"}},
                "version": {"$ref": "#/definitions/version-object"},
                "probability": {"type": "number", "minimum": 0, "maximum": 1},
            },
            "required": [
                "seed_point",
                "path_points",
                "sub_type",
                "groups",
                "type",
                "version",
            ],
            "additionalProperties": False,
        },
        "MPOL": {
            "type": "object",
            "properties": {
                "type": {"enum": ["Multiple polygons"]},
                "name": {"type": "string"},
                "polygons": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/polygon-object"},
                },
                "version": {"$ref": "#/definitions/version-object"},
            },
            "required": ["type", "version", "polygons"],
            "additionalProperties": False,
        },
        "LINE": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "type": {"enum": ["Line"]},
                "seed_points": {
                    "type": "array",
                    "items": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 3,
                        "maxItems": 3,
                    },
                },
                "path_point_lists": {
                    "type": "array",
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "array",
                            "items": {"type": "number"},
                            "minItems": 3,
                            "maxItems": 3,
                        },
                    },
                },
                "version": {"$ref": "#/definitions/version-object"},
                "probability": {"type": "number", "minimum": 0, "maximum": 1},
            },
            "required": ["seed_points", "path_point_lists", "type", "version"],
            "additionalProperties": False,
        },
        "MLIN": {
            "type": "object",
            "properties": {
                "type": {"enum": ["Multiple lines"]},
                "name": {"type": "string"},
                "lines": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/spline-object"},
                },
                "version": {"$ref": "#/definitions/version-object"},
            },
            "required": ["type", "version", "lines"],
            "additionalProperties": False,
        },
        "ANGL": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "type": {"enum": ["Angle"]},
                "lines": {
                    "type": "array",
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "array",
                            "items": {"type": "number"},
                            "minItems": 3,
                            "maxItems": 3,
                        },
                        "minItems": 2,
                        "maxItems": 2,
                    },
                    "minItems": 2,
                    "maxItems": 2,
                },
                "version": {"$ref": "#/definitions/version-object"},
                "probability": {"type": "number", "minimum": 0, "maximum": 1},
            },
            "required": ["lines", "version", "type"],
            "additionalProperties": False,
        },
        "MANG": {
            "type": "object",
            "properties": {
                "type": {"enum": ["Multiple angles"]},
                "name": {"type": "string"},
                "angles": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/angle-object"},
                },
                "version": {"$ref": "#/definitions/version-object"},
            },
            "required": ["type", "version", "angles"],
            "additionalProperties": False,
        },
        "MASK": {
            "type": "object",
            "properties": {
                "upload_session_pk": {"type": "string", "format": "uuid"}
            },
            "required": ["upload_session_pk"],
            "additionalProperties": False,
        },
        "2D-bounding-box-object": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "type": {"enum": ["2D bounding box"]},
                "corners": {
                    "type": "array",
                    "items": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 3,
                        "maxItems": 3,
                    },
                    "minItems": 4,
                    "maxItems": 4,
                },
                "probability": {"type": "number", "minimum": 0, "maximum": 1},
            },
            "required": ["corners"],
            "additionalProperties": False,
        },
        "M2DB": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "type": {"enum": ["Multiple 2D bounding boxes"]},
                "boxes": {
                    "type": "array",
                    "items": {
                        "allOf": [
                            {"$ref": "#/definitions/2D-bounding-box-object"}
                        ]
                    },
                },
                "version": {"$ref": "#/definitions/version-object"},
            },
            "required": ["version", "type", "boxes"],
            "additionalProperties": False,
        },
        "ELLI": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "type": {"enum": ["Ellipse"]},
                "major_axis": {
                    "type": "array",
                    "items": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 3,
                        "maxItems": 3,
                    },
                    "minItems": 2,
                    "maxItems": 2,
                },
                "minor_axis": {
                    "type": "array",
                    "items": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 3,
                        "maxItems": 3,
                    },
                    "minItems": 2,
                    "maxItems": 2,
                },
                "version": {"$ref": "#/definitions/version-object"},
                "probability": {"type": "number", "minimum": 0, "maximum": 1},
            },
            "required": ["version", "type", "major_axis", "minor_axis"],
            "additionalProperties": False,
        },
        "ellipse-object": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "type": {"enum": ["Ellipse"]},
                "major_axis": {
                    "type": "array",
                    "items": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 3,
                        "maxItems": 3,
                    },
                    "minItems": 2,
                    "maxItems": 2,
                },
                "minor_axis": {
                    "type": "array",
                    "items": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 3,
                        "maxItems": 3,
                    },
                    "minItems": 2,
                    "maxItems": 2,
                },
                "probability": {"type": "number", "minimum": 0, "maximum": 1},
            },
            "required": ["major_axis", "minor_axis"],
            "additionalProperties": False,
        },
        "MELL": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "type": {"enum": ["Multiple ellipses"]},
                "ellipses": {
                    "type": "array",
                    "items": {
                        "allOf": [{"$ref": "#/definitions/ellipse-object"}]
                    },
                },
                "version": {"$ref": "#/definitions/version-object"},
            },
            "required": ["version", "type", "ellipses"],
            "additionalProperties": False,
        },
        "3-point-angle-object": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "type": {"const": "Three-point angle"},
                "angle": {
                    "type": "array",
                    "items": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 3,
                        "maxItems": 3,
                    },
                    "minItems": 3,
                    "maxItems": 3,
                },
                "probability": {"type": "number", "minimum": 0, "maximum": 1},
            },
            "required": ["angle"],
            "additionalProperties": False,
        },
        "3ANG": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "type": {"const": "Three-point angle"},
                "angle": {
                    "type": "array",
                    "items": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 3,
                        "maxItems": 3,
                    },
                    "minItems": 3,
                    "maxItems": 3,
                },
                "version": {"$ref": "#/definitions/version-object"},
                "probability": {"type": "number", "minimum": 0, "maximum": 1},
            },
            "required": ["version", "type", "angle"],
            "additionalProperties": False,
        },
        "M3AN": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "type": {"enum": ["Multiple three-point angles"]},
                "angles": {
                    "type": "array",
                    "items": {
                        "allOf": [
                            {"$ref": "#/definitions/3-point-angle-object"}
                        ]
                    },
                },
                "version": {"$ref": "#/definitions/version-object"},
            },
            "required": ["version", "type", "angles"],
            "additionalProperties": False,
        },
        "version-object": {
            "type": "object",
            "properties": {
                "major": {"type": "number", "minimum": 0, "multipleOf": 1.0},
                "minor": {"type": "number", "minimum": 0, "multipleOf": 1.0},
            },
            "required": ["major", "minor"],
            "additionalProperties": False,
        },
    },
    # anyOf should exist, check Question.is_answer_valid
    "anyOf": [
        {"$ref": "#/definitions/null"},
        {"$ref": "#/definitions/STXT"},
        {"$ref": "#/definitions/MTXT"},
        {"$ref": "#/definitions/BOOL"},
        {"$ref": "#/definitions/NUMB"},
        {"$ref": "#/definitions/HEAD"},
        {"$ref": "#/definitions/2DBB"},
        {"$ref": "#/definitions/DIST"},
        {"$ref": "#/definitions/MDIS"},
        {"$ref": "#/definitions/POIN"},
        {"$ref": "#/definitions/MPOI"},
        {"$ref": "#/definitions/POLY"},
        {"$ref": "#/definitions/MPOL"},
        {"$ref": "#/definitions/CHOI"},
        {"$ref": "#/definitions/MCHO"},
        {"$ref": "#/definitions/MCHD"},
        {"$ref": "#/definitions/M2DB"},
        {"$ref": "#/definitions/MASK"},
        {"$ref": "#/definitions/LINE"},
        {"$ref": "#/definitions/MLIN"},
        {"$ref": "#/definitions/ANGL"},
        {"$ref": "#/definitions/MANG"},
        {"$ref": "#/definitions/ELLI"},
        {"$ref": "#/definitions/MELL"},
        {"$ref": "#/definitions/3ANG"},
        {"$ref": "#/definitions/M3AN"},
    ],
}

VEGA_LITE_SCHEMA = {
    "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
    "$ref": "https://vega.github.io/schema/vega-lite/v5.json",
}

INTERFACE_VALUE_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "definitions": {
        "STR": {"type": "string"},
        "INT": {"type": "integer"},
        "FLT": {"type": "number"},
        "BOOL": {"type": "boolean"},
        "JSON": {},
        "2DBB": ANSWER_TYPE_SCHEMA["definitions"]["2DBB"],
        "M2DB": ANSWER_TYPE_SCHEMA["definitions"]["M2DB"],
        "DIST": ANSWER_TYPE_SCHEMA["definitions"]["DIST"],
        "MDIS": ANSWER_TYPE_SCHEMA["definitions"]["MDIS"],
        "POIN": ANSWER_TYPE_SCHEMA["definitions"]["POIN"],
        "MPOI": ANSWER_TYPE_SCHEMA["definitions"]["MPOI"],
        "POLY": ANSWER_TYPE_SCHEMA["definitions"]["POLY"],
        "MPOL": ANSWER_TYPE_SCHEMA["definitions"]["MPOL"],
        "LINE": ANSWER_TYPE_SCHEMA["definitions"]["LINE"],
        "MLIN": ANSWER_TYPE_SCHEMA["definitions"]["MLIN"],
        "ANGL": ANSWER_TYPE_SCHEMA["definitions"]["ANGL"],
        "MANG": ANSWER_TYPE_SCHEMA["definitions"]["MANG"],
        "ELLI": ANSWER_TYPE_SCHEMA["definitions"]["ELLI"],
        "MELL": ANSWER_TYPE_SCHEMA["definitions"]["MELL"],
        "3ANG": ANSWER_TYPE_SCHEMA["definitions"]["3ANG"],
        "M3AN": ANSWER_TYPE_SCHEMA["definitions"]["M3AN"],
        "CHOI": {"type": "string"},
        "MCHO": {"type": "array", "items": {"type": "string"}},
        "CHART": VEGA_LITE_SCHEMA,
        # Support types
        "version-object": ANSWER_TYPE_SCHEMA["definitions"]["version-object"],
        "2D-bounding-box-object": ANSWER_TYPE_SCHEMA["definitions"][
            "2D-bounding-box-object"
        ],
        "line-object": ANSWER_TYPE_SCHEMA["definitions"]["line-object"],
        "point-object": ANSWER_TYPE_SCHEMA["definitions"]["point-object"],
        "polygon-object": ANSWER_TYPE_SCHEMA["definitions"]["polygon-object"],
        "spline-object": ANSWER_TYPE_SCHEMA["definitions"]["spline-object"],
        "angle-object": ANSWER_TYPE_SCHEMA["definitions"]["angle-object"],
        "ellipse-object": ANSWER_TYPE_SCHEMA["definitions"]["ellipse-object"],
        "3-point-angle-object": ANSWER_TYPE_SCHEMA["definitions"][
            "3-point-angle-object"
        ],
    },
    "anyOf": [
        {"$ref": "#/definitions/STR"},
        {"$ref": "#/definitions/INT"},
        {"$ref": "#/definitions/FLT"},
        {"$ref": "#/definitions/BOOL"},
        {"$ref": "#/definitions/JSON"},
        {"$ref": "#/definitions/2DBB"},
        {"$ref": "#/definitions/M2DB"},
        {"$ref": "#/definitions/DIST"},
        {"$ref": "#/definitions/MDIS"},
        {"$ref": "#/definitions/POIN"},
        {"$ref": "#/definitions/MPOI"},
        {"$ref": "#/definitions/POLY"},
        {"$ref": "#/definitions/MPOL"},
        {"$ref": "#/definitions/CHOI"},
        {"$ref": "#/definitions/MCHO"},
        {"$ref": "#/definitions/CHART"},
        {"$ref": "#/definitions/LINE"},
        {"$ref": "#/definitions/MLIN"},
        {"$ref": "#/definitions/ANGL"},
        {"$ref": "#/definitions/MANG"},
        {"$ref": "#/definitions/ELLI"},
        {"$ref": "#/definitions/MELL"},
        {"$ref": "#/definitions/3ANG"},
        {"$ref": "#/definitions/M3AN"},
    ],
}
