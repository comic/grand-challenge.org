import datetime
import sys
from io import BytesIO

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.files import File
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.http.response import JsonResponse
from rest_framework import generics, parsers, status

from grandchallenge.archives.models import Archive
from grandchallenge.archives.serializers import ArchiveSerializer
from grandchallenge.cases.models import Image, ImageFile
from grandchallenge.cases.serializers import ImageSerializer
from grandchallenge.challenges.models import ImagingModality
from grandchallenge.patients.models import Patient
from grandchallenge.patients.serializers import PatientSerializer
from grandchallenge.retina_importers.mixins import RetinaImportPermission
from grandchallenge.retina_importers.utils import (
    exclude_val_from_dict,
    upperize,
)
from grandchallenge.studies.models import Study
from grandchallenge.studies.serializers import StudySerializer


class CheckImage(generics.GenericAPIView):
    queryset = Image.objects.all()
    permission_classes = (RetinaImportPermission,)
    parser_classes = (parsers.JSONParser,)

    def post(self, request, *args, **kwargs):
        return JsonResponse({"exists": self.check_if_already_exists(request)})

    @staticmethod
    def check_if_already_exists(request):
        """Method that checks if a image already exists before uploading."""
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

    def post(self, request, *args, **kwargs):  # noqa: C901
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
            image_name = f"{file_name}.{extension}"
            img_file_model.file.save(image_name, image_file, save=True)
