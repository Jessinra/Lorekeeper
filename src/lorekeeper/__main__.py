from lorekeeper.logging_setup import configure_logging
from lorekeeper.server import init_service, mcp


def main() -> None:
    configure_logging()
    init_service()
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
