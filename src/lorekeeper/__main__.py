import argparse

from lorekeeper.config import Settings
from lorekeeper.logging_setup import configure_logging
from lorekeeper.server import init_service, mcp


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="lorekeeper",
        description="Self-improving MCP memory server for AI agents.",
        epilog="Runs until stopped — connect your MCP client to start using it.",
    )
    # No subcommands yet; just parse to handle --help/-h
    parser.parse_args()

    settings = Settings()
    configure_logging(log_dir=settings.log_dir)
    init_service(settings)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
