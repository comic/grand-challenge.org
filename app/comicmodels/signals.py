from django.dispatch import Signal

file_uploaded = Signal(providing_args=["uploader", "filename", "comicsite"])
new_admin = Signal(providing_args=["adder", "new_admin", "comicsite"])
new_participant = Signal(providing_args=["user", "comicsite"])
new_submission = Signal(providing_args=["submission", "comicsite"])
removed_admin = Signal(providing_args=["user", "removed_admin", "comicsite"])
