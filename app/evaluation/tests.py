from evaluation.models import Job
from comicmodels.models import UploadModel
from comicsite.tests import ComicframeworkTestCase


class EvaluationModelTest(ComicframeworkTestCase):
    def setUp_extra(self):
        [self.testproject,
         self.root,
         self.projectadmin,
         self.participant,
         self.registered_user] = self._create_dummy_project("evaluation-test")

    def test_job_creation(self):
        file = UploadModel()
        file.comicsite = self.testproject
        file.user = self.participant
        file.save()

        job = Job()
        job.submitted_file = file
        job.save()

        self.assertEqual(Job.objects.all().count(), 1)
