# copyright 2003-2012 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
# contact http://www.logilab.fr/ -- mailto:contact@logilab.fr
#
# This file is part of logilab-common.
#
# logilab-common is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 2.1 of the License, or (at your option) any
# later version.
#
# logilab-common is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License along
# with logilab-common.  If not, see <http://www.gnu.org/licenses/>.
"""unit tests for logilab.common.deprecation"""

import os
import warnings

from inspect import currentframe, getframeinfo

from logilab.common.testlib import TestCase, unittest_main
from logilab.common.modutils import LazyObject
from logilab.common import deprecation


CURRENT_FILE = os.path.abspath(__file__)


class RawInputTC(TestCase):

    # XXX with 2.6 we could test warnings
    # http://docs.python.org/library/warnings.html#testing-warnings
    # instead we just make sure it does not crash

    def mock_warn(self, *args, **kwargs):
        self.messages.append(str(args[0]))

    def setUp(self):
        self.messages = []
        deprecation.warn = self.mock_warn

    def tearDown(self):
        deprecation.warn = warnings.warn

    def mk_func(self):
        def any_func():
            pass

        return any_func

    def test_class_deprecated(self):
        class AnyClass(object, metaclass=deprecation.class_deprecated):
            pass

        AnyClass()
        self.assertEqual(self.messages, ["[test_deprecation] AnyClass is deprecated"])

    def test_class_renamed(self):
        class AnyClass(object):
            pass

        OldClass = deprecation.class_renamed("OldClass", AnyClass)

        OldClass()
        self.assertEqual(
            self.messages, ["[test_deprecation] OldClass is deprecated, use AnyClass instead"]
        )

    def test_class_renamed_conflict_metaclass(self):
        class SomeMetaClass(type):
            pass

        class AnyClass(metaclass=SomeMetaClass):
            pass

        # make sure the "metaclass conflict: the metaclass of a derived class # must be a
        # (non-strict) subclass of the metaclasses of all its bases" exception won't be raised
        deprecation.class_renamed("OldClass", AnyClass)

    def test_class_moved(self):
        class AnyClass(object):
            pass

        OldClass = deprecation.class_moved(new_class=AnyClass, old_name="OldName")
        OldClass()
        self.assertEqual(
            self.messages,
            [
                "[test_deprecation] class test_deprecation.OldName is now available as "
                "test_deprecation.AnyClass"
            ],
        )

        self.messages = []

        AnyClass = deprecation.class_moved(new_class=AnyClass)

        AnyClass()
        self.assertEqual(
            self.messages,
            [
                "[test_deprecation] class test_deprecation.AnyClass is now available as "
                "test_deprecation.AnyClass"
            ],
        )

    def test_deprecated_func(self):
        any_func = deprecation.callable_deprecated()(self.mk_func())
        any_func()
        any_func = deprecation.callable_deprecated("message")(self.mk_func())
        any_func()
        self.assertEqual(
            self.messages,
            [
                '[test_deprecation] The function "any_func" is deprecated',
                "[test_deprecation] message",
            ],
        )

    def test_deprecated_decorator(self):
        @deprecation.callable_deprecated()
        def any_func():
            pass

        any_func()

        @deprecation.callable_deprecated("message")
        def any_func():
            pass

        any_func()
        self.assertEqual(
            self.messages,
            [
                '[test_deprecation] The function "any_func" is deprecated',
                "[test_deprecation] message",
            ],
        )

    def test_deprecated_decorator_bad_lazyobject(self):
        # this should not raised an ImportationError
        deprecation.deprecated("foobar")(LazyObject("cubes.localperms", "xperm"))

        # with or without giving it a message (because it shouldn't access
        # attributes of the wrapped object before the object is called)
        deprecation.deprecated()(LazyObject("cubes.localperms", "xperm"))

        # all of this is done because of the magical way LazyObject is working
        # and that sometime CW used to use it to do fake import on deprecated
        # modules to raise a warning if they were used but not importing them
        # by default.
        # See: https://forge.extranet.logilab.fr/cubicweb/cubicweb/blob/3.24.0/cubicweb/schemas/__init__.py#L51 # noqa

    def test_lazy_wraps_function_name(self):
        """
        Avoid conflict from lazy_wraps where __name__ isn't correctly set on
        the wrapper from the wrapped and we end up with the name of the wrapper
        instead of the wrapped.

        Like here it would fail if "check_kwargs" is the name of the new
        function instead of new_function_name, this is because the wrapper in
        argument_renamed is called check_kwargs and doesn't transmit the
        __name__ of the wrapped (new_function_name) correctly.
        """

        @deprecation.argument_renamed(old_name="a", new_name="b")
        def new_function_name(b):
            pass

        old_function_name = deprecation.callable_renamed(
            old_name="old_function_name", new_function=new_function_name
        )
        old_function_name(None)

        assert "old_function_name" in self.messages[0]
        assert "new_function_name" in self.messages[0]
        assert "check_kwargs" not in self.messages[0]

    def test_attribute_renamed(self):
        @deprecation.attribute_renamed(old_name="old", new_name="new")
        class SomeClass:
            def __init__(self):
                self.new = 42

        some_class = SomeClass()
        self.assertEqual(some_class.old, some_class.new)
        self.assertEqual(
            self.messages,
            [
                "[test_deprecation] SomeClass.old has been renamed and is deprecated, "
                "use SomeClass.new instead"
            ],
        )

        some_class.old = 43
        self.assertEqual(some_class.old, 43)
        self.assertEqual(some_class.old, some_class.new)

        self.assertTrue(hasattr(some_class, "new"))
        self.assertTrue(hasattr(some_class, "old"))
        del some_class.old
        self.assertFalse(hasattr(some_class, "new"))
        self.assertFalse(hasattr(some_class, "old"))

    def test_argument_renamed(self):
        @deprecation.argument_renamed(old_name="old", new_name="new")
        def some_function(new):
            return new

        self.assertEqual(some_function(new=42), 42)
        self.assertEqual(some_function(old=42), 42)
        self.assertEqual(
            self.messages,
            [
                "[test_deprecation] argument old of callable some_function has been renamed and is "
                "deprecated, use keyword argument new instead"
            ],
        )

        with self.assertRaises(ValueError):
            some_function(new=42, old=42)

    def test_argument_removed(self):
        @deprecation.argument_removed("old")
        def some_function(new):
            return new

        self.assertEqual(some_function(new=42), 42)
        self.assertEqual(some_function(new=10, old=20), 10)
        self.assertEqual(
            self.messages,
            [
                "[test_deprecation] argument old of callable some_function has been removed and is "
                "deprecated"
            ],
        )

    def test_callable_renamed(self):
        def any_func():
            pass

        old_func = deprecation.callable_renamed("old_func", any_func)
        old_func()

        self.assertEqual(
            self.messages,
            [
                "[test_deprecation] old_func has been renamed and is deprecated, "
                "uses any_func instead"
            ],
        )

    def test_callable_moved(self):
        module = "data.deprecation"
        moving_target = deprecation.callable_moved(module, "moving_target")
        moving_target()
        self.assertEqual(
            self.messages,
            [
                "[test_deprecation] object test_deprecation.moving_target has been moved to "
                "data.deprecation.moving_target"
            ],
        )


