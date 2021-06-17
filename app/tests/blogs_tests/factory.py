import factory

from grandchallenge.blogs.models import Post
from tests.factories import UserFactory


class PostFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Post

    @factory.post_generation
    def authors(self, create, extracted, **kwargs):
        # See https://factoryboy.readthedocs.io/en/latest/recipes.html#simple-many-to-many-relationship
        if not create:
            return
        if extracted:
            self.authors.set([*extracted])
        if create and not extracted:
            self.authors.set([UserFactory()])
