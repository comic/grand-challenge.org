import sys
from functools import wraps

# Code by Gary Bernhardt, taken from https://github.com/garybernhardt/dingus
# Needed this code to do reliable loading of initial data using fixtures in
# south. See http://stackoverflow.com/questions/5472925/django-loading-data-from-fixture-after-backward-migration-loaddata-is-using-mo/5906258#5906258


def DingusTestCase(object_under_test, exclude=None):
    if isinstance(exclude, basestring):
        raise ValueError("Strings not allowed for exclude. " +
                         "Use a list: exclude=['identifier']")
    exclude = [] if exclude is None else exclude

    def get_names_under_test():
        module = sys.modules[object_under_test.__module__]
        for name, value in module.__dict__.iteritems():
            if value is object_under_test or name in exclude:
                yield name

    class TestCase(object):
        def setup(self):
            module_name = object_under_test.__module__
            self._dingus_module = sys.modules[module_name]
            self._dingus_replace_module_globals(self._dingus_module)

        def teardown(self):
            self._dingus_restore_module(self._dingus_module)

        def _dingus_replace_module_globals(self, module):
            old_module_dict = module.__dict__.copy()
            module_keys = set(module.__dict__.iterkeys())

            dunders = set(k for k in module_keys
                           if k.startswith('__') and k.endswith('__'))
            replaced_keys = (module_keys - dunders - set(names_under_test))
            for key in replaced_keys:
                module.__dict__[key] = Dingus()
            module.__dict__['__dingused_dict__'] = old_module_dict

        def _dingus_restore_module(self, module):
            old_module_dict = module.__dict__['__dingused_dict__']
            module.__dict__.clear()
            module.__dict__.update(old_module_dict)

    names_under_test = list(get_names_under_test())
    TestCase.__name__ = '%s_DingusTestCase' % '_'.join(names_under_test)
    return TestCase


# These sentinels are used for argument defaults because the user might want
# to pass in None, which is different in some cases than passing nothing.
class NoReturnValue(object):
    pass
class NoArgument(object):
    pass


def patch(object_path, new_object=NoArgument):
    module_name, attribute_name = object_path.rsplit('.', 1)
    return _Patcher(module_name, attribute_name, new_object)


class _Patcher:
    def __init__(self, module_name, attribute_name, new_object):
        self.module_name = module_name
        self.attribute_name = attribute_name
        self.module = _importer(self.module_name)
        if new_object is NoArgument:
            full_name = '%s.%s' % (module_name, attribute_name)
            self.new_object = Dingus(full_name)
        else:
            self.new_object = new_object

    def __call__(self, fn):
        @wraps(fn)
        def new_fn(*args, **kwargs):
            self.patch_object()
            try:
                return fn(*args, **kwargs)
            finally:
                self.restore_object()
        return new_fn

    def __enter__(self):
        self.patch_object()

    def __exit__(self, exc_type, exc_value, traceback):
        self.restore_object()

    def patch_object(self):
        self.original_object = getattr(self.module, self.attribute_name)
        setattr(self.module, self.attribute_name, self.new_object)

    def restore_object(self):
        setattr(self.module, self.attribute_name, self.original_object)


def isolate(object_path):
    def decorator(fn):
        module_name, object_name = object_path.rsplit('.', 1)
        module = sys.modules[module_name]
        neighbors = set(dir(module)) - set([object_name])
        for neighbor in neighbors:
            neighbor_path = '%s.%s' % (module_name, neighbor)
            fn = patch(neighbor_path)(fn)
        return fn
    return decorator


def _importer(target):
    components = target.split('.')
    import_path = components.pop(0)
    thing = __import__(import_path)

    for comp in components:
        import_path += ".%s" % comp
        thing = _dot_lookup(thing, comp, import_path)
    return thing


def _dot_lookup(thing, comp, import_path):
    try:
        return getattr(thing, comp)
    except AttributeError:
        __import__(import_path)
        return getattr(thing, comp)


class DontCare(object):
    pass


