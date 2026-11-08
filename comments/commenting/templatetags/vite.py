import json

from django import template
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.templatetags.static import static
from django.utils.html import format_html, format_html_join

register = template.Library()

ENTRY = "src/main.js"
DIST_STATIC_PREFIX = "commenting/dist/"


def _load_manifest() -> dict:
    manifest_path = settings.VITE_DIST_DIR / ".vite" / "manifest.json"
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ImproperlyConfigured(
            f"Vite manifest not found at {manifest_path}. "
            "Run `npm run build` in frontend/."
        ) from error


@register.simple_tag
def vite_assets():
    dev_server = settings.VITE_DEV_SERVER_URL.rstrip("/")
    if dev_server:
        return format_html(
            '<script type="module" src="{}/@vite/client"></script>\n'
            '<script type="module" src="{}/{}"></script>',
            dev_server,
            dev_server,
            ENTRY,
        )

    entry = _load_manifest()[ENTRY]
    styles = format_html_join(
        "\n",
        '<link rel="stylesheet" href="{}">',
        ((static(DIST_STATIC_PREFIX + css),) for css in entry.get("css", [])),
    )
    script = format_html(
        '<script type="module" src="{}"></script>',
        static(DIST_STATIC_PREFIX + entry["file"]),
    )
    return format_html("{}\n{}", styles, script)
