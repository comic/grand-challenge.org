import inspect
import re
from collections.abc import Callable
from re import Match

from django.utils.safestring import SafeString, mark_safe


class TagSubstitution:
    """
    Substitutes tags in blocks of text. This class allows the replacement of
    de-marked tags with new content. Supports Strings and SafeStrings.

    Parameters
    ----------
    tag_name
        Name of the tag
    replacement
        A callable that gets called with the tag arguments as positional arguments.
        Or a string that is set in place of the tag.
    markers
        Markers used to identify the tag in the block of texts

    Returns
    -------
    A String or SafeString dependent on inputs

    Examples
    --------
    >>> TagSubstitution("foo", "hello")("[ foo ] world")
    >>> "Hello world"

    >>> TagSubstitution("sayHi", lambda n: f"Hello {n}, greetings!")("[ sayHi Fred ]")
    >>> "Hello Fred, greetings!"
    """

    def __init__(
        self,
        *,
        tag_name: str,
        replacement: str | Callable,
    ):
        self.tag_name = tag_name.strip()
        self.replacement = replacement

        self.num_args = self._get_num_positional_args(self.replacement)

        if not re.search(r"\A[a-zA-Z_\-]+\Z", self.tag_name):
            raise ValueError(f"{self.tag_name} is not a valid tag name.")

    @property
    def pattern(self) -> str:
        var_match = r"\s+([a-zA-Z0-9_\-]+)"
        return rf"\[\s*{self.tag_name}{var_match*self.num_args}\s*\]"

    @staticmethod
    def _get_num_positional_args(func) -> int:
        if not isinstance(func, Callable):
            return 0

        argspec = inspect.getfullargspec(func)
        if argspec.defaults or argspec.varargs or argspec.kwonlyargs:
            raise NotImplementedError(
                "Only functions with positional arguments are currently supported for replacement callables"
            )
        count = len(argspec.args)

        if inspect.ismethod(func):  # bound function
            count = count - 1

        return count

    def __call__(self, s: str | SafeString) -> str | SafeString:
        input_and_replacement_safe = isinstance(s, SafeString)

        def subrepl(match: Match):
            if isinstance(self.replacement, Callable):
                result = self.replacement(*match.groups())
            else:
                result = self.replacement

            nonlocal input_and_replacement_safe
            input_and_replacement_safe |= isinstance(result, SafeString)

            return result

        out = re.sub(self.pattern, subrepl, s)

        if input_and_replacement_safe:
            out = mark_safe(out)

        return out
