import json

from django.conf import settings
from django.forms import Media


def get_webpack_bundles(bundle_name):
    """Get both JS and CSS bundles for a webpack bundle"""
    stats_file = settings.WEBPACK_LOADER["DEFAULT"]["STATS_FILE"]
    with open(stats_file) as f:
        stats = json.load(f)

    chunks = stats.get("chunks", {})
    assets = stats.get("assets", {})
    if bundle_name not in chunks:
        raise ValueError(f"Bundle {bundle_name!r} not found in webpack stats.")
    files = chunks[bundle_name]
    css_files = []
    js_files = []

    static_url_prefix = f"{settings.STATIC_URL}vendored/"

    for file in files:
        file_info = assets[file]
        if file_info["name"].endswith(".css"):
            css_files.append(static_url_prefix + file_info["path"])
        elif file_info["name"].endswith(".js"):
            js_files.append(static_url_prefix + file_info["path"])

    return {"css": css_files, "js": js_files}


class WebpackWidgetMixin:
    """Mixin to add webpack bundle support to Django widgets"""

    webpack_bundles = None  # List of bundle names

    @property
    def media(self):
        # Get base media from parent classes
        base_media = super().media if hasattr(super(), "media") else Media()

        # Add webpack bundles if specified
        if self.webpack_bundles:
            css_files = []
            js_files = []

            for bundle_name in self.webpack_bundles:
                bundles = get_webpack_bundles(bundle_name)
                css_files.extend(bundles["css"])
                js_files.extend(bundles["js"])

            webpack_media = Media(
                css={"all": css_files} if css_files else {},
                js=js_files if js_files else [],
            )
            return base_media + webpack_media

        return base_media
