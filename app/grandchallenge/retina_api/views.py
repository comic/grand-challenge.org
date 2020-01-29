import json
from enum import Enum

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import (
    MultipleObjectsReturned,
    ObjectDoesNotExist,
    ValidationError,
)
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import authentication, status, viewsets
from rest_framework.exceptions import NotFound
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_guardian import filters

from grandchallenge.annotations.models import (
    ETDRSGridAnnotation,
    ImagePathologyAnnotation,
    ImageQualityAnnotation,
    ImageTextAnnotation,
    LandmarkAnnotationSet,
    PolygonAnnotationSet,
    RetinaImagePathologyAnnotation,
    SinglePolygonAnnotation,
)
from grandchallenge.annotations.serializers import (
    ETDRSGridAnnotationSerializer,
    ImagePathologyAnnotationSerializer,
    ImageQualityAnnotationSerializer,
    ImageTextAnnotationSerializer,
    LandmarkAnnotationSetSerializer,
    PolygonAnnotationSetSerializer,
    RetinaImagePathologyAnnotationSerializer,
    SinglePolygonAnnotationSerializer,
)
from grandchallenge.archives.models import Archive
from grandchallenge.cases.models import Image
from grandchallenge.cases.permissions import ImagePermission
from grandchallenge.challenges.models import ImagingModality
from grandchallenge.core.serializers import UserSerializer
from grandchallenge.patients.models import Patient
from grandchallenge.registrations.serializers import (
    OctObsRegistrationSerializer,
)
from grandchallenge.retina_api.filters import RetinaAnnotationFilter
from grandchallenge.retina_api.mixins import (
    RetinaAPIPermission,
    RetinaAPIPermissionMixin,
    RetinaAdminAPIPermission,
    RetinaOwnerAPIPermission,
)
from grandchallenge.retina_api.renderers import Base64Renderer
from grandchallenge.retina_api.serializers import (
    BytesImageSerializer,
    TreeImageSerializer,
    TreeObjectSerializer,
)
from grandchallenge.serving.permissions import user_can_download_image
from grandchallenge.studies.models import Study


class ArchiveView(APIView):
    permission_classes = (RetinaAPIPermission,)
    authentication_classes = (authentication.SessionAuthentication,)
    pagination_class = None

    @staticmethod  # noqa: C901
    def create_response_object():  # noqa: C901
        # Exclude archives to reduce load time
        exclude = ["AREDS - GA selection", "RS1", "RS2", "RS3"]
        archives = Archive.objects.exclude(name__in=exclude)
        patients = Patient.objects.exclude(
            study__image__archive__name__in=exclude
        ).prefetch_related(
            "study_set",
            "study_set__image_set",
            "study_set__image_set__modality",
            "study_set__image_set__obs_image",
            "study_set__image_set__oct_image",
            "study_set__image_set__archive_set",
        )

        def generate_archives(archive_list, patients):
            for archive in archive_list:
                if archive.name == "kappadata":
                    subfolders = {}
                    images = dict(generate_images(archive.images))
                else:
                    subfolders = dict(generate_patients(archive, patients))
                    images = {}

                yield archive.name, {
                    "subfolders": subfolders,
                    "info": "level 3",
                    "name": archive.name,
                    "id": archive.id,
                    "images": images,
                }

        def generate_patients(archive, patients):
            patient_list = patients.filter(
                study__image__archive=archive
            ).distinct()
            for patient in patient_list:
                if archive.name == settings.RETINA_EXCEPTION_ARCHIVE:
                    image_set = {}
                    for study in patient.study_set.all():
                        image_set.update(
                            dict(generate_images(study.image_set))
                        )
                    yield patient.name, {
                        "subfolders": {},
                        "info": "level 4",
                        "name": patient.name,
                        "id": patient.id,
                        "images": image_set,
                    }
                else:
                    yield patient.name, {
                        "subfolders": dict(
                            generate_studies(patient.study_set)
                        ),
                        "info": "level 4",
                        "name": patient.name,
                        "id": patient.id,
                        "images": {},
                    }

        def generate_studies(study_list):
            for study in study_list.all():
                yield study.name, {
                    "info": "level 5",
                    "images": dict(generate_images(study.image_set)),
                    "name": study.name,
                    "id": study.id,
                    "subfolders": {},
                }

        def generate_images(image_list):
            for image in image_list.all():
                if image.modality.modality == settings.MODALITY_OCT:
                    # oct image add info
                    obs_image_id = "no info"
                    try:
                        oct_obs_registration = image.oct_image.get()
                        obs_image_id = oct_obs_registration.obs_image.id
                        obs_list = oct_obs_registration.registration_values
                        obs_registration_flat = [
                            val for sublist in obs_list for val in sublist
                        ]
                    except ObjectDoesNotExist:
                        obs_registration_flat = []

                    # leave voxel_size always empty because this info is in mhd file
                    voxel_size = [0, 0, 0]
                    study_datetime = "Unknown"
                    if image.study.datetime:
                        study_datetime = image.study.datetime.strftime(
                            "%Y/%m/%d %H:%M:%S"
                        )

                    yield image.name, {
                        "images": {
                            "trc_000": "no info",
                            "obs_000": obs_image_id,
                            "mot_comp": "no info",
                            "trc_001": "no info",
                            "oct": image.id,
                        },
                        "info": {
                            "voxel_size": {
                                "axial": voxel_size[0],
                                "lateral": voxel_size[1],
                                "transversal": voxel_size[2],
                            },
                            "date": study_datetime,
                            "registration": {
                                "obs": obs_registration_flat,
                                "trc": [0, 0, 0, 0],
                            },
                        },
                    }
                elif (
                    image.modality.modality == settings.MODALITY_CF
                    and image.name.endswith(".fds")
                ):
                    # OBS image, skip because this is already in fds
                    pass
                else:
                    yield image.name, image.id

        response = {
            "subfolders": dict(generate_archives(archives, patients)),
            "info": "level 2",
            "name": "Archives",
            "id": "none",
            "images": {},
        }
        return response

    def get(self, request):
        return Response(self.create_response_object())


