import datetime

import factory.fuzzy
import pytz

from grandchallenge.studies.models import Study
from tests.patients_tests.factories import PatientFactory


class StudyFactory(factory.DjangoModelFactory):
    class Meta:
        model = Study

    name = factory.Sequence(lambda n: f"Study {n}")
    patient = factory.SubFactory(PatientFactory)
    datetime = factory.fuzzy.FuzzyDateTime(
        datetime.datetime(1950, 1, 1, 0, 0, 0, 0, pytz.UTC)
    )
