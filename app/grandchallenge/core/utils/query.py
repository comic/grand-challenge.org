def index(queryset, obj):
    """
    Give the zero-based index of first occurrence of object in queryset.
    Return -1 if not found
    """
    for index, item in enumerate(queryset):
        if item == obj:
            return index

    return -1
