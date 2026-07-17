from datetime import timedelta
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, HttpUrl, RootModel
from pydantic_core import MISSING

from grandchallenge.components.models import ComponentJob


class ForgeArchive(BaseModel):
    slug: str
    url: HttpUrl


class ForgeSocket(BaseModel):
    slug: str
    relative_path: str
    example_value: Any = MISSING

    is_image_kind: bool = False
    is_panimg_kind: bool = False
    is_dicom_image_kind: bool = False
    is_json_kind: bool = False
    is_file_kind: bool = False
    is_json_file_kind: bool = False

    @property
    def has_example_value(self):
        return self.example_value is not MISSING


class ForgeInterface(BaseModel):
    inputs: list[ForgeSocket]
    outputs: list[ForgeSocket]


class ForgeAlgorithmContext:
    algorithm_interfaces: list[ForgeInterface]

    @property
    def algorithm_interface_names(self) -> list[str]:
        return [
            f"interf{idx}" for idx, _ in enumerate(self.algorithm_interfaces)
        ]

    @property
    def algorithm_interface_keys(self) -> list[tuple[str]]:
        algorithm_interface_keys = []
        for interface in self.algorithm_interfaces:
            algorithm_interface_keys.append(
                tuple(sorted([socket.slug for socket in interface.inputs]))
            )
        return algorithm_interface_keys

    @property
    def algorithm_input_sockets(self) -> list[ForgeSocket]:
        return [
            socket
            for interface in self.algorithm_interfaces
            for socket in interface.inputs
        ]

    @property
    def algorithm_output_sockets(self) -> list[ForgeSocket]:
        return [
            socket
            for interface in self.algorithm_interfaces
            for socket in interface.outputs
        ]


class ForgeChallenge(BaseModel):
    slug: str
    url: HttpUrl


class ForgePhase(ForgeAlgorithmContext, BaseModel):
    slug: str
    archive: ForgeArchive
    evaluation_additional_inputs: list[ForgeSocket]
    evaluation_additional_outputs: list[ForgeSocket]
    challenge: ForgeChallenge


class ForgeAlgorithm(ForgeAlgorithmContext, BaseModel):
    title: str
    slug: str
    url: HttpUrl


class ForgeSocketValue(BaseModel):
    socket: ForgeSocket
    file: str | None = None
    image: dict[str, str] | None = None
    value: Any = None


ForgeSocketValues = RootModel[list[ForgeSocketValue]]

ForgeStatusEnum = Enum(
    "ForgeStatusEnum",
    {str(value): str(label) for value, label in ComponentJob.STATUS_CHOICES},
)


class ForgePrediction(BaseModel):
    pk: UUID
    inputs: list[ForgeSocketValue]
    outputs: list[ForgeSocketValue]
    exec_duration: timedelta | None
    invoke_duration: timedelta | None
    status: ForgeStatusEnum


ForgePredictions = RootModel[list[ForgePrediction]]
