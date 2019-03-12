from django.core.exceptions import (
    ObjectDoesNotExist,
    ValidationError,
    MultipleObjectsReturned,
)
from rest_framework import generics, parsers, status, serializers
import datetime
import sys
from io import BytesIO
from django.http.response import JsonResponse
from django.core.files.uploadedfile import InMemoryUploadedFile
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
    SingleLandmarkAnnotationSerializer,
)
from grandchallenge.archives.models import Archive
from grandchallenge.archives.serializers import ArchiveSerializer
from grandchallenge.patients.models import Patient
from grandchallenge.patients.serializers import PatientSerializer
from grandchallenge.studies.models import Study
from grandchallenge.studies.serializers import StudySerializer

from grandchallenge.cases.models import Image, ImageFile
from grandchallenge.cases.serializers import ImageSerializer
from grandchallenge.challenges.models import ImagingModality
from .serializers import (
    UploadETDRSGridAnnotationSerializer,
    UploadBooleanClassificationAnnotationSerializer,
    UploadMeasurementAnnotationSerializer,
    UploadPolygonAnnotationSetSerializer,
    UploadLandmarkAnnotationSetSerializer,
)
from .mixins import RetinaImportPermission


class CheckImage(generics.GenericAPIView):
    queryset = Image.objects.all()
    permission_classes = (RetinaImportPermission,)
    parser_classes = (parsers.JSONParser,)

    def post(self, request, *args, **kwargs):
        return JsonResponse({"exists": self.check_if_already_exists(request)})

    @staticmethod
    def check_if_already_exists(request):
        """
        Method that checks if a image already exists before uploading.
        """
        try:
            archive_name = request.data.get("archive_identifier")
            if archive_name is not None:
                Archive.objects.get(name=archive_name)

            patient_name = request.data.get("patient_identifier")
            patient = None
            if patient_name is not None:
                patient = Patient.objects.get(name=patient_name)

            study_name = request.data.get("study_identifier")
            study = None
            if study_name is not None and patient is not None:
                study = Study.objects.get(patient=patient, name=study_name)
        except ObjectDoesNotExist:
            return False

        image_dict = UploadImage.create_image_dict(request)
        try:
            Image.objects.get(study=study, **image_dict)
            return True
        except ObjectDoesNotExist:
            return False


