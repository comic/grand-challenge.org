from grandchallenge.evaluation.models import Phase
from grandchallenge.evaluation.utils import SubmissionKindChoices
from grandchallenge.subdomains.utils import reverse


def get_forge_json_description(challenge, phases_queryset=None):
    """
    Generates a JSON description of the challenge and phases suitable for
    grand-challenge-forge to generate a challenge pack.
    """

    if phases_queryset is None:
        phases_queryset = Phase.objects.filter(challenge=challenge)

    phases = phases_queryset.filter(
        archive__isnull=False,
        submission_kind=SubmissionKindChoices.ALGORITHM,
    ).prefetch_related("archive", "inputs", "outputs")

    archives = {p.archive.id: p.archive for p in phases}.values()

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
            "inputs": [
                process_component_interface(ci) for ci in phase.inputs.all()
            ],
            "outputs": [
                process_component_interface(ci) for ci in phase.outputs.all()
            ],
        }

    return {
        "challenge": {
            "slug": challenge.slug,
            "phases": [process_phase(p) for p in phases],
            "archives": [process_archive(a) for a in archives],
        }
    }