class StructuredDeprecatedWarningsTest(TestCase):
    def mock_warn(self, *args, **kwargs):
        self.collected_warnings.append(args[0])

    def setUp(self):
        self.collected_warnings = []
        deprecation.warn = self.mock_warn

    def tearDown(self):
        deprecation.warn = warnings.warn

    def mk_func(self):
        def any_func():
            pass

        return any_func

    def test_class_deprecated(self):
        class AnyClass(metaclass=deprecation.class_deprecated):
            pass

        AnyClass()
        self.assertEqual(len(self.collected_warnings), 1)
        warning = self.collected_warnings.pop()

        self.assertEqual(warning.operation, deprecation.DeprecationWarningOperation.DEPRECATED)
        self.assertEqual(warning.kind, deprecation.DeprecationWarningKind.CLASS)

    def test_class_renamed(self):
        class AnyClass:
            pass

        OldClass = deprecation.class_renamed("OldClass", AnyClass)

        OldClass()
        self.assertEqual(len(self.collected_warnings), 1)
        warning = self.collected_warnings.pop()

        self.assertEqual(warning.operation, deprecation.DeprecationWarningOperation.RENAMED)
        self.assertEqual(warning.old_name, "OldClass")
        self.assertEqual(warning.new_name, "AnyClass")
        self.assertEqual(warning.kind, deprecation.DeprecationWarningKind.CLASS)

    def test_class_moved(self):
        class AnyClass:
            pass

        OldClass = deprecation.class_moved(new_class=AnyClass, old_name="OldName")
        OldClass()

        self.assertEqual(len(self.collected_warnings), 1)
        warning = self.collected_warnings.pop()

        self.assertEqual(warning.operation, deprecation.DeprecationWarningOperation.MOVED)
        self.assertEqual(warning.old_module, "test_deprecation")
        self.assertEqual(warning.new_module, "test_deprecation")
        self.assertEqual(warning.old_name, "OldName")
        self.assertEqual(warning.new_name, "AnyClass")
        self.assertEqual(warning.kind, deprecation.DeprecationWarningKind.CLASS)

        self.collected_warnings = []

        AnyClass = deprecation.class_moved(new_class=AnyClass)

        AnyClass()

        self.assertEqual(len(self.collected_warnings), 1)
        warning = self.collected_warnings.pop()

        self.assertEqual(warning.operation, deprecation.DeprecationWarningOperation.MOVED)
        self.assertEqual(warning.old_module, "test_deprecation")
        self.assertEqual(warning.new_module, "test_deprecation")
        self.assertEqual(warning.old_name, "AnyClass")
        self.assertEqual(warning.new_name, "AnyClass")
        self.assertEqual(warning.kind, deprecation.DeprecationWarningKind.CLASS)

    def test_deprecated_func(self):
        any_func = deprecation.callable_deprecated()(self.mk_func())
        any_func()

        self.assertEqual(len(self.collected_warnings), 1)
        warning = self.collected_warnings.pop()

        self.assertEqual(warning.operation, deprecation.DeprecationWarningOperation.DEPRECATED)
        self.assertEqual(warning.kind, deprecation.DeprecationWarningKind.CALLABLE)

        any_func = deprecation.callable_deprecated("message")(self.mk_func())
        any_func()

        self.assertEqual(len(self.collected_warnings), 1)
        warning = self.collected_warnings.pop()

        self.assertEqual(warning.operation, deprecation.DeprecationWarningOperation.DEPRECATED)
        self.assertEqual(warning.kind, deprecation.DeprecationWarningKind.CALLABLE)

    def test_deprecated_decorator(self):
        @deprecation.callable_deprecated()
        def any_func():
            pass

        any_func()

        self.assertEqual(len(self.collected_warnings), 1)
        warning = self.collected_warnings.pop()

        self.assertEqual(warning.operation, deprecation.DeprecationWarningOperation.DEPRECATED)
        self.assertEqual(warning.kind, deprecation.DeprecationWarningKind.CALLABLE)

        @deprecation.callable_deprecated("message")
        def any_func():
            pass

        any_func()

        self.assertEqual(len(self.collected_warnings), 1)
        warning = self.collected_warnings.pop()

        self.assertEqual(warning.operation, deprecation.DeprecationWarningOperation.DEPRECATED)
        self.assertEqual(warning.kind, deprecation.DeprecationWarningKind.CALLABLE)

    def test_attribute_renamed(self):
        @deprecation.attribute_renamed(old_name="old", new_name="new")
        class SomeClass:
            def __init__(self):
                self.new = 42

        some_class = SomeClass()

        some_class.old == some_class.new  # trigger warning

        self.assertEqual(len(self.collected_warnings), 1)
        warning = self.collected_warnings.pop()

        self.assertEqual(warning.operation, deprecation.DeprecationWarningOperation.RENAMED)
        self.assertEqual(warning.old_name, "old")
        self.assertEqual(warning.new_name, "new")
        self.assertEqual(warning.kind, deprecation.DeprecationWarningKind.ATTRIBUTE)

        some_class.old = 43

        self.assertEqual(len(self.collected_warnings), 1)
        warning = self.collected_warnings.pop()

        self.assertEqual(warning.operation, deprecation.DeprecationWarningOperation.RENAMED)
        self.assertEqual(warning.old_name, "old")
        self.assertEqual(warning.new_name, "new")
        self.assertEqual(warning.kind, deprecation.DeprecationWarningKind.ATTRIBUTE)

        del some_class.old

        self.assertEqual(len(self.collected_warnings), 1)
        warning = self.collected_warnings.pop()

        self.assertEqual(warning.operation, deprecation.DeprecationWarningOperation.RENAMED)
        self.assertEqual(warning.old_name, "old")
        self.assertEqual(warning.new_name, "new")
        self.assertEqual(warning.kind, deprecation.DeprecationWarningKind.ATTRIBUTE)

    def test_argument_renamed(self):
        @deprecation.argument_renamed(old_name="old", new_name="new")
        def some_function(new):
            return new

        some_function(old=42)

        self.assertEqual(len(self.collected_warnings), 1)
        warning = self.collected_warnings.pop()

        self.assertEqual(warning.operation, deprecation.DeprecationWarningOperation.RENAMED)
        self.assertEqual(warning.old_name, "old")
        self.assertEqual(warning.new_name, "new")
        self.assertEqual(warning.kind, deprecation.DeprecationWarningKind.ARGUMENT)

    def test_argument_removed(self):
        @deprecation.argument_removed("old")
        def some_function(new):
            return new

        some_function(new=10, old=20)

        self.assertEqual(len(self.collected_warnings), 1)
        warning = self.collected_warnings.pop()

        self.assertEqual(warning.operation, deprecation.DeprecationWarningOperation.REMOVED)
        self.assertEqual(warning.name, "old")
        self.assertEqual(warning.kind, deprecation.DeprecationWarningKind.ARGUMENT)

    def test_callable_renamed(self):
        def any_func():
            pass

        old_func = deprecation.callable_renamed("old_func", any_func)
        old_func()

        self.assertEqual(len(self.collected_warnings), 1)
        warning = self.collected_warnings.pop()

        self.assertEqual(warning.operation, deprecation.DeprecationWarningOperation.RENAMED)
        self.assertEqual(warning.old_name, "old_func")
        self.assertEqual(warning.new_name, "any_func")
        self.assertEqual(warning.kind, deprecation.DeprecationWarningKind.CALLABLE)

    def test_callable_moved(self):
        module = "data.deprecation"
        moving_target = deprecation.callable_moved(module, "moving_target")
        moving_target()

        self.assertEqual(len(self.collected_warnings), 1)
        warning = self.collected_warnings.pop()

        self.assertEqual(warning.operation, deprecation.DeprecationWarningOperation.MOVED)
        self.assertEqual(warning.old_module, "test_deprecation")
        self.assertEqual(warning.new_module, "data.deprecation")
        self.assertEqual(warning.old_name, "moving_target")
        self.assertEqual(warning.new_name, "moving_target")
        self.assertEqual(warning.kind, deprecation.DeprecationWarningKind.CALLABLE)