class ImageView(RetinaAPIPermissionMixin, View):
    authentication_classes = (authentication.SessionAuthentication,)

    def get(
        self,
        request,
        image_type,
        patient_identifier,
        study_identifier,
        image_identifier,
        image_modality,
    ):
        if patient_identifier == settings.RETINA_EXCEPTION_ARCHIVE:
            # BMES data contains no study name, switched up parameters
            image = Image.objects.filter(
                study__patient__name=study_identifier,  # this argument contains patient identifier
                name=image_identifier,
            )
        elif (
            patient_identifier == "Archives"
            and study_identifier == "kappadata"
        ):
            # Exception for finding image in kappadata
            image = Image.objects.filter(name=image_identifier)
        else:
            image = Image.objects.filter(
                name=image_identifier,
                study__name=study_identifier,
                study__patient__name=patient_identifier,
            )

        try:
            if image_modality == "obs_000":
                image = image.get(modality__modality=settings.MODALITY_CF)
            elif image_modality == "oct":
                image = image.get(modality__modality=settings.MODALITY_OCT)
            else:
                image = image.get()
        except MultipleObjectsReturned:
            print("failed unique image search")
            return Response(status=status.HTTP_404_NOT_FOUND)

        if image_type == "thumb":
            response = redirect("retina:image-thumbnail", image_id=image.id)
        else:
            response = redirect("retina:image-numpy", image_id=image.id)

        return response


