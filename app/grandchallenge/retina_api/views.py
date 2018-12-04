import json
from django.utils import timezone
from django.views import View
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http.response import HttpResponse, JsonResponse
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.core.cache import cache, caches, InvalidCacheBackendError
from django.shortcuts import redirect
from django.contrib.auth import get_user_model
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from grandchallenge.retina_api.mixins import RetinaAPIPermission, RetinaAPIPermissionMixin
from grandchallenge.archives.models import Archive
from grandchallenge.patients.models import Patient
from grandchallenge.studies.models import Study
from grandchallenge.retina_images.models import RetinaImage
from grandchallenge.annotations.models import PolygonAnnotationSet, LandmarkAnnotationSet


class ArchiveView(APIView):
    permission_classes = (RetinaAPIPermission,)

    @staticmethod
    def create_response_object():
        archives = Archive.objects.all()
        patients = Patient.objects.all().prefetch_related(
            "study_set",
            "study_set__retinaimage_set",
            "study_set__retinaimage_set__obs_image",
            "study_set__retinaimage_set__oct_image",
            "study_set__retinaimage_set__archive_set",
        )

        def generate_archives(archive_list, patients):
            for archive in archive_list:
                yield archive.name, {
                    "subfolders": dict(generate_patients(archive, patients)),
                    "info": "level 3",
                    "name": archive.name,
                    "id": archive.id,
                    "images": {},
                }

        def generate_patients(archive, patients):
            patient_list = patients.filter(
                study__retinaimage__archive=archive
            ).distinct()
            for patient in patient_list:
                if archive.name == "Australia":
                    image_set = {}
                    for study in patient.study_set.all():
                        image_set.update(dict(generate_images(study.retinaimage_set)))
                    yield patient.name, {
                        "subfolders": {},
                        "info": "level 4",
                        "name": patient.name,
                        "id": patient.id,
                        "images": image_set,
                    }
                else:
                    yield patient.name, {
                        "subfolders": dict(generate_studies(patient.study_set)),
                        "info": "level 4",
                        "name": patient.name,
                        "id": patient.id,
                        "images": {},
                    }

        def generate_studies(study_list):
            for study in study_list.all():
                yield study.name, {
                    "info": "level 5",
                    "images": dict(generate_images(study.retinaimage_set)),
                    "name": study.name,
                    "id": study.id,
                    "subfolders": {},
                }

        def generate_images(image_list):
            for image in image_list.all():
                if image.modality == RetinaImage.MODALITY_OCT:
                    if image.number != 0:  # only add data for first oct image in set
                        continue
                    # oct image add info
                    try:
                        obs_list = image.oct_image.get().registration_values
                        obs_registration_flat = [
                            val for sublist in obs_list for val in sublist
                        ]
                    except ObjectDoesNotExist:
                        obs_registration_flat = []

                    voxel_size = [0, 0, 0]
                    if image.voxel_size:
                        voxel_size = image.voxel_size
                    study_datetime = "Unknown"
                    if image.study.datetime:
                        study_datetime = image.study.datetime.strftime(
                            "%Y/%m/%d %H:%M:%S"
                        )

                    yield image.name, {
                        "images": {
                            "trc_000": "no info",
                            "obs_000": "no info",
                            "mot_comp": "no info",
                            "trc_001": "no info",
                            "oct": "no info",
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
                elif image.modality == RetinaImage.MODALITY_OBS:
                    # skip, already in fds
                    pass
                else:
                    yield image.name, "no tags"

        response = {
            "subfolders": dict(generate_archives(archives, patients)),
            "info": "level 2",
            "name": "GA Archive",
            "id": "none",
            "images": {},
        }
        return response

    def get(self, request):
        return Response(self.create_response_object())


class ImageView(RetinaAPIPermissionMixin, View):
    def get(
        self,
        request,
        image_type,
        patient_identifier,
        study_identifier,
        image_identifier,
        image_modality,
    ):
        # This works good only if name for series is unique. (should be but is not enforced)
        if patient_identifier == "Australia":
            # BMES data contains no study name, switched up parameters
            image = RetinaImage.objects.filter(
                study__patient__name=study_identifier,  # this argument contains patient identifier
                name=image_identifier,
            )
        else:
            image = RetinaImage.objects.filter(
                name=image_identifier,
                study__name=study_identifier,
                study__patient__name=patient_identifier,
            )

        try:
            if image_modality == "obs_000":
                image = image.get(modality=RetinaImage.MODALITY_OBS)
            elif image_modality == "oct":
                qs = RetinaImage.objects.filter(
                    study__name=study_identifier,
                    study__patient__name=patient_identifier,
                    modality=RetinaImage.MODALITY_OCT,
                )
                number = len(qs)
                image = qs.get(number=number // 2)
            else:
                image = image.get()
        except MultipleObjectsReturned:
            print("failed unique image search")

        if image_type == "thumb":
            response = redirect("retina:image-thumbnail", image_id=image.id)
        else:
            response = redirect("retina:image-numpy", image_id=image.id)

        # Set token authentication header to pass on
        #response["AUTHORIZATION"] = "Token " + request.META["HTTP_AUTHORIZATION"]
        return response


class DataView(APIView):
    permission_classes = (RetinaAPIPermission,)

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
        self, images, user, model_set, extra_conditions={}
    ):
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
            date_key = annotation_model.created.strftime("%Y-%m-%d--%H-%M-%S--%f")
            image_name = annotation_model.image.name
            if data_type == "ETDRS":
                result_data = {
                    "fovea": self.coordinate_to_dict(annotation_model.fovea),
                    "optic_disk": self.coordinate_to_dict(annotation_model.optic_disk),
                }
            elif data_type == "Fovea":
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
                {"modality": RetinaImage.MODALITY_OCT, "number": 0}
            )  # set number for oct images
        elif image_identifier == "obs_000":
            conditions.update({"modality": RetinaImage.MODALITY_OBS})
        return RetinaImage.objects.get(
            study__patient=patient,
            study__name=request_data.get("visit_nr"),
            name=request_data.get("img_name"),
            **conditions,
        )

    def get(self, request, data_type, username, archive_identifier, patient_identifier):
        data = {}
        images = RetinaImage.objects.filter(
            study__patient__name=patient_identifier, archive__name=archive_identifier
        )

        user = get_user_model().objects.get(username=username.lower())

        if data_type == "Registration":
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
                if archive_identifier == "Australia":
                    image_name = annotation.image.name

                    result_dict = {
                        image_name: self.coordinates_list_to_dict(annotation.landmarks)
                    }

                    if data.get(date_key):
                        data[date_key].update(result_dict)
                    else:
                        data.update({date_key: result_dict})
                else:
                    result_dict = {
                        "points": self.coordinates_list_to_dict(annotation.landmarks),
                        "visit_nr": annotation.image.study.name,
                        "img_name": annotation.image.name,
                    }
                    if annotation.image.modality == RetinaImage.MODALITY_OBS:
                        result_dict.update({"sub_img_name": "obs_000"})
                    if annotation.image.modality == RetinaImage.MODALITY_OCT:
                        result_dict.update({"sub_img_name": "oct"})
                    if data.get(date_key):
                        data[date_key].append(result_dict)
                    else:
                        data.update({date_key: [result_dict]})

        elif data_type == "ETDRS":
            annotation_models = self.get_models_related_to_image_and_user(
                images, user, "etdrsgridannotation_set"
            )

            for annotation_model in annotation_models:
                date_key = annotation_model.created.strftime("%Y-%m-%d--%H-%M-%S--%f")
                image_name = annotation_model.image.name
                result_data = {
                    "fovea": self.coordinate_to_dict(annotation_model.fovea),
                    "optic_disk": self.coordinate_to_dict(annotation_model.optic_disk),
                }
                if archive_identifier == "Australia":
                    result_dict = {image_name: result_data}
                    data.update(result_dict)
                else:
                    result_data.update(
                        {
                            "visit_nr": annotation_model.image.study.name,
                            "img_name": image_name,
                        }
                    )

                    if annotation_model.image.modality == RetinaImage.MODALITY_OBS:
                        result_dict.update({"sub_img_name": "obs_000"})
                    if annotation_model.image.modality == RetinaImage.MODALITY_OCT:
                        result_dict.update({"sub_img_name": "oct"})
                    if data.get(date_key):
                        data[date_key].update(result_data)
                    else:
                        data.update({date_key: result_data})

        elif data_type == "Measure":
            annotation_models = self.get_models_related_to_image_and_user(
                images, user, "measurementannotation_set"
            )

            for annotation_model in annotation_models:
                date_key = annotation_model.created.strftime("%Y-%m-%d--%H-%M-%S--%f")
                image_name = annotation_model.image.name
                result_data = {
                    "from": self.coordinate_to_dict(annotation_model.start_voxel),
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
        elif data_type == "Fovea":
            annotation_models = self.get_models_related_to_image_and_user(
                images,
                user,
                "booleanclassificationannotation_set",
                {"name": "fovea_affected"},
            )
            data = self.create_annotation_data_australia(data_type, annotation_models)
        elif data_type == "GA":
            annotation_models = self.get_models_related_to_image_and_user(
                images, user, "polygonannotationset_set"
            )

            for annotation_model in annotation_models:
                ga_type = annotation_model.name.capitalize()
                for spa in annotation_model.singlepolygonannotation_set.all():
                    date_key = annotation_model.created.strftime(
                        "%Y-%m-%d--%H-%M-%S--%f"
                    )
                    result_data_points = self.coordinates_list_to_dict(spa.value)

                    image_name = annotation_model.image.name
                    opposing_type = (
                        "Peripapillary" if ga_type == "Macular" else "Macular"
                    )
                    result_data = {
                        ga_type: [result_data_points],
                        opposing_type: [],  # Add opposing GA type to object to prevent front-end error
                    }
                    series_name = image_name
                    if archive_identifier != "Australia":
                        visit_id = annotation_model.image.study.name
                        sub_img_name = None
                        if annotation_model.image.modality == RetinaImage.MODALITY_OBS:
                            sub_img_name = "obs_000"
                        if annotation_model.image.modality == RetinaImage.MODALITY_OCT:
                            sub_img_name = "oct"

                        img_name = [image_name, sub_img_name]
                        sub_img_name = '' if sub_img_name is None else sub_img_name
                        series_name = visit_id + image_name + sub_img_name

                        result_data.update({"visit_nr": visit_id, "img_name": img_name})

                    result_dict = {series_name: result_data}
                    if data.get(date_key):
                        if data[date_key].get(series_name):
                            if data[date_key][series_name].get(ga_type) is None:
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

    @method_decorator(ensure_csrf_cookie)
    def put(self, request, data_type, username, archive_identifier, patient_identifier):
        request_data = json.loads(request.body)
        patient = Patient.objects.filter(
            name=patient_identifier, study__retinaimage__archive__name=archive_identifier
        ).distinct().get()
        user = get_user_model().objects.get(username=username.lower())

        save_data = {"grader": user, "created": timezone.now()}
        if data_type == "Registration":
            # Create parent LandmarkAnnotationSet model to link landmarks to
            landmark_annotation_set_model = LandmarkAnnotationSet.objects.create(**save_data)

        if archive_identifier == "Australia":
            # Australia
            for image_name, data in request_data.items():
                image = RetinaImage.objects.get(
                    name=image_name, study__patient=patient
                )
                if data_type == "ETDRS":
                    image.etdrsgridannotation_set.create(
                        **save_data,
                        fovea=self.dict_to_coordinate(data["fovea"]),
                        optic_disk=self.dict_to_coordinate(data["optic_disk"]),
                    )
                elif data_type == "GA":
                    for ga_type, ga_data_list in data.items():
                        if not ga_data_list:
                            continue  # skip empty arrays
                        ga_points_model = image.polygonannotationset_set.create(
                            **save_data, name=ga_type.lower()
                        )
                        for ga_data in ga_data_list:
                            ga_points_model.singlepolygonannotation_set.create(
                                value=self.dict_list_to_coordinates(ga_data)
                            )
                elif data_type == "Fovea":
                    image.booleanclassificationannotation_set.create(
                        **save_data, name="fovea_affected", value=data["fovea_affected"]
                    )
                elif data_type == "Measure":
                    for measurement in data:
                        image.measurementannotation_set.create(
                            **save_data,
                            start_voxel=self.dict_to_coordinate(
                                measurement["from"]
                            ),
                            end_voxel=self.dict_to_coordinate(measurement["to"]),
                        )
                elif data_type == "Registration":
                    landmark_annotation_set_model.singlelandmarkannotation_set.create(
                        image=image, landmarks=self.dict_list_to_coordinates(data)
                    )
        else:
            # Rotterdam study data
            data = request_data
            if data_type == "ETDRS":
                image = self.get_image_from_rotterdam_data(patient, data)
                image.etdrsgridannotation_set.create(
                    **save_data,
                    fovea=self.dict_to_coordinate(data["fovea"]),
                    optic_disk=self.dict_to_coordinate(data["optic_disk"]),
                )
            elif data_type == "Registration":
                for registration in data:
                    image = self.get_image_from_rotterdam_data(patient, registration)
                    landmark_annotation_set_model.singlelandmarkannotation_set.create(
                        image=image,
                        landmarks=self.dict_list_to_coordinates(registration["points"]),
                    )
            elif data_type == "GA":
                for visit_image_name, ga_data in data.items():
                    conditions = {}
                    if ga_data["img_name"][1] == "obs_000":
                        conditions.update({"modality": RetinaImage.MODALITY_OBS})
                    elif ga_data["img_name"][1] == "oct":
                        conditions.update({"modality": RetinaImage.MODALITY_OCT})

                    image = RetinaImage.objects.get(
                        study__name=ga_data["visit_nr"],
                        study__patient=patient,
                        name=ga_data["img_name"][0],
                        **conditions
                    )
                    for ga_type, ga_data_list in ga_data.items():
                        if ga_type in ("img_name", "visit_nr") or not ga_data_list:
                            continue  # skip non ga elements in dict
                        ga_points_model = image.polygonannotationset_set.create(
                            **save_data, name=ga_type.lower()
                        )
                        for single_ga_data in ga_data_list:
                            ga_points_model.singlepolygonannotation_set.create(
                                value=self.dict_list_to_coordinates(single_ga_data)
                            )

        return Response({"success": True}, status=status.HTTP_201_CREATED)
