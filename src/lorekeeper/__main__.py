import argparse
import importlib.metadata

from lorekeeper.config import Settings
from lorekeeper.logging_setup import configure_logging
from lorekeeper.server import init_service, mcp


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="lorekeeper",
        description="Personal AI memory MCP server — stores facts and knowledge for AI agents.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {importlib.metadata.version('lorekeeper')}",
    )
    parser.parse_args()

    settings = Settings()
    configure_logging(log_dir=settings.log_dir)
    init_service(settings)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
