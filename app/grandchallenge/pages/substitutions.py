import re
from re import Match
from typing import Tuple, Union

from django.utils.html import format_html
from django.utils.safestring import SafeString, mark_safe


class Substitution:
    """
    Substitute tags in blocks of text.

    This class allows the replacement of Django like tags with new content,
    without using Django templates. Supports Strings and SafeStrings, and
    substituting 1 argument provided in the tag to the replacement using
    format_html.
    """

    def __init__(
        self,
        *,
        tag_name: str,
        replacement: str,
        markers: Tuple[str, str] = ("{%", "%}"),
        use_arg: bool = False,
    ):
        self._tag_name = tag_name.strip()
        self._replacement = replacement
        self._markers = [re.escape(m) for m in markers]
        self._use_arg = use_arg

        if not re.search(r"\A[a-zA-Z_\-]+\Z", self._tag_name):
            raise ValueError(f"{self._tag_name} is not a valid tag name.")

    @property
    def pattern(self) -> str:
        pattern = rf"{self._markers[0]}\s*{self._tag_name}"
        if self._use_arg:
            pattern += rf"\s+[\'\"]?([a-zA-Z0-9_\-]+)[\'\"]?"
        pattern += rf"\s*{self._markers[1]}"
        return pattern

    def sub(self, s: Union[str, SafeString]) -> Union[str, SafeString]:
        def subrepl(match: Match):
            if self._use_arg:
                return format_html(self._replacement, match.group(1))
            else:
                return self._replacement

        out = re.sub(self.pattern, subrepl, s)

        if isinstance(s, SafeString) and isinstance(
            self._replacement, SafeString
        ):
            out = mark_safe(out)

        return out