class DataView(APIView):
    permission_classes = (RetinaOwnerAPIPermission,)
    authentication_classes = (authentication.SessionAuthentication,)
    pagination_class = None

    class DataType(Enum):
        REGISTRATION = "Registration"
        ETDRS = "ETDRS"
        FOVEA = "Fovea"
        MEASURE = "Measure"
        GA = "GA"
        KAPPA = "kappa"

    @staticmethod
    def coordinate_to_dict(coordinate):
        return {"x": coordinate[0], "y": coordinate[1]}

    def coordinates_list_to_dict(self, coordinate_list):
        result = []
        for coordinate in coordinate_list:
            result.append(self.coordinate_to_dict(coordinate))
        return result

    @staticmethod
    def dict_to_coordinate(dictionary):
        return [dictionary["x"], dictionary["y"]]

    def dict_list_to_coordinates(self, dict_list):
        result = []
        for coordinate in dict_list:
            result.append(self.dict_to_coordinate(coordinate))
        return result

    def get_models_related_to_image_and_user(
        self, images, user, model_set, extra_conditions=None
    ):
        if extra_conditions is None:
            extra_conditions = {}

        annotation_models = []

        for image in images:
            user_annotation_models = getattr(image, model_set).filter(
                grader=user, **extra_conditions
            )
            for annotation_model in user_annotation_models:
                annotation_models.append(annotation_model)

        return annotation_models

    def create_annotation_data_australia(self, data_type, annotation_models):
        data = {}
        for annotation_model in annotation_models:
            date_key = annotation_model.created.strftime(
                "%Y-%m-%d--%H-%M-%S--%f"
            )
            image_name = annotation_model.image.name
            if data_type == self.DataType.ETDRS.value:
                result_data = {
                    "fovea": self.coordinate_to_dict(annotation_model.fovea),
                    "optic_disk": self.coordinate_to_dict(
                        annotation_model.optic_disk
                    ),
                }
            elif data_type == self.DataType.FOVEA.value:
                result_data = {"fovea_affected": annotation_model.value}
                pass
            result_dict = {image_name: result_data}
            if data.get(date_key):
                data[date_key].update(result_dict)
            else:
                data.update({date_key: result_dict})
        return data

    @staticmethod
    def get_image_from_rotterdam_data(patient, request_data):
        image_identifier = request_data.get("sub_img_name")
        conditions = {}
        if image_identifier == "oct":
            conditions.update(
                {"modality__modality": settings.MODALITY_OCT}
            )  # set number for oct images
        elif image_identifier == "obs_000":
            conditions.update({"modality__modality": settings.MODALITY_CF})
        return Image.objects.get(
            study__patient=patient,
            study__name=request_data.get("visit_nr"),
            name=request_data.get("img_name"),
            **conditions,
        )

    @staticmethod
    def get_image_from_kappadata(request_data):
        image_name = request_data.items()[0]
        image = Image.objects.get(name=image_name)
        return image

    def get(  # noqa: C901
        self,
        request,
        data_type,
        user_id,
        archive_identifier,
        patient_identifier,
    ):
        data = {}
        images = Image.objects.filter(
            study__patient__name=patient_identifier,
            archive__name=archive_identifier,
        )
        if archive_identifier == "kappadata":
            images = Image.objects.filter(
                archive=Archive.objects.get(name="kappadata")
            )

        user = get_user_model().objects.get(id=user_id)

        if data_type == self.DataType.REGISTRATION.value:
            landmark_annotations = []
            for image in images:
                user_landmark_annotations = image.singlelandmarkannotation_set.filter(
                    annotation_set__grader_id=user.id
                )
                for user_landmark_annotation in user_landmark_annotations:
                    landmark_annotations.append(user_landmark_annotation)

            for annotation in landmark_annotations:
                date_key = annotation.annotation_set.created.strftime(
                    "%Y-%m-%d--%H-%M-%S--%f"
                )
                if archive_identifier == settings.RETINA_EXCEPTION_ARCHIVE:
                    image_name = annotation.image.name

                    result_dict = {
                        image_name: self.coordinates_list_to_dict(
                            annotation.landmarks
                        )
                    }

                    if data.get(date_key):
                        data[date_key].update(result_dict)
                    else:
                        data.update({date_key: result_dict})
                else:
                    result_dict = {
                        "points": self.coordinates_list_to_dict(
                            annotation.landmarks
                        ),
                        "visit_nr": annotation.image.study.name,
                        "img_name": annotation.image.name,
                    }
                    if (
                        annotation.image.modality.modality
                        == settings.MODALITY_CF
                        and annotation.image.name.endswith("OCT.fds")
                    ):
                        result_dict.update({"sub_img_name": "obs_000"})
                    if (
                        annotation.image.modality.modality
                        == settings.MODALITY_OCT
                    ):
                        result_dict.update({"sub_img_name": "oct"})
                    if data.get(date_key):
                        data[date_key].append(result_dict)
                    else:
                        data.update({date_key: [result_dict]})

        elif data_type == self.DataType.ETDRS.value:
            annotation_models = self.get_models_related_to_image_and_user(
                images, user, "etdrsgridannotation_set"
            )

            for annotation_model in annotation_models:
                date_key = annotation_model.created.strftime(
                    "%Y-%m-%d--%H-%M-%S--%f"
                )
                image_name = annotation_model.image.name
                result_data = {
                    "fovea": self.coordinate_to_dict(annotation_model.fovea),
                    "optic_disk": self.coordinate_to_dict(
                        annotation_model.optic_disk
                    ),
                }
                if archive_identifier == settings.RETINA_EXCEPTION_ARCHIVE:
                    result_dict = {image_name: result_data}
                    data.update(result_dict)
                else:
                    result_data.update({"img_name": image_name})
                    if annotation_model.image.study is not None:
                        result_data.update(
                            {"visit_nr": annotation_model.image.study.name}
                        )

                    if (
                        annotation_model.image.modality.modality
                        == settings.MODALITY_CF
                        and annotation_model.image.name.endswith("OCT.fds")
                    ):
                        result_dict.update({"sub_img_name": "obs_000"})
                    if (
                        annotation_model.image.modality.modality
                        == settings.MODALITY_OCT
                    ):
                        result_dict.update({"sub_img_name": "oct"})
                    if data.get(date_key):
                        data[date_key].update(result_data)
                    else:
                        data.update({date_key: result_data})

        elif data_type == self.DataType.MEASURE.value:
            annotation_models = self.get_models_related_to_image_and_user(
                images, user, "measurementannotation_set"
            )

            for annotation_model in annotation_models:
                date_key = annotation_model.created.strftime(
                    "%Y-%m-%d--%H-%M-%S--%f"
                )
                image_name = annotation_model.image.name
                result_data = {
                    "from": self.coordinate_to_dict(
                        annotation_model.start_voxel
                    ),
                    "to": self.coordinate_to_dict(annotation_model.end_voxel),
                }
                result_dict = {image_name: [result_data]}
                if data.get(date_key):
                    if data[date_key].get(image_name):
                        data[date_key][image_name].append(result_data)
                    else:
                        data[date_key].update(result_dict)
                else:
                    data.update({date_key: result_dict})
        elif data_type == self.DataType.FOVEA.value:
            annotation_models = self.get_models_related_to_image_and_user(
                images,
                user,
                "booleanclassificationannotation_set",
                {"name": "fovea_affected"},
            )
            data = self.create_annotation_data_australia(
                data_type, annotation_models
            )
        elif (
            data_type == self.DataType.GA.value
            or data_type == self.DataType.KAPPA.value
        ):
            annotation_models = self.get_models_related_to_image_and_user(
                images, user, "polygonannotationset_set"
            )

            for annotation_model in annotation_models:
                ga_type = annotation_model.name
                if data_type == self.DataType.GA.value:
                    ga_type = ga_type.capitalize()
                for spa in annotation_model.singlepolygonannotation_set.all():
                    date_key = annotation_model.created.strftime(
                        "%Y-%m-%d--%H-%M-%S--%f"
                    )
                    result_data_points = self.coordinates_list_to_dict(
                        spa.value
                    )

                    image_name = annotation_model.image.name
                    result_data = {ga_type: [result_data_points]}
                    if data_type == self.DataType.GA.value:
                        opposing_type = (
                            "Peripapillary"
                            if ga_type == "Macular"
                            else "Macular"
                        )
                        result_data.update(
                            {
                                opposing_type: []  # Add opposing GA type to object to prevent front-end error
                            }
                        )
                    series_name = image_name

                    if (
                        archive_identifier != settings.RETINA_EXCEPTION_ARCHIVE
                        and archive_identifier != "kappadata"
                    ):
                        visit_id = annotation_model.image.study.name
                        sub_img_name = None
                        if (
                            annotation_model.image.modality.modality
                            == settings.MODALITY_CF
                            and annotation_model.image.name.endswith("OCT.fds")
                        ):
                            sub_img_name = "obs_000"
                        if (
                            annotation_model.image.modality.modality
                            == settings.MODALITY_OCT
                        ):
                            sub_img_name = "oct"

                        img_name = [image_name, sub_img_name]
                        sub_img_name = (
                            "" if sub_img_name is None else sub_img_name
                        )
                        series_name = visit_id + image_name + sub_img_name

                        result_data.update(
                            {"visit_nr": visit_id, "img_name": img_name}
                        )

                    result_dict = {series_name: result_data}
                    if data.get(date_key):
                        if data[date_key].get(series_name):
                            if (
                                data[date_key][series_name].get(ga_type)
                                is None
                            ):
                                data[date_key][series_name].update(result_data)
                            else:
                                data[date_key][series_name][ga_type].append(
                                    result_data_points
                                )
                        else:
                            data[date_key].update(result_dict)
                    else:
                        data.update({date_key: result_dict})

        if data == {}:
            response_data = {"status": "no data", "data": {}}
        else:
            response_data = {"status": "data", "data": data}

        return Response(response_data)

    @method_decorator(ensure_csrf_cookie)  # noqa: C901
    def put(  # noqa: C901
        self,
        request,
        data_type,
        user_id,
        archive_identifier,
        patient_identifier,
    ):
        request_data = json.loads(request.body)
        if archive_identifier != "kappadata":
            patient = (
                Patient.objects.filter(
                    name=patient_identifier,
                    study__image__archive__name=archive_identifier,
                )
                .distinct()
                .get()
            )

        user = get_user_model().objects.get(id=user_id)

        save_data = {"grader": user, "created": timezone.now()}
        if data_type == self.DataType.REGISTRATION.value:
            # Create parent LandmarkAnnotationSet model to link landmarks to
            landmark_annotation_set_model = LandmarkAnnotationSet.objects.create(
                **save_data
            )

        if archive_identifier == settings.RETINA_EXCEPTION_ARCHIVE:
            # Australia
            for image_name, data in request_data.items():
                image = Image.objects.get(
                    name=image_name, study__patient=patient
                )
                if data_type == self.DataType.ETDRS.value:
                    image.etdrsgridannotation_set.create(
                        fovea=self.dict_to_coordinate(data["fovea"]),
                        optic_disk=self.dict_to_coordinate(data["optic_disk"]),
                        **save_data,
                    )
                elif (
                    data_type == self.DataType.GA.value
                    or data_type == self.DataType.KAPPA.value
                ):
                    for ga_type, ga_data_list in data.items():
                        if not ga_data_list:
                            continue  # skip empty arrays
                        ga_points_model = image.polygonannotationset_set.create(
                            name=ga_type.lower(), **save_data
                        )
                        for ga_data in ga_data_list:
                            ga_points_model.singlepolygonannotation_set.create(
                                value=self.dict_list_to_coordinates(ga_data)
                            )
                elif data_type == self.DataType.FOVEA.value:
                    image.booleanclassificationannotation_set.create(
                        name="fovea_affected",
                        value=data["fovea_affected"],
                        **save_data,
                    )
                elif data_type == self.DataType.MEASURE.value:
                    for measurement in data:
                        image.measurementannotation_set.create(
                            start_voxel=self.dict_to_coordinate(
                                measurement["from"]
                            ),
                            end_voxel=self.dict_to_coordinate(
                                measurement["to"]
                            ),
                            **save_data,
                        )
                elif data_type == self.DataType.REGISTRATION.value:
                    landmark_annotation_set_model.singlelandmarkannotation_set.create(
                        image=image,
                        landmarks=self.dict_list_to_coordinates(data),
                    )
        elif archive_identifier == "kappadata":
            # kappadata
            data = request_data
            if data_type == self.DataType.ETDRS.value:
                image = Image.objects.get(name=data["img_name"])
                image.etdrsgridannotation_set.create(
                    fovea=self.dict_to_coordinate(data["fovea"]),
                    optic_disk=self.dict_to_coordinate(data["optic_disk"]),
                    **save_data,
                )
            elif data_type == self.DataType.KAPPA.value:
                for image_name, ga_data in data.items():
                    image = Image.objects.get(name=image_name)
                    for ga_type, ga_data_list in ga_data.items():
                        if not ga_data_list:
                            continue  # skip empty elements in dict
                        ga_points_model = image.polygonannotationset_set.create(
                            name=ga_type.lower(), **save_data
                        )
                        for single_ga_data in ga_data_list:
                            ga_points_model.singlepolygonannotation_set.create(
                                value=self.dict_list_to_coordinates(
                                    single_ga_data
                                )
                            )
        else:
            # Rotterdam study data
            data = request_data
            if data_type == self.DataType.ETDRS.value:
                image = self.get_image_from_rotterdam_data(patient, data)
                image.etdrsgridannotation_set.create(
                    fovea=self.dict_to_coordinate(data["fovea"]),
                    optic_disk=self.dict_to_coordinate(data["optic_disk"]),
                    **save_data,
                )
            elif data_type == self.DataType.REGISTRATION.value:
                for registration in data:
                    image = self.get_image_from_rotterdam_data(
                        patient, registration
                    )
                    landmark_annotation_set_model.singlelandmarkannotation_set.create(
                        image=image,
                        landmarks=self.dict_list_to_coordinates(
                            registration["points"]
                        ),
                    )
            elif (
                data_type == self.DataType.GA.value
                or data_type == self.DataType.KAPPA.value
            ):
                for _visit_image_name, ga_data in data.items():
                    conditions = {}
                    if ga_data["img_name"][1] == "obs_000":
                        conditions.update(
                            {
                                "modality": ImagingModality.objects.get(
                                    modality=settings.MODALITY_CF
                                )
                            }
                        )
                    elif ga_data["img_name"][1] == "oct":
                        conditions.update(
                            {
                                "modality": ImagingModality.objects.get(
                                    modality=settings.MODALITY_OCT
                                )
                            }
                        )

                    image = Image.objects.get(
                        study__name=ga_data["visit_nr"],
                        study__patient=patient,
                        name=ga_data["img_name"][0],
                        **conditions,
                    )
                    for ga_type, ga_data_list in ga_data.items():
                        if (
                            ga_type in ("img_name", "visit_nr")
                            or not ga_data_list
                        ):
                            continue  # skip non ga elements in dict
                        ga_points_model = image.polygonannotationset_set.create(
                            name=ga_type.lower(), **save_data
                        )
                        for single_ga_data in ga_data_list:
                            ga_points_model.singlepolygonannotation_set.create(
                                value=self.dict_list_to_coordinates(
                                    single_ga_data
                                )
                            )

        return Response({"success": True}, status=status.HTTP_201_CREATED)