class DeprecatedWarningsTracebackLocationTest(TestCase):
    def setUp(self):
        self.catch_warnings = warnings.catch_warnings(record=True)
        self.collected_warnings = self.catch_warnings.__enter__()

    def tearDown(self):
        self.catch_warnings.__exit__()

    def mk_func(self):
        def any_func():
            pass

        return any_func

    def test_class_deprecated(self):
        class AnyClass(metaclass=deprecation.class_deprecated):
            pass

        AnyClass()
        warning_line = getframeinfo(currentframe()).lineno - 1

        self.assertEqual(len(self.collected_warnings), 1)
        warning = self.collected_warnings.pop()

        location = f"{CURRENT_FILE}:{warning_line}"
        self.assertEqual(f"{warning.filename}:{warning.lineno}", location)

    def test_class_renamed(self):
        class AnyClass:
            pass

        OldClass = deprecation.class_renamed("OldClass", AnyClass)

        OldClass()
        warning_line = getframeinfo(currentframe()).lineno - 1

        self.assertEqual(len(self.collected_warnings), 1)
        warning = self.collected_warnings.pop()

        location = f"{CURRENT_FILE}:{warning_line}"
        self.assertEqual(f"{warning.filename}:{warning.lineno}", location)

    def test_class_moved(self):
        class AnyClass:
            pass

        OldClass = deprecation.class_moved(new_class=AnyClass, old_name="OldName")
        OldClass()
        warning_line = getframeinfo(currentframe()).lineno - 1

        self.assertEqual(len(self.collected_warnings), 1)
        warning = self.collected_warnings.pop()

        location = f"{CURRENT_FILE}:{warning_line}"
        self.assertEqual(f"{warning.filename}:{warning.lineno}", location)

        AnyClass = deprecation.class_moved(new_class=AnyClass)

        AnyClass()
        warning_line = getframeinfo(currentframe()).lineno - 1

        self.assertEqual(len(self.collected_warnings), 1)
        warning = self.collected_warnings.pop()

        location = f"{CURRENT_FILE}:{warning_line}"
        self.assertEqual(f"{warning.filename}:{warning.lineno}", location)

    def test_deprecated_func(self):
        any_func = deprecation.callable_deprecated()(self.mk_func())
        any_func()
        warning_line = getframeinfo(currentframe()).lineno - 1

        self.assertEqual(len(self.collected_warnings), 1)
        warning = self.collected_warnings.pop()

        location = f"{CURRENT_FILE}:{warning_line}"
        self.assertEqual(f"{warning.filename}:{warning.lineno}", location)

        any_func = deprecation.callable_deprecated("message")(self.mk_func())
        any_func()
        warning_line = getframeinfo(currentframe()).lineno - 1

        self.assertEqual(len(self.collected_warnings), 1)
        warning = self.collected_warnings.pop()

        location = f"{CURRENT_FILE}:{warning_line}"
        self.assertEqual(f"{warning.filename}:{warning.lineno}", location)

    def test_deprecated_decorator(self):
        @deprecation.callable_deprecated()
        def any_func():
            pass

        any_func()
        warning_line = getframeinfo(currentframe()).lineno - 1

        self.assertEqual(len(self.collected_warnings), 1)
        warning = self.collected_warnings.pop()

        location = f"{CURRENT_FILE}:{warning_line}"
        self.assertEqual(f"{warning.filename}:{warning.lineno}", location)

        @deprecation.callable_deprecated("message")
        def any_func():
            pass

        any_func()
        warning_line = getframeinfo(currentframe()).lineno - 1

        self.assertEqual(len(self.collected_warnings), 1)
        warning = self.collected_warnings.pop()

        location = f"{CURRENT_FILE}:{warning_line}"
        self.assertEqual(f"{warning.filename}:{warning.lineno}", location)

    def test_attribute_renamed(self):
        @deprecation.attribute_renamed(old_name="old", new_name="new")
        class SomeClass:
            def __init__(self):
                self.new = 42

        some_class = SomeClass()

        some_class.old == some_class.new  # trigger warning
        warning_line = getframeinfo(currentframe()).lineno - 1

        self.assertEqual(len(self.collected_warnings), 1)
        warning = self.collected_warnings.pop()

        location = f"{CURRENT_FILE}:{warning_line}"
        self.assertEqual(f"{warning.filename}:{warning.lineno}", location)

        some_class.old = 43
        warning_line = getframeinfo(currentframe()).lineno - 1

        self.assertEqual(len(self.collected_warnings), 1)
        warning = self.collected_warnings.pop()

        location = f"{CURRENT_FILE}:{warning_line}"
        self.assertEqual(f"{warning.filename}:{warning.lineno}", location)

        del some_class.old
        warning_line = getframeinfo(currentframe()).lineno - 1

        self.assertEqual(len(self.collected_warnings), 1)
        warning = self.collected_warnings.pop()

        location = f"{CURRENT_FILE}:{warning_line}"
        self.assertEqual(f"{warning.filename}:{warning.lineno}", location)

    def test_argument_renamed(self):
        @deprecation.argument_renamed(old_name="old", new_name="new")
        def some_function(new):
            return new

        some_function(old=42)
        warning_line = getframeinfo(currentframe()).lineno - 1

        self.assertEqual(len(self.collected_warnings), 1)
        warning = self.collected_warnings.pop()

        location = f"{CURRENT_FILE}:{warning_line}"
        self.assertEqual(f"{warning.filename}:{warning.lineno}", location)

    def test_argument_removed(self):
        @deprecation.argument_removed("old")
        def some_function(new):
            return new

        some_function(new=10, old=20)
        warning_line = getframeinfo(currentframe()).lineno - 1

        self.assertEqual(len(self.collected_warnings), 1)
        warning = self.collected_warnings.pop()

        location = f"{CURRENT_FILE}:{warning_line}"
        self.assertEqual(f"{warning.filename}:{warning.lineno}", location)

    def test_callable_renamed(self):
        def any_func():
            pass

        old_func = deprecation.callable_renamed("old_func", any_func)
        old_func()
        warning_line = getframeinfo(currentframe()).lineno - 1

        self.assertEqual(len(self.collected_warnings), 1)
        warning = self.collected_warnings.pop()

        location = f"{CURRENT_FILE}:{warning_line}"
        self.assertEqual(f"{warning.filename}:{warning.lineno}", location)

    def test_callable_moved(self):
        module = "data.deprecation"
        moving_target = deprecation.callable_moved(module, "moving_target")
        moving_target()
        warning_line = getframeinfo(currentframe()).lineno - 1

        self.assertEqual(len(self.collected_warnings), 1)
        warning = self.collected_warnings.pop()

        location = f"{CURRENT_FILE}:{warning_line}"
        self.assertEqual(f"{warning.filename}:{warning.lineno}", location)


if __name__ == "__main__":
    unittest_main()
