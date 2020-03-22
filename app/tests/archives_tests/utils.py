from tests.archives_tests.factories import ArchiveFactory
from tests.factories import UserFactory


class TwoArchives:
    def __init__(self):
        self.arch1, self.arch2 = ArchiveFactory(), ArchiveFactory()
        (
            self.editor1,
            self.uploader1,
            self.user1,
            self.editor2,
            self.uploader2,
            self.user2,
        ) = (
            UserFactory(),
            UserFactory(),
            UserFactory(),
            UserFactory(),
            UserFactory(),
            UserFactory(),
        )
        self.arch1.add_editor(user=self.editor1)
        self.arch2.add_editor(user=self.editor2)
        self.arch1.add_uploader(user=self.uploader1)
        self.arch2.add_uploader(user=self.uploader2)
        self.arch1.add_user(user=self.user1)
        self.arch2.add_user(user=self.user2)
        self.u = UserFactory()
