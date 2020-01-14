import re
from typing import Tuple, Union

from django.utils.safestring import SafeString, mark_safe


class Substitution:
    def __init__(
        self,
        *,
        tag_name: str,
        content: str,
        markers: Tuple[str, str] = ("{%", "%}"),
    ):

        self._tag_name = tag_name.strip()

        self._replacement = content.strip()
        if isinstance(content, SafeString):
            self._replacement = mark_safe(self._replacement)

        self._markers = [re.escape(m) for m in markers]
        if not re.search(r"\A[a-zA-Z_\-]+\Z", self._tag_name):
            raise ValueError(f"{self._tag_name} is not a valid name.")

    @property
    def regex(self) -> str:
        return rf"{self._markers[0]}\s*{self._tag_name}\s*{self._markers[1]}"

    def replace(self, s: Union[str, SafeString]) -> Union[str, SafeString]:
        out = re.sub(self.regex, self._replacement, s)
        if isinstance(s, SafeString) and isinstance(
            self._replacement, SafeString
        ):
            out = mark_safe(out)
        return out
