from rest_framework.pagination import LimitOffsetPagination


class MaxLimit1000OffsetPagination(LimitOffsetPagination):
    max_limit = 1000
