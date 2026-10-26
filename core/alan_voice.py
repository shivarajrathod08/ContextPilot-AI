"""Optional Alan AI voice-agent embed for the Streamlit UI.

Alan AI provides no Python SDK. The supported integration is the JavaScript Web
SDK (`@alan-ai/alan-sdk-web`, also distributed as `alan_lib.min.js`), loaded in
the browser and rendered here through Streamlit's HTML component.

The embed is intentionally inert until `ALAN_PROJECT_KEY` is configured, and it
depends on a matching dialog script in Alan AI Studio. That script must send a
``prefillTask`` command, for example:

    play({ command: "prefillTask", task: "Add pagination to the products API" })

Voice results come back to Python through the ``?task=`` query parameter, which
`app.py` reads with ``st.query_params``.
"""

import json
import os
import re
from typing import Optional

ALAN_SDK_URL = "https://studio.alan.app/web/lib/alan_lib.min.js"
ALAN_HOST = "v1.alan.app"

# Project keys are public client identifiers, but still constrain the value so a
# malformed key can never inject markup or JavaScript into the page.
_PROJECT_KEY_PATTERN = re.compile(r"[A-Za-z0-9_-]{10,200}")


def get_project_key(custom_key: Optional[str] = None) -> str:
    """Returns the Alan AI project key from the argument or environment."""
    key = custom_key if custom_key is not None else os.getenv("ALAN_PROJECT_KEY", "")
    return (key or "").strip()


def is_configured(custom_key: Optional[str] = None) -> bool:
    """Reports whether a syntactically valid project key is available."""
    key = get_project_key(custom_key)
    return bool(_PROJECT_KEY_PATTERN.fullmatch(key))


def build_embed_html(custom_key: Optional[str] = None) -> str:
    """Builds the Alan AI button embed, or an empty string when unconfigured.

    Raises:
        ValueError: If a project key is set but is not a valid key format.
    """
    key = get_project_key(custom_key)
    if not key:
        return ""
    if not _PROJECT_KEY_PATTERN.fullmatch(key):
        raise ValueError(
            "ALAN_PROJECT_KEY is not a valid Alan AI project key. "
            "Copy the key from your Alan AI Studio project settings."
        )

    key_literal = json.dumps(key)
    sdk_literal = json.dumps(ALAN_SDK_URL)
    host_literal = json.dumps(ALAN_HOST)

    return f"""
<div id="alan-ai-voice-root"></div>
<script src={sdk_literal}></script>
<script>
(function () {{
  if (typeof alanBtn !== "function") {{
    return;
  }}
  alanBtn({{
    key: {key_literal},
    host: {host_literal},
    onCommand: function (command) {{
      if (!command || command.command !== "prefillTask" || !command.task) {{
        return;
      }}
      try {{
        var url = new URL(window.parent.location.href);
        url.searchParams.set("task", command.task);
        window.parent.location.href = url.toString();
      }} catch (err) {{
        window.open("?task=" + encodeURIComponent(command.task), "_top");
      }}
    }}
  }});
}})();
</script>
"""