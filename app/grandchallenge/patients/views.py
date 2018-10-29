from grandchallenge.patients.models import Patient
from grandchallenge.patients.serializer import PatientSerializer
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from rest_framework import generics
from django_filters.rest_framework import DjangoFilterBackend


class PatientTable(generics.ListCreateAPIView):
    serializer_class = PatientSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_fields = ('id', 'name', 'sex')

    def get_queryset(self):
        # Get URL parameter as a string, if exists
        ids = self.request.query_params.get('ids', None)

        # Get snippets for ids if they exist
        if ids is not None:
            # Convert parameter string to list of integers
            ids = [int(x) for x in ids.split(',')]
            # Get objects for all parameter ids
            queryset = Patient.objects.filter(pk__in=ids)

        else:
            # Else no parameters, return all objects
            queryset = Patient.objects.all()

        return queryset


class PatientRecord(generics.RetrieveUpdateDestroyAPIView):
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer


class PatientCreate(CreateView):
    model = Patient
    fields = '__all__'


class PatientUpdate(UpdateView):
    model = Patient
    fields = '__all__'


class PatientDelete(DeleteView):
    model = Patient
    success_url = reverse_lazy('patients')
