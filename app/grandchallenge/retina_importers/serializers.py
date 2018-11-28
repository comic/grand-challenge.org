from rest_framework import serializers


class AbstractUploadSerializer(serializers.Serializer):
    archive_identifier = serializers.CharField(max_length=255, required=True)
    patient_identifier = serializers.CharField(max_length=255, required=True)
    user_identifier = serializers.CharField(max_length=150, required=True)
    datetime = serializers.DateTimeField()
    data = serializers.ListField(child=serializers.DictField())

    # Functon for validation coordinate values
    # Prefixed with do_ to disable recognition as a validate field function by serializer
    def do_validate_coordinates(self, data):
        # Validate if data is in the form of [x(float), y(float)]
        valid = True
        if not isinstance(data, list) or len(data) != 2:
            valid = False
        else:
            for point in data:
                if not isinstance(point, float) and not isinstance(point, int):
                    valid = False

        if not valid:
            raise serializers.ValidationError(
                "Coordinates in {} are not valid. Invalid value: {}".format(
                    self.__class__.__name__, data
                )
            )

    @staticmethod
    def do_validate_as_charfield(value, name, max_length=255, required=True):
        # Check if value is valid charfield
        if required and not value:
            print(value)
            raise serializers.ValidationError("{} cannot be empty".format(name))

        if not isinstance(value, str):
            raise serializers.ValidationError("{} must be a string".format(name))

        if len(value) > max_length:
            raise serializers.ValidationError(
                "{} exceeds max length of {} characters".format(name, max_length)
            )

    def validate_data(self, value):
        for dict_obj in value:
            for key, val in dict_obj.items():
                if key in ("series_identifier", "image_identifier", "study_identifier"):
                    self.do_validate_as_charfield(val, key)

        return value

    class Meta:
        abstract = True
        fields = (
            "archive_identifier",
            "patient_identifier",
            "user_identifier",
            "datetime",
            "data",
        )


class UploadLandmarkAnnotationSetSerializer(AbstractUploadSerializer):
    def validate(self, data):
        # check if amount of points equal
        length = None
        for annotation in data["data"]:
            # Uncomment to enable equal points validation check
            # if length is None:
            #     length = len(annotation["points"])
            # else:
            #     if length != len(annotation["points"]):
            #         raise serializers.ValidationError(
            #             "The amount of points in each registrations must be equal"
            #         )

            for point in annotation["landmarks"]:
                self.do_validate_coordinates(point)

        return data


class UploadETDRSGridAnnotationSerializer(AbstractUploadSerializer):
    def validate(self, data):
        # check if etdrs fovea and optic disk contain valid coordinates
        for etdrs_grid in data["data"]:
            for coordinates_type in ("fovea", "optic_disk"):
                self.do_validate_coordinates(etdrs_grid[coordinates_type])
        return data


class UploadMeasurementAnnotationSerializer(AbstractUploadSerializer):
    def validate(self, data):
        # check if start and end coordinates contain valid coordinates
        for measurement in data["data"]:
            for pos_type in ("start_voxel", "end_voxel"):
                self.do_validate_coordinates(measurement[pos_type])
        return data


class UploadBooleanClassificationAnnotationSerializer(AbstractUploadSerializer):
    def validate(self, data):
        for annotation in data["data"]:
            if not isinstance(annotation["value"], bool):
                raise serializers.ValidationError(
                    "Value in BooleanClassificationAnnotation is not a boolean"
                )
            if not isinstance(annotation["name"], str):
                raise serializers.ValidationError(
                    "Name in BooleanClassificationAnnotation is not a string"
                )
        return data


class UploadPolygonAnnotationSetSerializer(AbstractUploadSerializer):
    def validate(self, data):
        for annotation in data["data"]:
            self.do_validate_as_charfield(
                annotation["name"], "PolygonAnnotationSet.name"
            )

            for ga_polygon in annotation["value"]:
                for coordinate in ga_polygon:
                    self.do_validate_coordinates(coordinate)
        return data