class PolygonListView(ListAPIView):
    """
    Get a serialized list of all PolygonAnnotationSets with all related SinglePolygonAnnotations
    belonging to a single user and image.
    """

    permission_classes = (RetinaOwnerAPIPermission,)
    authentication_classes = (authentication.SessionAuthentication,)
    serializer_class = PolygonAnnotationSetSerializer
    pagination_class = None

    def get_queryset(self):
        user_id = self.kwargs["user_id"]
        image_id = self.kwargs["image_id"]
        image = get_object_or_404(Image, id=image_id)
        return image.polygonannotationset_set.prefetch_related(
            "singlepolygonannotation_set"
        ).filter(grader__id=user_id)


class PolygonAnnotationSetViewSet(viewsets.ModelViewSet):
    permission_classes = (RetinaOwnerAPIPermission,)
    authentication_classes = (authentication.SessionAuthentication,)
    serializer_class = PolygonAnnotationSetSerializer
    filter_backends = (filters.ObjectPermissionsFilter,)
    pagination_class = None
    queryset = PolygonAnnotationSet.objects.all()


class SinglePolygonViewSet(viewsets.ModelViewSet):
    permission_classes = (RetinaOwnerAPIPermission,)
    authentication_classes = (authentication.SessionAuthentication,)
    serializer_class = SinglePolygonAnnotationSerializer
    filter_backends = (filters.ObjectPermissionsFilter,)
    pagination_class = None
    queryset = SinglePolygonAnnotation.objects.all()


