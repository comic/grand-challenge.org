from django import template

register = template.Library()


@register.simple_tag
def get_associated_objects(*, publication, checker):

    archives = publication.archive_set.all()
    algorithms = publication.algorithm_set.all()
    reader_studies = publication.readerstudy_set.all()
    challenges = publication.challenge_set.all()
    external_challenges = publication.externalchallenge_set.all()

    object_list = [
        *archives,
        *reader_studies,
        *challenges,
        *external_challenges,
        *algorithms,
    ]
    objects = {}
    for obj in object_list:
        if checker.has_perm(f"view_{obj._meta.model_name}", obj):
            objects[obj] = obj._meta.model_name

    return objects
