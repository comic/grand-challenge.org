import re
from re import Match
from typing import Tuple, Union

from django.utils.html import format_html
from django.utils.safestring import SafeString, mark_safe


class Substitution:
    def __init__(
        self,
        *,
        tag_name: str,
        content: str,
        markers: Tuple[str, str] = ("{%", "%}"),
        use_args: bool = False,
    ):

        self._tag_name = tag_name.strip()

        self._replacement = content.strip()
        if isinstance(content, SafeString):
            self._replacement = mark_safe(self._replacement)

        self._markers = [re.escape(m) for m in markers]
        if not re.search(r"\A[a-zA-Z_\-]+\Z", self._tag_name):
            raise ValueError(f"{self._tag_name} is not a valid name.")

        self._use_args = use_args

    @property
    def regex(self) -> str:
        pattern = rf"{self._markers[0]}\s*{self._tag_name}"
        if self._use_args:
            pattern += rf"\s+[\'\"]?([a-zA-Z0-9_\-]+)[\'\"]?"
        pattern += rf"\s*{self._markers[1]}"
        return pattern

    def replace(self, s: Union[str, SafeString]) -> Union[str, SafeString]:
        def subrepl(match: Match):
            if self._use_args:
                return format_html(self._replacement, match.group(1))
            else:
                return self._replacement

        out = re.sub(self.regex, subrepl, s)

        if isinstance(s, SafeString) and isinstance(
            self._replacement, SafeString
        ):
            out = mark_safe(out)

        return out
