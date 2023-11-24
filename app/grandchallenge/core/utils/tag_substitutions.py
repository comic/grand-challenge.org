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

    num_args = 0

    def __init__(
        self,
        *,
        tag_name: str,
        replacement: str | Callable,
        markers: tuple[str, str] = ("[", "]"),
    ):
        self.tag_name = tag_name.strip()
        self.replacement = replacement
        self.markers = [re.escape(m) for m in markers]

        if isinstance(self.replacement, Callable):
            self.num_args = self._get_num_positional_args(self.replacement)

        if not re.search(r"\A[a-zA-Z_\-]+\Z", self.tag_name):
            raise ValueError(f"{self.tag_name} is not a valid tag name.")

    @property
    def pattern(self) -> str:
        pattern = rf"{self.markers[0]}\s*{self.tag_name}"
        for _ in range(0, self.num_args):
            pattern += r"\s+[\'\"]?([a-zA-Z0-9_\-]+)[\'\"]?"
        pattern += rf"\s*{self.markers[1]}"
        return pattern

    @staticmethod
    def _get_num_positional_args(func) -> int:
        argspec = inspect.getfullargspec(func)
        if argspec.defaults or argspec.varargs or argspec.kwonlyargs:
            raise NotImplementedError(
                "Only functions with positional arguments are supported for replacement callables"
            )
        count = len(argspec.args)

        if inspect.ismethod(func):  # bound function
            count = count - 1

        return count

    def __call__(self, s: str | SafeString) -> str | SafeString:
        safe_replacements = True

        def subrepl(match: Match):
            result = SafeString()
            if isinstance(self.replacement, Callable):
                result = self.replacement(*match.groups())
            elif isinstance(self.replacement, str):
                result = self.replacement
            nonlocal safe_replacements
            safe_replacements = safe_replacements and isinstance(
                result, SafeString
            )
            return result

        out = re.sub(self.pattern, subrepl, s)

        if isinstance(s, SafeString) and safe_replacements:
            out = mark_safe(out)

        return out
