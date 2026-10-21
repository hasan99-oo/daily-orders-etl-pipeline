"""Extract stage: load the raw source file into a DataFrame."""
import logging
import pandas as pd

from config import REQUIRED_COLUMNS

logger = logging.getLogger("etl.extract")


def extract_orders(source_path) -> pd.DataFrame:
    """Read the raw orders CSV and confirm it has the columns we expect.

    Deliberately does NOT clean or validate row-level data here --
    that's the transform stage's job, so extraction stays a fast,
    dumb read that fails loudly on structural problems only.
    """
    logger.info("Extracting from %s", source_path)
    df = pd.read_csv(source_path, dtype=str)  # read as str; transform handles typing

    missing = set(REQUIRED_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"Source file is missing required columns: {missing}")

    logger.info("Extracted %d raw rows", len(df))
    return df
