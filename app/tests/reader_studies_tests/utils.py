from tests.factories import UserFactory
from tests.reader_studies_tests.factories import ReaderStudyFactory


class TwoReaderStudies:
    def __init__(self):
        self.creator = UserFactory()
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
