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
            "kind": ComponentInterface.Kind.ANY,
            "relative_path": "results.json",
        },
        {
            "title": "Predictions JSON File",
            "kind": ComponentInterface.Kind.ANY,
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
            "kind": ComponentInterface.Kind.ANY,
            "relative_path": "metrics.json",
        },
    ]

    for interface in default_interfaces:
        ComponentInterface.objects.get_or_create(**interface)


class CoreConfig(AppConfig):
    name = "grandchallenge.components"

    def ready(self):
        post_migrate.connect(init_default_interfaces, sender=self)