class UploadImage(generics.CreateAPIView):
    queryset = Image.objects.all()
    permission_classes = (RetinaImportPermission,)
    parser_classes = (parsers.MultiPartParser, parsers.JSONParser)

    def post(self, request, *args, **kwargs):
        response_obj = {}
        try:
            # Process archive
            archive_name = request.data.get("archive_identifier")
            archive = None
            if archive_name is not None:
                archive_dict = {"name": archive_name}
                self.validate_model(archive_dict, ArchiveSerializer)
                archive, archive_created = Archive.objects.get_or_create(
                    **archive_dict
                )
                response_obj.update(
                    {
                        "archive_created": archive_created,
                        "archive": ArchiveSerializer(archive).data,
                    }
                )

            # Process patient
            patient_name = request.data.get("patient_identifier")
            patient = None
            if patient_name is not None:
                patient_dict = {"name": patient_name}
                self.validate_model(patient_dict, PatientSerializer)
                patient, patient_created = Patient.objects.update_or_create(
                    name=patient_dict["name"],
                    defaults=exclude_val_from_dict(patient_dict, "name"),
                )
                response_obj.update(
                    {
                        "patient_created": patient_created,
                        "patient": PatientSerializer(patient).data,
                    }
                )

            # Process study (only possible if patient exists)
            study_name = request.data.get("study_identifier")
            study = None
            if study_name is not None and patient is not None:
                study_datetime = None
                if request.data.get("study_datetime") is not None:
                    study_datetime = datetime.datetime.strptime(
                        request.data.get("study_datetime"),
                        "%Y-%m-%dT%H:%M:%S.%f%z",
                    )
                study_dict = {"name": study_name, "datetime": study_datetime}
                self.validate_model(study_dict, StudySerializer)
                study, study_created = Study.objects.update_or_create(
                    patient=patient,
                    name=study_dict["name"],
                    defaults=exclude_val_from_dict(study_dict, "name"),
                )
                response_obj.update(
                    {
                        "study_created": study_created,
                        "study": StudySerializer(study).data,
                    }
                )

            # Process image
            image_created = False
            image_dict = self.create_image_dict(request)
            # Check if image already exists in database
            try:
                img = Image.objects.get(study=study, **image_dict)
                # Image already exists. Do nothing and return response
            except Image.DoesNotExist:
                # Image does not exist yet, create it.
                img = Image.objects.create(study=study, **image_dict)

                # Save mhd and raw files
                self.save_mhd_and_raw_files(request, img)

                # Link images to archive
                if archive is not None:
                    archive.images.add(img)
                image_created = True

                # Set correct permissions for retina image
                img.permit_viewing_by_retina_users()
            except Exception as e:
                return JsonResponse(
                    {"error": e}, status=status.HTTP_400_BAD_REQUEST
                )
            response_obj.update(
                {
                    "image_created": image_created,
                    "image": ImageSerializer(img).data,
                }
            )
        except ValidationError as e:
            return JsonResponse(
                e.message_dict, status=status.HTTP_400_BAD_REQUEST
            )

        # Create response
        response_status = status.HTTP_201_CREATED
        if not image_created:
            response_status = status.HTTP_400_BAD_REQUEST

        return JsonResponse(response_obj, status=response_status)

    @staticmethod
    def create_image_dict(request):
        modality = upperize(request.data.get("image_modality"))
        # Set color space
        if modality == "OCT" or modality == "HRA":
            color_space = Image.COLOR_SPACE_GRAY
        else:
            color_space = Image.COLOR_SPACE_RGB

        # Set modality
        if modality == "FUN" or modality == "OBS":
            modality = settings.MODALITY_CF
        if modality == "HRA":
            modality = settings.MODALITY_IR
        modality, _ = ImagingModality.objects.get_or_create(modality=modality)

        optional_values = {}
        stereoscopic_choice = request.data.get("image_stereoscopic_choice")
        if stereoscopic_choice:
            optional_values.update(
                {"stereoscopic_choice": stereoscopic_choice}
            )

        field_of_view = request.data.get("image_field_of_view")
        if field_of_view:
            optional_values.update({"field_of_view": field_of_view})

        if request.data.get("image_width"):
            optional_values.update({"width": request.data["image_width"]})
        if request.data.get("image_height"):
            optional_values.update({"height": request.data["image_height"]})
        if request.data.get("image_depth"):
            optional_values.update({"depth": request.data["image_depth"]})

        return {
            "name": request.data.get("image_identifier"),
            "eye_choice": upperize(request.data.get("image_eye_choice")),
            "modality_id": modality.pk,
            "color_space": color_space,
            **optional_values,
        }

    @staticmethod
    def validate_model(model_dict, model_serializer):
        serializer = model_serializer(data=model_dict)
        is_valid = serializer.is_valid()
        if not is_valid:
            raise ValidationError(serializer.errors)
        return True

    @staticmethod
    def set_element_data_file_header(mhd_file, raw_file_name):
        # Read file lines into list
        f_content = mhd_file.readlines()

        # Replace line with new ElementDataFile name
        for i, line in enumerate(f_content):
            if b"ElementDataFile" in line:
                f_content[i] = "ElementDataFile = {}\n".format(
                    raw_file_name
                ).encode()

        # Write lines into new file and return
        new_file = BytesIO()
        new_file.writelines(f_content)
        new_file.seek(0)
        return InMemoryUploadedFile(
            new_file,
            "ImageField",
            mhd_file.name,
            "application/octet-stream",
            None,
            sys.getsizeof(new_file),
        )

    def save_mhd_and_raw_files(self, request, img):
        # Save MHD and ZRAW files to Image.files model
        file_name = "out"
        # Set ElementDataFile in mhd file to correct zraw filename
        raw_file_name = file_name + ".zraw"
        request.data["image_hd"] = self.set_element_data_file_header(
            request.data["image_hd"], raw_file_name
        )
        # Save mhd and zraw files
        for image_key in ("image_hd", "image_raw"):
            img_file_model = ImageFile(image=img)
            # Save image fieldfile into ImageFile, also triggers ImageFile model save method
            image_file = File(request.data[image_key])
            extension = "zraw" if image_key == "image_raw" else "mhd"
            image_name = "{}.{}".format(file_name, extension)
            img_file_model.file.save(image_name, image_file, save=True)


