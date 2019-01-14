from django.core.exceptions import ObjectDoesNotExist
from rest_framework import permissions, generics, parsers, status, serializers
import datetime
import uuid
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


class UploadImage(generics.CreateAPIView):
    queryset = Image.objects.all()
    permission_classes = (permissions.IsAdminUser,)
    parser_classes = (parsers.MultiPartParser,)

    def post(self, request, *args, **kwargs):
        errors, archive_dict, patient_dict, study_dict, image_dict = self.create_model_dicts(
            request
        )

        if errors:
            return JsonResponse(errors, status=status.HTTP_400_BAD_REQUEST)

        # get existing or create new data structure models in database
        archive, archive_created = Archive.objects.get_or_create(
            **archive_dict
        )
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
        # Check if image already exists in database
        try:
            img = Image.objects.get(study=study, **image_dict)
            # Image already exists. Do nothing and return response
        except Image.DoesNotExist:
            # Image does not exist yet.
            img = Image.objects.create(study=study, **image_dict)

            # Create ImageFile object without linking image file and without saving
            random_uuid_str = str(uuid.uuid4())

            # Set ElementDataFile in mhd file to correct zraw filename
            raw_file_name = random_uuid_str + ".zraw"
            request.data["image_hd"] = self.set_element_data_file_header(
                request.data["image_hd"], raw_file_name
            )
            for image_key in ("image_hd", "image_raw"):
                img_file_model = ImageFile(image=img)

                # Save image fieldfile into ImageFile, also triggers ImageFile model save method
                image_file = File(request.data[image_key])
                extension = "zraw" if image_key == "image_raw" else "mhd"
                image_name = "{}.{}".format(random_uuid_str, extension)
                img_file_model.file.save(image_name, image_file, save=True)

            archive.images.add(img)
            image_created = True
        except Exception as e:
            return JsonResponse(
                {"error": e}, status=status.HTTP_400_BAD_REQUEST
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
            "image": ImageSerializer(img).data,
        }
        response_status = status.HTTP_201_CREATED
        if not image_created:
            response_status = status.HTTP_400_BAD_REQUEST

        return JsonResponse(response_obj, status=response_status)

    def create_model_dicts(self, request):
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

        image_dict = {
            "name": request.data.get("image_identifier"),
            "eye_choice": upperize(request.data.get("image_eye_choice")),
            "modality_id": modality.pk,
            "color_space": color_space,
            "width": request.data.get("image_width"),
            "height": request.data.get("image_height"),
            "depth": request.data.get("image_depth"),
        }

        # Perform validation with serializers
        archive_serializer = ArchiveSerializer(data=archive_dict)
        patient_serializer = PatientSerializer(data=patient_dict)
        study_serializer = StudySerializer(data=study_dict)
        image_serializer = ImageSerializer(data=image_dict)
        archive_valid = archive_serializer.is_valid()
        patient_valid = patient_serializer.is_valid()
        study_valid = study_serializer.is_valid()
        image_valid = image_serializer.is_valid()

        if (
            not archive_valid
            or not patient_valid
            or not study_valid
            or not image_valid
        ):
            errors = {
                "archive_errors": archive_serializer.errors,
                "patient_errors": patient_serializer.errors,
                "study_errors": study_serializer.errors,
                "image_errors": image_serializer.errors,
            }
        else:
            errors = None

        return (errors, archive_dict, patient_dict, study_dict, image_dict)

    def set_element_data_file_header(self, mhd_file, raw_file_name):
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

        patient = Patient.objects.get(
            name=request.data.get("patient_identifier")
        )

        grader_group, group_created = Group.objects.get_or_create(
            name=settings.RETINA_GRADERS_GROUP_NAME
        )

        grader, user_created = get_user_model().objects.get_or_create(
            username=request.data.get("user_identifier").lower()
        )

        if (
            user_created
            or grader.groups.filter(
                name=settings.RETINA_GRADERS_GROUP_NAME
            ).count()
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
                image = self.trace_image_through_parents(annotation, patient)
                if "errors" in self.response:
                    return JsonResponse(
                        self.response,
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
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
