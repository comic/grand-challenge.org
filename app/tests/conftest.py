import pytest
from django.core import management
@pytest.fixture(autouse=True)
def enable_db_access(db):
    management.call_command('init_db_data')