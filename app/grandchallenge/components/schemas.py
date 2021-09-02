ANSWER_TYPE_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "definitions": {
        "null": {"type": "null"},
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
                "version",
            ],
            "additionalProperties": False,
        },
        "PIMG": {
            "type": "object",
            "properties": {
                "upload_session_pk": {"type": "string", "format": "uuid"}
            },
            "required": ["upload_session_pk"],
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
        "MPIM": {
            "type": "object",
            "properties": {
                "upload_session_pk": {"type": "string", "format": "uuid"}
            },
            "required": ["upload_session_pk"],
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
        {"$ref": "#/definitions/PIMG"},
        {"$ref": "#/definitions/MPOL"},
        {"$ref": "#/definitions/MPIM"},
        {"$ref": "#/definitions/CHOI"},
        {"$ref": "#/definitions/MCHO"},
        {"$ref": "#/definitions/MCHD"},
        {"$ref": "#/definitions/M2DB"},
        {"$ref": "#/definitions/MASK"},
    ],
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
        "CHOI": {"type": "string"},
        "MCHO": {"type": "array", "items": {"type": "string"}},
        # Support types
        "version-object": ANSWER_TYPE_SCHEMA["definitions"]["version-object"],
        "2D-bounding-box-object": ANSWER_TYPE_SCHEMA["definitions"][
            "2D-bounding-box-object"
        ],
        "line-object": ANSWER_TYPE_SCHEMA["definitions"]["line-object"],
        "point-object": ANSWER_TYPE_SCHEMA["definitions"]["point-object"],
        "polygon-object": ANSWER_TYPE_SCHEMA["definitions"]["polygon-object"],
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
    ],
}