class Call(tuple):
    def __new__(cls, name, args, kwargs, return_value):
        return tuple.__new__(cls, (name, args, kwargs, return_value))

    def __init__(self, *args):
        self.name = self[0]
        self.args = self[1]
        self.kwargs = self[2]
        self.return_value = self[3]
        
    def __getnewargs__(self):
        return (self.name, self.args, self.kwargs, self.return_value)


class CallList(list):
    @staticmethod
    def _match_args(call, args):
        if not args:
            return True
        elif len(args) != len(call.args):
            return False
        else:
            return all(args[i] in (DontCare, call.args[i])
                       for i in range(len(call.args)))

    @staticmethod
    def _match_kwargs(call, kwargs):
        if not kwargs:
            return True
        elif len(kwargs) != len(call.kwargs):
            return False
        else:
            return all(name in kwargs and kwargs[name] in (DontCare, val)
                       for name, val in call.kwargs.iteritems())

    def one(self):
        if len(self) == 1:
            return self[0]
        else:
            return None

    def once(self):
        return self.one()

    def __call__(self, __name=NoArgument, *args, **kwargs):
        return CallList([call for call in self
                         if (__name is NoArgument or __name == call.name)
                         and self._match_args(call, args)
                         and self._match_kwargs(call, kwargs)])


def returner(return_value):
    return Dingus(return_value=return_value)


