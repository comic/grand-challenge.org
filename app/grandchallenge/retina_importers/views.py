from django.core.exceptions import ObjectDoesNotExist
from rest_framework import permissions, generics, parsers, status, serializers
import datetime
from django.http.response import JsonResponse
from django.db import IntegrityError, transaction
from django.core.files import File
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from .utils import upperize, exclude_val_from_dict
from grandchallenge.annotations.models import (
    ETDRSGridAnnotation,
    BooleanClassificationAnnotation,
    MeasurementAnnotation,
    PolygonAnnotationSet,
    SinglePolygonAnnotation,
    LandmarkAnnotationSet,
    SingleLandmarkAnnotation,
)
from grandchallenge.annotations.serializers import (
    ETDRSGridAnnotationSerializer,
    BooleanClassificationAnnotationSerializer,
    MeasurementAnnotationSerializer,
    PolygonAnnotationSetSerializer,
    LandmarkAnnotationSetSerializer,
    SingleLandmarkAnnotationSerializer,
)
from grandchallenge.archives.models import Archive
from grandchallenge.archives.serializers import ArchiveSerializer
from grandchallenge.patients.models import Patient
from grandchallenge.patients.serializers import PatientSerializer
from grandchallenge.studies.models import Study
from grandchallenge.studies.serializers import StudySerializer
from grandchallenge.retina_images.models import RetinaImage
from grandchallenge.retina_images.serializers import RetinaImageSerializer

from .serializers import (
    UploadETDRSGridAnnotationSerializer,
    UploadBooleanClassificationAnnotationSerializer,
    UploadMeasurementAnnotationSerializer,
    UploadPolygonAnnotationSetSerializer,
    UploadLandmarkAnnotationSetSerializer,
)


class UploadImage(generics.CreateAPIView):
    queryset = RetinaImage.objects.all()
    serializer_class = RetinaImageSerializer
    permission_classes = (permissions.IsAdminUser,)
    parser_classes = (parsers.MultiPartParser,)

    def post(self, request, *args, **kwargs):
        # generate data dictionaries, excluding relations
        archive_dict = {"name": request.data.get("archive_identifier")}
        patient_dict = {"name": request.data.get("patient_identifier")}
        study_datetime = None
        if request.data.get("study_datetime") is not None:
            study_datetime = datetime.datetime.strptime(
                request.data.get("study_datetime"), "%Y-%m-%dT%H:%M:%S.%f%z"
            )

        study_dict = {
            "name": request.data.get("study_identifier"),
            "datetime": study_datetime,
        }

        image_dict = {
            "name": request.data.get("image_identifier"),
            "number": request.data.get("image_number"),
            "modality": upperize(request.data.get("image_modality")),
            "eye_choice": upperize(request.data.get("image_eye_choice")),
        }
        if (
            request.data.get("series_voxel_size_axial") is not None
            and request.data.get("series_voxel_size_lateral") is not None
            and request.data.get("series_voxel_size_transversal") is not None
        ):
            image_dict.update(
                {
                    "voxel_size": [
                        request.data.get("series_voxel_size_axial"),
                        request.data.get("series_voxel_size_lateral"),
                        request.data.get("series_voxel_size_transversal"),
                    ]
                }
            )

        # Perform validation with serializers
        archive_serializer = ArchiveSerializer(data=archive_dict)
        patient_serializer = PatientSerializer(data=patient_dict)
        study_serializer = StudySerializer(data=study_dict)
        image_serializer = RetinaImageSerializer(data=image_dict)
        archive_valid = archive_serializer.is_valid()
        patient_valid = patient_serializer.is_valid()
        study_valid = study_serializer.is_valid()
        image_valid = image_serializer.is_valid()

        if not archive_valid or not patient_valid or not study_valid or not image_valid:
            errors = {
                "archive_errors": archive_serializer.errors,
                "patient_errors": patient_serializer.errors,
                "study_errors": study_serializer.errors,
                "image_errors": image_serializer.errors,
            }
            return JsonResponse(errors, status=status.HTTP_400_BAD_REQUEST)

        # get existing or create new data structure models in database
        archive, archive_created = Archive.objects.get_or_create(**archive_dict)
        patient, patient_created = Patient.objects.update_or_create(
            name=patient_dict["name"],
            defaults=exclude_val_from_dict(patient_dict, "name"),
        )
        study, study_created = Study.objects.update_or_create(
            patient=patient,
            name=study_dict["name"],
            defaults=exclude_val_from_dict(study_dict, "name"),
        )

        image_created = False
        img = None
        # Check if image already exists in database
        try:
            img = RetinaImage.objects.get(study=study, **image_dict)
            # RetinaImage already exists. Do nothing and return response
        except RetinaImage.DoesNotExist:
            # RetinaImage does not exist yet.
            # Create image object without linking image file and without saving
            img = RetinaImage(study=study, **image_dict)

            # Save image fieldfile into RetinaImage, also triggers RetinaImage model save method
            image_file = File(request.data.get("image"))
            image_name = img.create_image_file_name(request.data.get("image"))
            img.image.save(image_name, image_file, save=True)
            archive.images.add(img)
            image_created = True
        except Exception:
            return JsonResponse(
                {"error": Exception}, status=status.HTTP_400_BAD_REQUEST
            )

        # Create response
        archive_response = ArchiveSerializer(archive).data
        archive_response.pop("images")
        response_obj = {
            "archive_created": archive_created,
            "archive": archive_response,
            "patient_created": patient_created,
            "patient": PatientSerializer(patient).data,
            "study_created": study_created,
            "study": StudySerializer(study).data,
            "image_created": image_created,
            "image": RetinaImageSerializer(img).data,
        }
        response_status = status.HTTP_201_CREATED
        if not image_created:
            response_status = status.HTTP_400_BAD_REQUEST

        return JsonResponse(response_obj, status=response_status)


