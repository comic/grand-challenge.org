from django.apps import AppConfig
from django.db.models.signals import post_migrate


def init_default_interfaces(*_, **__):
    from grandchallenge.components.models import ComponentInterface

    default_interfaces = [
        {
            "title": "Generic Medical Image",
            "kind": ComponentInterface.Kind.IMAGE,
            "relative_path": "",
        },
        {
            "title": "Generic Overlay",
            "kind": ComponentInterface.Kind.HEAT_MAP,
            "relative_path": "images",
        },
        {
            "title": "Results JSON File",
            "kind": ComponentInterface.Kind.JSON,
            "relative_path": "results.json",
        },
        {
            "title": "Predictions JSON File",
            "kind": ComponentInterface.Kind.JSON,
            "relative_path": "predictions.json",
        },
        {
            "title": "Predictions CSV File",
            "kind": ComponentInterface.Kind.CSV,
            "relative_path": "predictions.csv",
        },
        {
            "title": "Predictions ZIP File",
            "kind": ComponentInterface.Kind.ZIP,
            "relative_path": "predictions.zip",
        },
        {
            "title": "Metrics JSON File",
            "kind": ComponentInterface.Kind.JSON,
            "relative_path": "metrics.json",
        },
        {
            "title": "Boolean",
            "kind": ComponentInterface.Kind.BOOL,
            "relative_path": "bool",
        },
        {
            "title": "String",
            "kind": ComponentInterface.Kind.STRING,
            "relative_path": "string",
        },
        {
            "title": "Integer",
            "kind": ComponentInterface.Kind.INTEGER,
            "relative_path": "int",
        },
        {
            "title": "Float",
            "kind": ComponentInterface.Kind.FLOAT,
            "relative_path": "float",
        },
        {
            "title": "2D bounding box",
            "kind": ComponentInterface.Kind.TWO_D_BOUNDING_BOX,
            "relative_path": "2d_bounding_box",
        },
        {
            "title": "Multiple 2D bounding boxes",
            "kind": ComponentInterface.Kind.MULTIPLE_TWO_D_BOUNDING_BOXES,
            "relative_path": "multiple_2d_bounding_boxes",
        },
        {
            "title": "Distance measurement",
            "kind": ComponentInterface.Kind.DISTANCE_MEASUREMENT,
            "relative_path": "distance_measurement",
        },
        {
            "title": "Multiple distance measurements",
            "kind": ComponentInterface.Kind.MULTIPLE_DISTANCE_MEASUREMENTS,
            "relative_path": "multiple_distance_measurements",
        },
        {
            "title": "Point",
            "kind": ComponentInterface.Kind.POINT,
            "relative_path": "point",
        },
        {
            "title": "Multiple points",
            "kind": ComponentInterface.Kind.MULTIPLE_POINTS,
            "relative_path": "multiple_points",
        },
        {
            "title": "Polygon",
            "kind": ComponentInterface.Kind.POLYGON,
            "relative_path": "polygon",
        },
        {
            "title": "Multiple polygons",
            "kind": ComponentInterface.Kind.MULTIPLE_POLYGONS,
            "relative_path": "multiple_polygons",
        },
    ]

    for interface in default_interfaces:
        ComponentInterface.objects.get_or_create(**interface)


class CoreConfig(AppConfig):
    name = "grandchallenge.components"

    def ready(self):
        post_migrate.connect(init_default_interfaces, sender=self)
