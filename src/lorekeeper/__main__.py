from lorekeeper.config import Settings
from lorekeeper.logging_setup import configure_logging
from lorekeeper.server import init_service, mcp


def main() -> None:
    settings = Settings()
    configure_logging(log_dir=settings.log_dir)
    init_service(settings)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()