class GradersWithPolygonAnnotationsListView(ListAPIView):
    permission_classes = (RetinaAdminAPIPermission,)
    authentication_classes = (authentication.SessionAuthentication,)
    pagination_class = None
    serializer_class = UserSerializer

    def get_queryset(self):
        image_id = self.kwargs["image_id"]
        image = get_object_or_404(Image, id=image_id)
        polygon_annotation_sets = PolygonAnnotationSet.objects.filter(
            image=image
        )
        graders = (
            get_user_model()
            .objects.filter(
                polygonannotationset__in=polygon_annotation_sets,
                groups__name=settings.RETINA_GRADERS_GROUP_NAME,
            )
            .distinct()
        )
        return graders


class ETDRSGridAnnotationViewSet(viewsets.ModelViewSet):
    permission_classes = (RetinaOwnerAPIPermission,)
    authentication_classes = (authentication.SessionAuthentication,)
    serializer_class = ETDRSGridAnnotationSerializer
    filter_backends = (filters.ObjectPermissionsFilter,)
    pagination_class = None
    queryset = ETDRSGridAnnotation.objects.all()


class LandmarkAnnotationSetForImageList(ListAPIView):
    permission_classes = (RetinaOwnerAPIPermission,)
    authentication_classes = (authentication.SessionAuthentication,)
    serializer_class = LandmarkAnnotationSetSerializer
    filter_backends = (filters.ObjectPermissionsFilter,)
    pagination_class = None

    def get_queryset(self):
        user_id = self.kwargs["user_id"]
        image_ids = self.request.query_params.get("image_ids")
        if image_ids is None:
            raise NotFound()
        image_ids = image_ids.split(",")
        user = get_object_or_404(get_user_model(), id=user_id)
        queryset = user.landmarkannotationset_set.filter(
            singlelandmarkannotation__image__id__in=image_ids
        ).distinct()
        return queryset


