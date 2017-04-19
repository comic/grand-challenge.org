from django.db.models.signals import post_init
from six import iteritems

def track_data(*fields):
    # decorator posted by Riya Jose in http://computer3technology.blogspot.nl/2013/02/tracking-changes-to-fields-in-django.html
    # https://plus.google.com/104750802944871860103/posts
    """
    Tracks property changes on a model instance.

    The changed list of properties is refreshed on model initialization
    and save.

    >>> @track_data('name')
    >>> class Post(models.Model):
    >>> name = models.CharField(...)
    >>>
    >>> @classmethod
    >>> def post_save(cls, sender, instance, created, **kwargs):
    >>> if instance.has_changed('name'):
    >>> print("Hooray!")
    """

    UNSAVED = dict()

    def _store(self):
        "Updates a local copy of attributes values"
        if self.id:
            self.__data = dict((f, getattr(self, f)) for f in fields)
        else:
            self.__data = UNSAVED

    def inner(cls):
        # contains a local copy of the previous values of attributes
        cls.__data = {}

        def has_changed(self, field):
            "Returns ``True`` if ``field`` has changed since initialization."
            if self.__data is UNSAVED:
                return False
            return self.__data.get(field) != getattr(self, field)
        cls.has_changed = has_changed

        def old_value(self, field):
            "Returns the previous value of ``field``"
            return self.__data.get(field)
        cls.old_value = old_value

        def whats_changed(self):
            "Returns a list of changed attributes."
            changed = {}
            if self.__data is UNSAVED:
                return changed
            for k, v in iteritems(self.__data):
                if v != getattr(self, k):
                    changed[k] = v
            return changed
        cls.whats_changed = whats_changed

        # Ensure we are updating local attributes on model init
        def _post_init(sender, instance, **kwargs):
            _store(instance)
        post_init.connect(_post_init, sender=cls, weak=False)

        # Ensure we are updating local attributes on model save
        def save(self, *args, **kwargs):
            save._original(self, *args, **kwargs)
            _store(self)
        save._original = cls.save
        cls.save = save
        return cls
    return inner
