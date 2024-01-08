from grandchallenge.evaluation.utils import SubmissionKindChoices
from grandchallenge.subdomains.utils import reverse


def get_forge_json_description(challenge, phase_pks=None):
    """
    Generates a JSON description of the challenge and phases suitable for
    grand-challenge-forge to generate a challenge pack.
    """

    phases = challenge.phase_set.filter(
        archive__isnull=False,
        submission_kind=SubmissionKindChoices.ALGORITHM,
    ).prefetch_related("archive", "algorithm_inputs", "algorithm_outputs")

    if phase_pks is not None:
        phases = phases.filter(pk__in=phase_pks)

    archives = {p.archive for p in phases}

    def process_archive(archive):
        return {
            "slug": archive.slug,
            "url": reverse("archives:detail", kwargs={"slug": archive.slug}),
        }

    def process_component_interface(component_interface):
        return {
            "slug": component_interface.slug,
            "kind": component_interface.get_kind_display(),
            "super_kind": component_interface.super_kind.label,
            "relative_path": component_interface.relative_path,
        }

    def process_phase(phase):
        return {
            "slug": phase.slug,
            "archive": process_archive(phase.archive),
            "algorithm_inputs": [
                process_component_interface(ci)
                for ci in phase.algorithm_inputs.all()
            ],
            "algorithm_outputs": [
                process_component_interface(ci)
                for ci in phase.algorithm_outputs.all()
            ],
        }

    return {
        "challenge": {
            "slug": challenge.slug,
            "phases": [process_phase(p) for p in phases],
            "archives": [process_archive(a) for a in archives],
        }
    }
