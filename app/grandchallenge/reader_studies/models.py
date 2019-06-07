from django_extensions.db.models import TitleSlugDescriptionModel

from grandchallenge.core.models import UUIDModel


class ReaderStudy(UUIDModel, TitleSlugDescriptionModel):
    class Meta(UUIDModel.Meta, TitleSlugDescriptionModel.Meta):
        verbose_name_plural = "reader studies"
