import os
from typing import Any

import uvicorn


def main() -> None:
    port = int(os.environ.get("LORE_DASH_PORT", "7777"))
    reload = os.environ.get("LORE_DASH_RELOAD", "1").lower() not in ("0", "false", "no")
    # Pass app as import string when reload=True — uvicorn requires it for the child process
    app_ref = "lorekeeper.dashboard.app:app" if reload else _import_app()
    uvicorn.run(app_ref, host="127.0.0.1", port=port, reload=reload)


def _import_app() -> Any:
    from lorekeeper.dashboard.app import app
    return app