class AbstractUploadView(generics.CreateAPIView):
    permission_classes = (permissions.IsAdminUser,)
    parser_classes = (parsers.JSONParser,)
    response = {}

    # keys that should be removed from request.data.get("data") when saving
    delete_keys = ("study_identifier", "series_identifier", "image_identifier")

    # define these variables in upload views that implement this abstract class
    queryset = None
    serializer_class = None  # Upload data serializer
    child_serializer_class = None  # Child model serializer
    parent_model_class = None  # parent model
    child_model_class = None  # child model (for models in request.data.get("data")

    def handle_validation(self, serializer, request):
        serializer = serializer(data=request.data)
        valid = serializer.is_valid()
        if not valid:
            self.response.update({"errors": serializer.errors})
            return None, None, None, None, None

        try:
            archive = Archive.objects.get(name=request.data.get("archive_identifier"))
        except Archive.DoesNotExist:
            r = "Archive does not exist: {}".format(
                request.data.get("archive_identifier")
            )
            self.response.update({"errors": [r]})
            return None, None, None, None, None

        patient = Patient.objects.get(name=request.data.get("patient_identifier"))

        grader_group, group_created = Group.objects.get_or_create(
            name=settings.RETINA_GRADERS_GROUP_NAME
        )

        grader, user_created = get_user_model().objects.get_or_create(
            username=request.data.get("user_identifier").lower()
        )

        if (
            user_created
            or grader.groups.filter(name=settings.RETINA_GRADERS_GROUP_NAME).count()
            == 0
        ):
            grader_group.user_set.add(grader)
            print(grader.username, "added to", grader_group.name)

        annotation_datetime = datetime.datetime.strptime(
            request.data.get("datetime"), "%Y-%m-%dT%H:%M:%S.%f%z"
        )

        return archive, patient, grader, user_created, annotation_datetime

    def trace_image_through_parents(self, data, patient):
        try:
            study = Study.objects.get(name=data["study_identifier"], patient=patient)
            image = RetinaImage.objects.get(name=data["image_identifier"], study=study)
        except ObjectDoesNotExist:
            error = "Non-existant object. Data: {}".format(data)
            self.response.update({"errors": error})
            return None

        return image

    def create_or_return_duplicate_error_message(self, model, unique_args):
        try:
            with transaction.atomic():
                model.save()
            return model
        except (IntegrityError, serializers.ValidationError):
            args_arr = []
            for key, item in unique_args.items():
                args_arr.append("{}: {}".format(key, item))

            class_name = model.__class__.__name__

            msg = "{} already exists for {}".format(class_name, ", ".join(args_arr))
            self.response.update({"errors": {"duplicate": msg}})

            return model

    def post(self, request, *args, **kwargs):
        self.response = {"success": False}

        archive, patient, grader, user_created, annotation_datetime = self.handle_validation(
            self.serializer_class, request
        )
        if "errors" in self.response:
            return JsonResponse(self.response, status=status.HTTP_400_BAD_REQUEST)

        if self.parent_model_class == LandmarkAnnotationSet:
            parent_model = self.parent_model_class(
                grader=grader, created=annotation_datetime
            )

            saved_model = self.create_or_return_duplicate_error_message(
                parent_model,
                {
                    "grader": grader.username,
                    "created": annotation_datetime.strftime("%Y-%m-%dT%H:%M:%S.%f%z"),
                },
            )
            if "errors" in self.response:
                return JsonResponse(self.response, status=status.HTTP_400_BAD_REQUEST)

        if self.child_model_class:
            child_bulk_save_models = []
            serialized_models = []
            for annotation in request.data.get("data"):
                image = self.trace_image_through_parents(annotation, patient)
                if "errors" in self.response:
                    return JsonResponse(
                        self.response, status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )

                for k in self.delete_keys:
                    annotation.pop(k)

                if self.parent_model_class == LandmarkAnnotationSet:
                    # ImageRegistration2D specific code
                    annotation["annotation_set"] = saved_model
                    single_child_model = self.child_model_class(
                        image=image, **annotation
                    )
                    child_bulk_save_models.append(single_child_model)
                    serialized_models.append(
                        self.child_serializer_class(single_child_model).data
                    )
                else:
                    polygon_value = None
                    if self.child_model_class == PolygonAnnotationSet:
                        # PolygonAnnotationSet specific code
                        polygon_value = annotation.pop("value")

                    child_model = self.child_model_class(
                        grader=grader,
                        created=annotation_datetime,
                        image=image,
                        **annotation
                    )

                    saved_model = self.create_or_return_duplicate_error_message(
                        child_model,
                        {
                            "grader": grader.username,
                            "image": image,
                            "created": annotation_datetime.strftime(
                                "%Y-%m-%dT%H:%M:%S.%f%z"
                            ),
                        },
                    )

                    if "errors" in self.response:
                        return JsonResponse(
                            self.response, status=status.HTTP_400_BAD_REQUEST
                        )
                    else:
                        serialized_models.append(
                            self.child_serializer_class(saved_model).data
                        )

                    if self.child_model_class == PolygonAnnotationSet:
                        # PolygonAnnotationSet specific code
                        # Create single polygon annotations and bind to set
                        for polygon in polygon_value:
                            if len(polygon) > 0:
                                child_bulk_save_models.append(
                                    SinglePolygonAnnotation(
                                        value=polygon, annotation_set=saved_model
                                    )
                                )
                        if len(child_bulk_save_models) > 0:
                            SinglePolygonAnnotation.objects.bulk_create(
                                child_bulk_save_models
                            )
                            child_bulk_save_models = []

            if len(child_bulk_save_models) > 0:
                self.child_model_class.objects.bulk_create(child_bulk_save_models)
            self.response.update(
                {
                    "success": True,
                    "user_created": user_created,
                    "grader": grader.username,
                    "model": serialized_models,
                }
            )

            return JsonResponse(self.response, status=status.HTTP_201_CREATED)


