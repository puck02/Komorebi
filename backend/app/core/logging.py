import logging


def configure_logging(level: str) -> None:
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(level=numeric_level, format="%(message)s")
    logging.getLogger("komorebi.agent").setLevel(numeric_level)
