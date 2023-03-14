import pytest

from tests.algorithms_tests.factories import AlgorithmFactory
from tests.archives_tests.factories import ArchiveFactory
from tests.evaluation_tests.test_permissions import get_groups_with_set_perms
from tests.factories import ChallengeFactory
from tests.organizations_tests.factories import OrganizationFactory
from tests.reader_studies_tests.factories import ReaderStudyFactory


@pytest.mark.django_db
@pytest.mark.parametrize("reverse", [True, False])
@pytest.mark.parametrize(
    "factory,related_name,perm",
    (
        (AlgorithmFactory, "algorithms", "view_algorithm"),
        (ArchiveFactory, "archives", "view_archive"),
        (ChallengeFactory, "challenges", "view_challenge"),
        (ReaderStudyFactory, "readerstudies", "view_readerstudy"),
    ),
)
def test_related_permissions_assigned(
    client, reverse, factory, related_name, perm
):
    org1, org2 = OrganizationFactory(), OrganizationFactory()

    obj1, obj2, obj3, obj4 = (factory(), factory(), factory(), factory())

    if reverse:
        for obj in [obj1, obj2, obj3, obj4]:
            obj.organizations.add(org1, org2)
        for obj in [obj3, obj4]:
            obj.organizations.remove(org1, org2)
        for obj in [obj1, obj2]:
            obj.organizations.remove(org2)
    else:
        getattr(org1, related_name).add(obj1, obj2, obj3, obj4)
        getattr(org1, related_name).remove(obj3, obj4)

    # We end up with org1 only being related to obj1 and obj2
    expected_perms = {
        obj1: {org1.editors_group: {perm}, org1.members_group: {perm}},
        obj2: {org1.editors_group: {perm}, org1.members_group: {perm}},
    }
    for obj in [obj1, obj2, obj3, obj4]:
        for group in [
            org1.editors_group,
            org1.members_group,
            org2.editors_group,
            org2.members_group,
        ]:
            assert get_groups_with_set_perms(obj).get(
                group
            ) == expected_perms.get(obj, {}).get(group)

    # Test clearing
    if reverse:
        obj1.organizations.clear()
        obj2.organizations.clear()
    else:
        getattr(org1, related_name).clear()

    for obj in [obj1, obj2, obj3, obj4]:
        for group in [
            org1.editors_group,
            org1.members_group,
            org2.editors_group,
            org2.members_group,
        ]:
            assert get_groups_with_set_perms(obj).get(group) is None