class OctObsRegistrationRetrieve(RetrieveAPIView):
    permission_classes = (RetinaAPIPermission,)
    authentication_classes = (authentication.SessionAuthentication,)
    serializer_class = OctObsRegistrationSerializer
    filter_backends = (filters.ObjectPermissionsFilter,)
    lookup_url_kwarg = "image_id"

    def get_object(self):
        image_id = self.kwargs.get("image_id")
        if image_id is None:
            raise NotFound()
        image = get_object_or_404(
            Image.objects.prefetch_related("oct_image", "obs_image"),
            id=image_id,
        )
        if image.oct_image.exists():
            return image.oct_image.get()
        elif image.obs_image.exists():
            return image.obs_image.get()
        else:
            raise NotFound()


class ImageElementSpacingView(RetinaAPIPermissionMixin, View):
    raise_exception = True  # Raise 403 on unauthenticated request

    def get(self, request, image_id):
        image_object = get_object_or_404(Image, pk=image_id)

        if not user_can_download_image(user=request.user, image=image_object):
            return HttpResponse(status=status.HTTP_403_FORBIDDEN)

        image_itk = image_object.get_sitk_image()
        if image_itk is None:
            return HttpResponse(status=status.HTTP_404_NOT_FOUND)

        spacing = image_itk.GetSpacing()

        return HttpResponse(
            json.dumps(spacing), content_type="application/json"
        )


