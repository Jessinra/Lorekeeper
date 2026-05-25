import argparse
import os
from pathlib import Path
from typing import Any

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description="Lorekeeper Dashboard")
    parser.add_argument(
        "--data-dir",
        type=str,
        default=None,
        help="Memory data directory (default: $LORE_DATA_DIR or ~/.lorekeeper)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("LORE_DASH_PORT", "7777")),
        help="HTTP port (default: 7777, or $LORE_DASH_PORT)",
    )
    args = parser.parse_args()

    port = args.port
    reload = os.environ.get("LORE_DASH_RELOAD", "1").lower() not in ("0", "false", "no")

    # --data-dir sets LORE_DATA_DIR so Settings() picks it up in both
    # reload and no-reload modes (uvicorn reload spawns a child process).
    if args.data_dir:
        os.environ["LORE_DATA_DIR"] = str(Path(args.data_dir).resolve())

    app_ref = "lorekeeper.dashboard.app:app" if reload else _import_app()
    uvicorn.run(app_ref, host="127.0.0.1", port=port, reload=reload)


def _import_app() -> Any:
    from lorekeeper.dashboard.app import app

    return app
