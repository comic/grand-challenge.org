import factory

from grandchallenge.patients.models import Patient


class PatientFactory(factory.DjangoModelFactory):
    class Meta:
        model = Patient

    name = factory.Sequence(lambda n: f"Patient {n}")