class ImageQualityAnnotationViewSet(viewsets.ModelViewSet):
    permission_classes = (RetinaOwnerAPIPermission,)
    authentication_classes = (authentication.SessionAuthentication,)
    serializer_class = ImageQualityAnnotationSerializer
    filter_backends = (filters.ObjectPermissionsFilter,)
    pagination_class = None
    queryset = ImageQualityAnnotation.objects.all()


class ImagePathologyAnnotationViewSet(viewsets.ModelViewSet):
    permission_classes = (RetinaOwnerAPIPermission,)
    authentication_classes = (authentication.SessionAuthentication,)
    serializer_class = ImagePathologyAnnotationSerializer
    filter_backends = (filters.ObjectPermissionsFilter,)
    pagination_class = None
    queryset = ImagePathologyAnnotation.objects.all()


class RetinaImagePathologyAnnotationViewSet(viewsets.ModelViewSet):
    permission_classes = (RetinaOwnerAPIPermission,)
    authentication_classes = (authentication.SessionAuthentication,)
    serializer_class = RetinaImagePathologyAnnotationSerializer
    filter_backends = (filters.ObjectPermissionsFilter,)
    pagination_class = None
    queryset = RetinaImagePathologyAnnotation.objects.all()


class ArchiveAPIView(APIView):
    permission_classes = (RetinaAPIPermission,)
    authentication_classes = (authentication.TokenAuthentication,)
    pagination_class = None

    def get(self, request, pk=None):
        image_prefetch_related = ("modality", "study__patient", "archive_set")
        objects = []
        images = []
        if pk is None:
            objects = Archive.objects.all()
        else:
            if Archive.objects.filter(pk=pk).exists():
                objects = Patient.objects.filter(
                    study__image__archive__pk=pk
                ).distinct()
                images = Image.objects.filter(
                    archive__pk=pk, study=None
                ).prefetch_related(*image_prefetch_related)
            elif Patient.objects.filter(pk=pk).exists():
                objects = Study.objects.filter(patient__pk=pk)
            elif Study.objects.filter(pk=pk).exists():
                images = Image.objects.filter(study__pk=pk).prefetch_related(
                    *image_prefetch_related
                )
            else:
                return HttpResponse(status=status.HTTP_404_NOT_FOUND)

        objects_serialized = TreeObjectSerializer(objects, many=True).data
        images_serialized = TreeImageSerializer(images, many=True).data

        response = {
            "directories": sorted(objects_serialized, key=lambda x: x["name"]),
            "images": sorted(images_serialized, key=lambda x: x["name"]),
        }
        return Response(response)


