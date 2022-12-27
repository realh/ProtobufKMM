import logging

def getLogger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logging.basicConfig(
        level = logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    return logger
