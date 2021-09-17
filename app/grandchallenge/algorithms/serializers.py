from typing import Optional

from guardian.shortcuts import assign_perm
from rest_framework import serializers
from rest_framework.fields import (
    CharField,
    SerializerMethodField,
    URLField,
)
from rest_framework.relations import (
    HyperlinkedRelatedField,
    StringRelatedField,
)

from grandchallenge.algorithms.models import Algorithm, AlgorithmImage, Job
from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
)
from grandchallenge.components.serializers import (
    ComponentInterfaceSerializer,
    ComponentInterfaceValuePostSerializer,
    ComponentInterfaceValueSerializer,
    HyperlinkedComponentInterfaceValueSerializer,
)


class AlgorithmSerializer(serializers.ModelSerializer):
    average_duration = SerializerMethodField()
    inputs = ComponentInterfaceSerializer(many=True)
    outputs = ComponentInterfaceSerializer(many=True)
    logo = URLField(source="logo.x20.url", read_only=True)
    url = URLField(source="get_absolute_url", read_only=True)

    class Meta:
        model = Algorithm
        fields = [
            "api_url",
            "url",
            "description",
            "pk",
            "title",
            "logo",
            "slug",
            "average_duration",
            "inputs",
            "outputs",
        ]

    def get_average_duration(self, obj: Algorithm) -> Optional[float]:
        """The average duration of successful jobs in seconds"""
        if obj.average_duration is None:
            return None
        else:
            return obj.average_duration.total_seconds()


class AlgorithmImageSerializer(serializers.ModelSerializer):
    algorithm = HyperlinkedRelatedField(
        read_only=True, view_name="api:algorithm-detail"
    )

    class Meta:
        model = AlgorithmImage
        fields = ["pk", "api_url", "algorithm"]


class JobSerializer(serializers.ModelSerializer):
    """Serializer without hyperlinks for internal use"""

    algorithm_image = StringRelatedField()
    inputs = ComponentInterfaceValueSerializer(many=True)
    outputs = ComponentInterfaceValueSerializer(many=True)

    status = CharField(source="get_status_display", read_only=True)
    algorithm_title = CharField(
        source="algorithm_image.algorithm.title", read_only=True
    )

    class Meta:
        model = Job
        fields = [
            "pk",
            "api_url",
            "algorithm_image",
            "inputs",
            "outputs",
            "status",
            "rendered_result_text",
            "algorithm_title",
            "started_at",
            "completed_at",
        ]


class HyperlinkedJobSerializer(JobSerializer):
    """Serializer with hyperlinks for use in public API"""

    algorithm_image = HyperlinkedRelatedField(
        queryset=AlgorithmImage.objects.all(),
        view_name="api:algorithms-image-detail",
    )
    inputs = HyperlinkedComponentInterfaceValueSerializer(many=True)
    outputs = HyperlinkedComponentInterfaceValueSerializer(many=True)

    class Meta(JobSerializer.Meta):
        pass


class JobPostSerializer(JobSerializer):
    algorithm = HyperlinkedRelatedField(
        queryset=Algorithm.objects.all(),
        view_name="api:algorithm-detail",
        write_only=True,
    )
    inputs = ComponentInterfaceValuePostSerializer(many=True)

    class Meta:
        model = Job
        fields = ["pk", "algorithm", "inputs", "status"]

    def validate(self, data):
        alg = data.pop("algorithm")
        user = self.context.get("user")

        if not user.has_perm("execute_algorithm", alg):
            raise serializers.ValidationError(
                f"User does not have permission to use algorithm {alg}"
            )

        if not alg.latest_ready_image:
            raise serializers.ValidationError(
                "Algorithm image is not ready to be used"
            )
        data["creator"] = user
        data["algorithm_image"] = alg.latest_ready_image

        # validate that no inputs are provided that are not configured for the
        # algorithm and that all interfaces without defaults are provided
        algorithm_input_pks = {a.pk for a in alg.inputs.all()}
        input_pks = {i["interface"].pk for i in data["inputs"]}

        # surplus inputs: provided but interfaces not configured for the algorithm
        surplus = ComponentInterface.objects.filter(
            id__in=list(input_pks - algorithm_input_pks)
        )
        if surplus:
            titles = ", ".join(ci.title for ci in surplus)
            raise serializers.ValidationError(
                f"Provided inputs(s) {titles} are not defined for this algorithm"
            )

        # missing inputs
        missing = alg.inputs.filter(
            id__in=list(algorithm_input_pks - input_pks),
            default_value__isnull=True,
        )
        if missing:
            titles = ", ".join(ci.title for ci in missing)
            raise serializers.ValidationError(
                f"Interface(s) {titles} do not have a default value and should be provided."
            )

        return data

    def create(self, validated_data):
        inputs_data = validated_data.pop("inputs")
        job = Job.objects.create(**validated_data)

        # TODO AUG2021 JM permission management should be done in 1 place
        # The execution for jobs over the API or non-sessions needs
        # to be cleaned up. See callers of `execute_jobs`.
        editors_group = job.algorithm_image.algorithm.editors_group
        job.viewer_groups.add(editors_group)
        assign_perm("algorithms.view_logs", editors_group, job)

        component_interface_values = []
        upload_pks = {}
        for input_data in inputs_data:
            # check for upload_session in input
            upload_session = input_data.pop("upload_session", None)
            civ = ComponentInterfaceValue(**input_data)
            if upload_session:
                # CIVs with upload sessions cannot be validated, done in
                # run_algorithm_job_for_inputs
                civ.save()
                upload_pks[civ.pk] = upload_session.pk
            else:
                civ.full_clean()
                civ.save()
            component_interface_values.append(civ)

        # use interface defaults if no value was provided
        algorithm_input_pks = {
            a.pk for a in job.algorithm_image.algorithm.inputs.all()
        }
        input_pks = {i["interface"].pk for i in inputs_data}
        defaults = job.algorithm_image.algorithm.inputs.filter(
            id__in=list(algorithm_input_pks - input_pks),
            default_value__isnull=False,
        )

        for d in defaults:
            civ = ComponentInterfaceValue(
                interface_id=d.id, value=d.default_value
            )
            civ.full_clean()
            civ.save()
            component_interface_values.append(civ)

        job.inputs.add(*component_interface_values)
        job.run_job(upload_pks=upload_pks)

        return job