class B64ThumbnailAPIView(RetrieveAPIView):
    permission_classes = (ImagePermission, RetinaAPIPermission)
    authentication_classes = (authentication.TokenAuthentication,)
    renderer_classes = (Base64Renderer,)
    queryset = Image.objects.all()
    serializer_class = BytesImageSerializer

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        width = kwargs.get("width", settings.RETINA_DEFAULT_THUMBNAIL_SIZE)
        height = kwargs.get("height", settings.RETINA_DEFAULT_THUMBNAIL_SIZE)
        serializer_context = {"width": width, "height": height}
        serializer = BytesImageSerializer(instance, context=serializer_context)
        return Response(serializer.data)


class ImageTextAnnotationViewSet(viewsets.ModelViewSet):
    permission_classes = (RetinaOwnerAPIPermission,)
    authentication_classes = (authentication.SessionAuthentication,)
    serializer_class = ImageTextAnnotationSerializer
    filter_backends = (filters.ObjectPermissionsFilter,)
    pagination_class = None
    queryset = ImageTextAnnotation.objects.all()


class LandmarkAnnotationSetViewSet(viewsets.ModelViewSet):
    permission_classes = (RetinaAPIPermission,)
    authentication_classes = (authentication.TokenAuthentication,)
    serializer_class = LandmarkAnnotationSetSerializer
    filter_backends = (filters.ObjectPermissionsFilter, RetinaAnnotationFilter)
    pagination_class = None

    def get_queryset(self):
        """
        If the query parameter `image_id` is defined, the queryset will be a list of
        `LandmarkAnnotationSet`s that contain a `SingleLandmarkAnnotation` related to
        the given image id. If the image does not exist, this will raise a Http404
        Exception. Otherwise, it will return the full `LandmarkAnnotationSet` queryset

        Returns
        -------
        QuerySet
        """
        queryset = LandmarkAnnotationSet.objects.prefetch_related(
            "singlelandmarkannotation_set"
        ).all()
        image_id = self.request.query_params.get("image_id")
        if image_id is not None:
            try:
                image = get_object_or_404(Image.objects.all(), pk=image_id)
            except ValidationError:
                # Invalid uuid passed, return 404
                raise NotFound()
            queryset = LandmarkAnnotationSet.objects.filter(
                singlelandmarkannotation__image=image
            )

        return queryset