class AbstractUploadView(generics.CreateAPIView):
    permission_classes = (RetinaImportPermission,)
    parser_classes = (parsers.JSONParser,)
    response = {}

    # keys that should be removed from request.data.get("data") when saving
    delete_keys = ("study_identifier", "series_identifier", "image_identifier")

    # define these variables in upload views that implement this abstract class
    queryset = None
    serializer_class = None  # Upload data serializer
    child_serializer_class = None  # Child model serializer
    parent_model_class = None  # parent model
    child_model_class = (
        None
    )  # child model (for models in request.data.get("data")

    def handle_validation(self, serializer, request):
        serializer = serializer(data=request.data)
        valid = serializer.is_valid()
        if not valid:
            self.response.update({"errors": serializer.errors})
            return None, None, None, None, None

        try:
            archive = Archive.objects.get(
                name=request.data.get("archive_identifier")
            )
        except Archive.DoesNotExist:
            r = "Archive does not exist: {}".format(
                request.data.get("archive_identifier")
            )
            self.response.update({"errors": [r]})
            return None, None, None, None, None

        if request.data.get("patient_identifier") != "None":
            patient = Patient.objects.get(
                name=request.data.get("patient_identifier")
            )
        else:
            patient = None

        grader_group, group_created = Group.objects.get_or_create(
            name=settings.RETINA_GRADERS_GROUP_NAME
        )

        grader, user_created = get_user_model().objects.get_or_create(
            username=request.data.get("user_identifier").lower()
        )

        if (
            user_created
            or not grader.groups.filter(
                name=settings.RETINA_GRADERS_GROUP_NAME
            ).exists()
        ):
            grader_group.user_set.add(grader)

        annotation_datetime = datetime.datetime.strptime(
            request.data.get("datetime"), "%Y-%m-%dT%H:%M:%S.%f%z"
        )

        return archive, patient, grader, user_created, annotation_datetime

    def trace_image_through_parents(self, data, patient):
        try:
            study = Study.objects.get(
                name=data["study_identifier"], patient=patient
            )
            if data["image_identifier"] == "obs_000":
                image = Image.objects.get(
                    name=data["series_identifier"],
                    modality__modality=settings.MODALITY_CF,
                    study=study,
                )
            elif data["image_identifier"] == "oct":
                image = Image.objects.get(
                    name=data["series_identifier"],
                    modality=ImagingModality.objects.get(
                        modality=settings.MODALITY_OCT
                    ),
                    study=study,
                )
            else:
                image = Image.objects.get(
                    name=data["image_identifier"], study=study
                )
        except ObjectDoesNotExist:
            error = "Non-existant object. Data: {}".format(data)
            self.response.update({"errors": error})
            return None

        return image

    def trace_image_through_archive(
        self, image_identifier, archive_identifier
    ):
        try:
            image = Image.objects.get(
                name=image_identifier, archive__name=archive_identifier
            )
            return image
        except ObjectDoesNotExist:
            error = f"Non-existant object. Image: {image_identifier}, Archive: {archive_identifier}"
            self.response.update({"errors": error})
            return None
        except MultipleObjectsReturned:
            error = f"Multiple objects returned. Image: {image_identifier}, Archive: {archive_identifier}"
            self.response.update({"errors": error})
            return None

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

            msg = "{} already exists for {}".format(
                class_name, ", ".join(args_arr)
            )
            self.response.update({"errors": {"duplicate": msg}})

            return model

    def post(self, request, *args, **kwargs):
        self.response = {"success": False}

        archive, patient, grader, user_created, annotation_datetime = self.handle_validation(
            self.serializer_class, request
        )
        if "errors" in self.response:
            return JsonResponse(
                self.response, status=status.HTTP_400_BAD_REQUEST
            )

        if self.parent_model_class == LandmarkAnnotationSet:
            parent_model = self.parent_model_class(
                grader=grader, created=annotation_datetime
            )

            saved_model = self.create_or_return_duplicate_error_message(
                parent_model,
                {
                    "grader": grader.username,
                    "created": annotation_datetime.strftime(
                        "%Y-%m-%dT%H:%M:%S.%f%z"
                    ),
                },
            )
            if "errors" in self.response:
                return JsonResponse(
                    self.response, status=status.HTTP_400_BAD_REQUEST
                )

        if self.child_model_class:
            child_bulk_save_models = []
            serialized_models = []
            for annotation in request.data.get("data"):
                if archive.name == "kappadata":
                    image = self.trace_image_through_archive(
                        annotation["image_identifier"], archive.name
                    )
                else:
                    image = self.trace_image_through_parents(
                        annotation, patient
                    )
                if "errors" in self.response:
                    return JsonResponse(
                        self.response,
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )

                for k in self.delete_keys:
                    annotation.pop(k, None)

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
                        **annotation,
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
                                        value=polygon,
                                        annotation_set=saved_model,
                                    )
                                )
                        if len(child_bulk_save_models) > 0:
                            SinglePolygonAnnotation.objects.bulk_create(
                                child_bulk_save_models
                            )
                            child_bulk_save_models = []

            if len(child_bulk_save_models) > 0:
                self.child_model_class.objects.bulk_create(
                    child_bulk_save_models
                )
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
    serializer_class = (
        UploadLandmarkAnnotationSetSerializer
    )  # Upload data serializer
    child_serializer_class = (
        SingleLandmarkAnnotationSerializer
    )  # Child model serializer
    parent_model_class = LandmarkAnnotationSet  # parent model
    child_model_class = (
        SingleLandmarkAnnotation
    )  # child model (for models in request.data.get("data")


class UploadETDRSGridAnnotation(AbstractUploadView):
    queryset = ETDRSGridAnnotation.objects.all()
    serializer_class = (
        UploadETDRSGridAnnotationSerializer
    )  # Upload data serializer
    child_serializer_class = (
        ETDRSGridAnnotationSerializer
    )  # Child model serializer
    parent_model_class = None  # parent model
    child_model_class = (
        ETDRSGridAnnotation
    )  # child model (for models in request.data.get("data")


class UploadMeasurementAnnotation(AbstractUploadView):
    queryset = MeasurementAnnotation.objects.all()
    serializer_class = (
        UploadMeasurementAnnotationSerializer
    )  # Upload data serializer
    child_serializer_class = (
        MeasurementAnnotationSerializer
    )  # Child model serializer
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
