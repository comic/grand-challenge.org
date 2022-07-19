from django.urls import path

from grandchallenge.components.views import (
    ComponentInterfaceAutocomplete,
    ComponentInterfaceIOSwitch,
    ComponentInterfaceList,
    InterfaceListTypeOptions,
    InterfaceObjectTypeOptions,
)

app_name = "components"

urlpatterns = [
    path(
        "interfaces/algorithms/",
        ComponentInterfaceIOSwitch.as_view(),
        name="component-interface-list-algorithms",
    ),
    path(
        "interfaces/archives/",
        ComponentInterfaceList.as_view(
            list_type=InterfaceListTypeOptions.ITEM,
            object_type=InterfaceObjectTypeOptions.ARCHIVE,
        ),
        name="component-interface-list-archives",
    ),
    path(
        "interfaces/reader-studies/",
        ComponentInterfaceList.as_view(
            list_type=InterfaceListTypeOptions.CASE,
            object_type=InterfaceObjectTypeOptions.READER_STUDY,
        ),
        name="component-interface-list-reader-studies",
    ),
    path(
        "interfaces/inputs/",
        ComponentInterfaceList.as_view(
            list_type=InterfaceListTypeOptions.INPUT,
            object_type=InterfaceObjectTypeOptions.ALGORITHM,
        ),
        name="component-interface-list-input",
    ),
    path(
        "interfaces/outputs/",
        ComponentInterfaceList.as_view(
            list_type=InterfaceListTypeOptions.OUTPUT,
            object_type=InterfaceObjectTypeOptions.ALGORITHM,
        ),
        name="component-interface-list-output",
    ),
    path(
        "interfaces/autocomplete/",
        ComponentInterfaceAutocomplete.as_view(),
        name="component-interface-autocomplete",
    ),
]
