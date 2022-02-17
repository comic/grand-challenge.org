import logging

from celery import shared_task
from django.conf import settings
from requests.exceptions import RequestException

from grandchallenge.publications.models import Publication
from grandchallenge.publications.utils import get_identifier_csl

logger = logging.getLogger(__name__)


@shared_task(**settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-2xlarge"])
def update_publication_metadata():
    for publication in Publication.objects.all():
        try:
            csl, new_identifier = get_identifier_csl(
                doi_or_arxiv=publication.identifier
            )
        except ValueError:
            logger.warning(
                f"Identifier {publication.identifier} not recognised"
            )
            continue
        except RequestException as e:
            logger.warning(f"Error updating {publication.identifier}: {e}")
            continue

        publication.identifier = new_identifier
        publication.csl = csl
        publication.save()