class Dingus(object):
    @property
    def __enter__(self):
        return self._existing_or_new_child('__enter__')

    def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
        if exc_type and exc_type not in self.consumed_context_manager_exceptions:
            return False
        else:
            return True

    def __init__(self,
                 dingus_name=None,
                 full_name=None,
                 consumed_context_manager_exceptions=None,
                 **kwargs):
        self._parent = None
        self.reset()
        name = 'dingus_%i' % id(self) if dingus_name is None else dingus_name
        full_name = name if full_name is None else full_name
        self._short_name = name
        self._full_name = full_name
        self.__name__ = name
        self._full_name = full_name
        self.consumed_context_manager_exceptions = (
            consumed_context_manager_exceptions or [])

        for attr_name, attr_value in kwargs.iteritems():
            if attr_name.endswith('__returns'):
                attr_name = attr_name.replace('__returns', '')
                returner = self._create_child(attr_name)
                returner.return_value = attr_value
                setattr(self, attr_name, returner)
            else:
                setattr(self, attr_name, attr_value)

        self._replace_init_method()

    @classmethod
    def many(cls, count):
        return tuple(cls() for _ in range(count))

    def _fake_init(self, *args, **kwargs):
        return self.__getattr__('__init__')(*args, **kwargs)

    def _replace_init_method(self):
        self.__init__ = self._fake_init

    def _create_child(self, name):
        separator = ('' if (name.startswith('()') or name.startswith('['))
                     else '.')
        full_name = self._full_name + separator + name
        child = self.__class__(name, full_name)
        child._parent = self
        return child

    def reset(self):
        self._return_value = NoReturnValue
        self.calls = CallList()
        self._children = {}

    def assert_call(self, *args, **kwargs):
        expected_call = self.calls('()', *args, **kwargs)
        if expected_call:
            return
        recorded_calls = self.calls
        calls_description = "No calls recorded" if not recorded_calls \
                                                else "Recorded calls: %s" % recorded_calls
        message = "Expected a call to: '%s', " % self + \
                  "args: %s, kwargs: %s, " % (args, kwargs) + \
                  "\n" + calls_description

        raise AssertionError(message)

    def _get_return_value(self):
        if self._return_value is NoReturnValue:
            self._return_value = self._create_child('()')
        return self._return_value

    def _set_return_value(self, value):
        self._return_value = value

    return_value = property(_get_return_value, _set_return_value)

    def __call__(self, *args, **kwargs):
        self._log_call('()', args, kwargs, self.return_value)
        if self._parent:
            self._parent._log_call(self._short_name,
                                   args,
                                   kwargs,
                                   self.return_value)

        return self.return_value

    def _log_call(self, name, args, kwargs, return_value):
        self.calls.append(Call(name, args, kwargs, return_value))

    def _should_ignore_attribute(self, name):
        return name in ['__pyobjc_object__', '__getnewargs__']
    
    def __getstate__(self):
        # Python cannot pickle a instancemethod
        # http://bugs.python.org/issue558238
        return [ (attr, value) for attr, value in self.__dict__.items() if attr != "__init__"]
    
    def __setstate__(self, state):
        self.__dict__.update(state)
        self._replace_init_method()

    def _existing_or_new_child(self, child_name, default_value=NoArgument):
        if child_name not in self._children:
            value = (self._create_child(child_name)
                     if default_value is NoArgument
                     else default_value)
            self._children[child_name] = value

        return self._children[child_name]

    def _remove_child_if_exists(self, child_name):
        if child_name in self._children:
            del self._children[child_name]

    def __getattr__(self, name):
        if self._should_ignore_attribute(name):
            raise AttributeError(name)
        return self._existing_or_new_child(name)

    def __delattr__(self, name):
        self._log_call('__delattr__', (name,), {}, None)

    def __getitem__(self, index):
        child_name = '[%s]' % (index,)
        return_value = self._existing_or_new_child(child_name)
        self._log_call('__getitem__', (index,), {}, return_value)
        return return_value

    def __setitem__(self, index, value):
        child_name = '[%s]' % (index,)
        self._log_call('__setitem__', (index, value), {}, None)
        self._remove_child_if_exists(child_name)
        self._existing_or_new_child(child_name, value)

    def _create_infix_operator(name):
        def operator_fn(self, other):
            return_value = self._existing_or_new_child(name)
            self._log_call(name, (other,), {}, return_value)
            return return_value
        operator_fn.__name__ = name
        return operator_fn

    _BASE_OPERATOR_NAMES = ['add', 'and', 'div', 'lshift', 'mod', 'mul', 'or',
                            'pow', 'rshift', 'sub', 'xor']

    def _infix_operator_names(base_operator_names):
        # This function has to have base_operator_names passed in because
        # Python's scoping rules prevent it from seeing the class-level
        # _BASE_OPERATOR_NAMES.

        reverse_operator_names = ['r%s' % name for name in base_operator_names]
        for operator_name in base_operator_names + reverse_operator_names:
            operator_fn_name = '__%s__' % operator_name
            yield operator_fn_name

    # Define each infix operator
    for operator_fn_name in _infix_operator_names(_BASE_OPERATOR_NAMES):
        exec('%s = _create_infix_operator("%s")' % (operator_fn_name,
                                              operator_fn_name))

    def _augmented_operator_names(base_operator_names):
        # Augmented operators are things like +=. They behavior differently
        # than normal infix operators because they return self instead of a
        # new object.

        return ['__i%s__' % operator_name
                for operator_name in base_operator_names]

    def _create_augmented_operator(name):
        def operator_fn(self, other):
            return_value = self
            self._log_call(name, (other,), {}, return_value)
            return return_value
        operator_fn.__name__ = name
        return operator_fn

    # Define each augmenting operator
    for operator_fn_name in _augmented_operator_names(_BASE_OPERATOR_NAMES):
        exec('%s = _create_augmented_operator("%s")' % (operator_fn_name,
                                                        operator_fn_name))

    def __str__(self):
        return '<Dingus %s>' % self._full_name
    __repr__ = __str__

    def __len__(self):
        return 1

    def __iter__(self):
        return iter([self._existing_or_new_child('__iter__')])

    # We don't want to define __deepcopy__ at all. If there isn't one, deepcopy
    # will clone the whole object, which is what we want.
    __deepcopy__ = None


def exception_raiser(exception):
    def raise_exception(*args, **kwargs):
        raise exception
    return raise_exception


def loaddata(orm, fixture_name):
    _get_model = lambda model_identifier: orm[model_identifier]

    with patch('django.core.serializers.python._get_model', _get_model):
        from django.core.management import call_command
        call_command("loaddata", fixture_name)