class UploadLandmarkAnnotationSet(AbstractUploadView):
    queryset = LandmarkAnnotationSet.objects.all()
    serializer_class = UploadLandmarkAnnotationSetSerializer  # Upload data serializer
    child_serializer_class = (
        SingleLandmarkAnnotationSerializer
    )  # Child model serializer
    parent_model_class = LandmarkAnnotationSet  # parent model
    child_model_class = (
        SingleLandmarkAnnotation
    )  # child model (for models in request.data.get("data")


class UploadETDRSGridAnnotation(AbstractUploadView):
    queryset = ETDRSGridAnnotation.objects.all()
    serializer_class = UploadETDRSGridAnnotationSerializer  # Upload data serializer
    child_serializer_class = ETDRSGridAnnotationSerializer  # Child model serializer
    parent_model_class = None  # parent model
    child_model_class = (
        ETDRSGridAnnotation
    )  # child model (for models in request.data.get("data")


class UploadMeasurementAnnotation(AbstractUploadView):
    queryset = MeasurementAnnotation.objects.all()
    serializer_class = UploadMeasurementAnnotationSerializer  # Upload data serializer
    child_serializer_class = MeasurementAnnotationSerializer  # Child model serializer
    parent_model_class = None  # parent model
    child_model_class = (
        MeasurementAnnotation
    )  # child model (for models in request.data.get("data")


class UploadBooleanClassificationAnnotation(AbstractUploadView):
    queryset = BooleanClassificationAnnotation.objects.all()
    serializer_class = (
        UploadBooleanClassificationAnnotationSerializer
    )  # Upload data serializer
    child_serializer_class = (
        BooleanClassificationAnnotationSerializer
    )  # Child model serializer
    parent_model_class = None  # parent model
    child_model_class = (
        BooleanClassificationAnnotation
    )  # child model (for models in request.data.get("data")


class UploadPolygonAnnotationSet(AbstractUploadView):
    queryset = PolygonAnnotationSet.objects.all()
    serializer_class = UploadPolygonAnnotationSetSerializer
    child_serializer_class = PolygonAnnotationSetSerializer
    parent_model_class = None
    child_model_class = PolygonAnnotationSet
