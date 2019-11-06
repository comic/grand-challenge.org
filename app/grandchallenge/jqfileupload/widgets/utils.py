class IntervalMap:
    """
    Create a lookup table for contiguous ranges that can be described by a
    single length. It stores a mapping of these ranges to an
    arbitrary object allowing one to encode mappings like:

    ..code-block::

        range(0, 100000)        -> SomeObject()
        range(100000, 100012)   -> AnotherObject()
        range(100012, 200000)   -> AThirdObject()

    in a space efficient manner. The example map above would be constructed as
    follows with an interval map:

    ..code-block::

        im = IntervalMap()
        im.append_interval(100000, SomeObject())
        im.append_interval(12, AnotherObject())
        im.append_interval(99988, AThirdObject())

    The total length of the entire range can be queried using the `len()`
    operator, but one should prefer the `len` property since the len-operator
    will fail for very large arrays (> sys.maxint):

    ..code-block::

        len(im)
        -> 200000

    Lookups can be done with the usual `[]` operator:

    ..code-block::

        im[5000]
        -> SomeObject
        im[12300]
        -> AThridObject
        im[1242342134]
        -> raises IndexError

    Note that negative indexes are not allowed.
    """

    def __init__(self):
        self.__endpoints = []

    def append_interval(self, length, label):
        self.__endpoints.append((self.len + length, label))
        self.__endpoints.sort()

    def __find_endpoint_index(self, i):
        def find(start, end):
            # use nested intervals to find correct label
            if start == end:
                return start

            else:
                mid = (start + end) // 2
                if self.__endpoints[mid][0] > i:
                    return find(start, mid)

                else:
                    return find(mid + 1, end)

        if i < 0 or i >= self.len:
            return None

        else:
            return find(0, len(self.__endpoints))

    def get_offset(self, i):
        """
        Tries to find the start point of an interval that was added through
        append_interval that is indexed by i.

        Arguments
        ---------
        i: int
            The index of an item for which to find the start-point of its
            interval.

        Returns
        -------
        Integer value describing the start point of the interval that i falls
        into.

        Raises
        ------
        IndexError:
            In case that i does not fall in any interval/
        """
        if not isinstance(i, int):
            raise TypeError("index must be int")

        endpoint_index = self.__find_endpoint_index(i)
        if endpoint_index is None:
            raise IndexError()

        elif endpoint_index == 0:
            return 0

        else:
            return self.__endpoints[endpoint_index - 1][0]

    def __getitem__(self, i):
        if not isinstance(i, int):
            raise TypeError("index must be int")

        if i < 0:
            raise IndexError()

        endpoint_index = self.__find_endpoint_index(i)
        if endpoint_index is None:
            raise IndexError()

        else:
            return self.__endpoints[endpoint_index][1]

    @property
    def len(self):
        return self.__endpoints[-1][0] if self.__endpoints else 0

    def __len__(self):
        return self.len
