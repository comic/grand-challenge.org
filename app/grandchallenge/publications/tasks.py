import logging

from requests.exceptions import RequestException

from grandchallenge.core.celery import acks_late_2xlarge_task
from grandchallenge.publications.models import Publication

logger = logging.getLogger(__name__)


@acks_late_2xlarge_task
def update_publication_metadata():
    pks_to_delete = []

    for publication in Publication.objects.iterator():
        try:
            csl, new_identifier = publication.identifier.csl
        except ValueError:
            logger.warning(
                f"Identifier {publication.identifier} not recognised"
            )
            continue
        except RequestException as e:
            logger.warning(f"Error updating {publication.identifier}: {e}")
            continue

        if (
            Publication.objects.filter(identifier=new_identifier)
            .exclude(pk=publication.pk)
            .exists()
        ):
            merge_publications(
                old_publication=publication, new_identifier=new_identifier
            )
            pks_to_delete.append(publication.pk)
        else:
            publication.identifier = new_identifier
            publication.csl = csl
            publication.save()

    Publication.objects.filter(pk__in=pks_to_delete).delete()


def merge_publications(*, old_publication, new_identifier):
    new_publication = Publication.objects.get(identifier=new_identifier)

    for field in Publication.get_reverse_many_to_many_fields():
        getattr(new_publication, field).add(
            *getattr(old_publication, field).all()
        )
