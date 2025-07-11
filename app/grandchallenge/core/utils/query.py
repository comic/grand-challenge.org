from django.db import connection


def index(queryset, obj):
    """
    Give the zero-based index of first occurrence of object in queryset.
    Return -1 if not found
    """
    for index, item in enumerate(queryset):
        if item == obj:
            return index

    return -1


def set_seed(seed):
    # Note: this only works for postgres, if we ever switch dbs, this
    # may need changing.
    cursor = connection.cursor()
    cursor.execute(f"SELECT setseed({seed});")
    cursor.close()
