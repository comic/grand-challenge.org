from django.conf import settings
from django.contrib.auth.models import Group

from tests.factories import UserFactory
from tests.reader_studies_tests.factories import ReaderStudyFactory


def get_rs_creator():
    creator = UserFactory()
    g = Group.objects.get(name=settings.READER_STUDY_CREATORS_GROUP_NAME)
    g.user_set.add(creator)
    return creator


class TwoReaderStudies:
    def __init__(self):
        self.creator = get_rs_creator()
        self.rs1, self.rs2 = ReaderStudyFactory(), ReaderStudyFactory()
        self.editor1, self.reader1, self.editor2, self.reader2 = (
            UserFactory(),
            UserFactory(),
            UserFactory(),
            UserFactory(),
        )
        self.rs1.add_editor(user=self.editor1)
        self.rs2.add_editor(user=self.editor2)
        self.rs1.add_reader(user=self.reader1)
        self.rs2.add_reader(user=self.reader2)
        self.u = UserFactory()
