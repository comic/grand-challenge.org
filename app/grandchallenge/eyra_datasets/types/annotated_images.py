from grandchallenge.eyra_datasets.types.base_type import BaseType


class AnnotatedImages(BaseType):
    name = "annotated_images"
    verbose_name = "Annotated Images"
    files = ["train_images", "train_labels", "test_images", "test_labels"]
