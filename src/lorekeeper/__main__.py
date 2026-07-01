import argparse
import importlib.metadata
import sys

from lorekeeper.infra.logging_setup import configure_logging
from lorekeeper.infra.settings import Settings
from lorekeeper.server import init_service, mcp


def _distribution_version() -> str:
    """Return the installed package version.

    The published distribution is ``lorekeeper-mcp``; keep ``lorekeeper`` as a
    fallback for editable/local environments where metadata may be incomplete.
    """

    for dist_name in ("lorekeeper-mcp", "lorekeeper"):
        try:
            return importlib.metadata.version(dist_name)
        except importlib.metadata.PackageNotFoundError:
            continue
    return "0.0.0"


def _run_mcp_server() -> None:
    settings = Settings()
    configure_logging(log_dir=settings.log_dir)
    init_service(settings)
    mcp.run(transport="stdio")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="lorekeeper",
        description="Personal AI memory MCP server — stores facts and knowledge for AI agents.",
    )
    subparsers = parser.add_subparsers(dest="command")

    setup_parser = subparsers.add_parser("setup", help="Configure AI agents to use Lorekeeper.")
    setup_parser.add_argument(
        "--check",
        action="store_true",
        help="Dry-run: show what would be configured without writing anything.",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {_distribution_version()}",
    )
    args = parser.parse_args()

    if args.command == "setup":
        from lorekeeper.cli.setup import run_setup

        sys.exit(run_setup(dry_run=args.check))

    _run_mcp_server()


if __name__ == "__main__":
    main()
