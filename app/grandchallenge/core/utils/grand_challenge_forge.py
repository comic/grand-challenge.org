from grandchallenge.evaluation.utils import SubmissionKindChoices


def _process_component_interface(component_interface):
    result = {
        "slug": component_interface.slug,
        "kind": component_interface.get_kind_display(),
        "super_kind": component_interface.super_kind.label,
        "relative_path": component_interface.relative_path,
        "example_value": None,
    }

    if component_interface.is_json_kind:
        result["example_value"] = component_interface.json_kind_example.value

    return result


def get_forge_challenge_pack_context(challenge, phase_pks=None):
    """
    Generates a JSON description of the challenge and phases suitable for
    grand-challenge-forge to generate a challenge pack.
    """

    phases = challenge.phase_set.filter(
        archive__isnull=False,
        submission_kind=SubmissionKindChoices.ALGORITHM,
    ).prefetch_related("archive", "algorithm_interfaces")

    if phase_pks is not None:
        phases = phases.filter(pk__in=phase_pks)

    archives = {p.archive for p in phases}

    def process_archive(archive):
        return {
            "slug": archive.slug,
            "url": archive.get_absolute_url(),
        }

    def process_phase(phase):
        interfaces = phase.algorithm_interfaces.all()
        inputs = {
            ci for interface in interfaces for ci in interface.inputs.all()
        }
        outputs = {
            ci for interface in interfaces for ci in interface.outputs.all()
        }
        return {
            "slug": phase.slug,
            "archive": process_archive(phase.archive),
            "algorithm_inputs": [
                _process_component_interface(ci) for ci in inputs
            ],
            "algorithm_outputs": [
                _process_component_interface(ci) for ci in outputs
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
    interfaces = algorithm.interfaces.all()
    inputs = {ci for interface in interfaces for ci in interface.inputs.all()}
    outputs = {
        ci for interface in interfaces for ci in interface.outputs.all()
    }
    return {
        "algorithm": {
            "title": algorithm.title,
            "slug": algorithm.slug,
            "url": algorithm.get_absolute_url(),
            "inputs": [_process_component_interface(ci) for ci in inputs],
            "outputs": [_process_component_interface(ci) for ci in outputs],
        }
    }
