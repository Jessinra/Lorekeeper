import argparse
import sys

from lorekeeper.config import Settings
from lorekeeper.logging_setup import configure_logging
from lorekeeper.server import init_service, mcp


def _run_mcp_server() -> None:
    settings = Settings()
    configure_logging(log_dir=settings.log_dir)
    init_service(settings)
    mcp.run(transport="stdio")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="lorekeeper",
        description="Self-improving MCP memory server for AI agents.",
        epilog="Run without arguments to start the MCP server.",
    )
    sub = parser.add_subparsers(dest="command")

    # setup subcommand
    setup_p = sub.add_parser("setup", help="Configure AI agents to use Lorekeeper.")
    setup_p.add_argument(
        "--check",
        action="store_true",
        help="Dry-run: show what would be configured without writing anything.",
    )

    args = parser.parse_args()

    if args.command == "setup":
        from lorekeeper.cli.setup import run_setup

        sys.exit(run_setup(dry_run=args.check))
    else:
        # Default (no subcommand): run MCP server — preserves backward compat
        _run_mcp_server()


if __name__ == "__main__":
    main()
