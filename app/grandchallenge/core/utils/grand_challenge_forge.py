from grandchallenge.evaluation.utils import SubmissionKindChoices


def _process_socket(socket):
    result = {
        "slug": socket.slug,
        "kind": socket.get_kind_display(),
        "super_kind": socket.super_kind.label,
        "relative_path": socket.relative_path,
        "example_value": None,
    }

    if socket.is_json_kind:
        result["example_value"] = socket.json_kind_example.value

    return result


def _process_algorithm_interfaces(algorithm_interfaces):
    result = []

    for interface in algorithm_interfaces:
        result.append(
            {
                "inputs": [
                    _process_socket(socket)
                    for socket in interface.inputs.all()
                ],
                "outputs": [
                    _process_socket(socket)
                    for socket in interface.outputs.all()
                ],
            }
        )

    return result


def get_forge_challenge_pack_context(challenge, phase_pks=None):
    """
    Generates a JSON description of the challenge and phases suitable for
    grand-challenge-forge to generate a challenge pack.
    """

    phases = challenge.phase_set.filter(
        archive__isnull=False,
        submission_kind=SubmissionKindChoices.ALGORITHM,
    ).prefetch_related(
        "archive",
        "additional_evaluation_inputs",
        "evaluation_outputs",
        "algorithm_interfaces__inputs",
        "algorithm_interfaces__outputs",
    )

    if phase_pks is not None:
        phases = phases.filter(pk__in=phase_pks)

    archives = {p.archive for p in phases}

    def process_archive(archive):
        return {
            "slug": archive.slug,
            "url": archive.get_absolute_url(),
        }

    def process_phase(phase):
        return {
            "slug": phase.slug,
            "archive": process_archive(phase.archive),
            "algorithm_interfaces": _process_algorithm_interfaces(
                phase.algorithm_interfaces.all()
            ),
            "evaluation_additional_inputs": [
                _process_socket(socket)
                for socket in phase.additional_evaluation_inputs.all()
            ],
            "evaluation_additional_outputs": [
                _process_socket(socket)
                for socket in phase.evaluation_outputs.exclude(
                    slug="metrics-json-file"
                )
            ],
        }

    return {
        "challenge": {
            "slug": challenge.slug,
            "url": challenge.get_absolute_url(),
            "phases": [process_phase(p) for p in phases],
            "archives": [process_archive(a) for a in archives],
        }
    }


def get_forge_algorithm_template_context(algorithm):
    return {
        "algorithm": {
            "title": algorithm.title,
            "slug": algorithm.slug,
            "url": algorithm.get_absolute_url(),
            "algorithm_interfaces": _process_algorithm_interfaces(
                algorithm.interfaces.all()
            ),
        }
    }
