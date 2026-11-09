# data_processor.py
import logging

import pandas as pd

logger = logging.getLogger(__name__)


def remove_duplicates(df):
    """Remove duplicate rows."""
    before = len(df)
    df = df.drop_duplicates()
    logger.debug("remove_duplicates: %d → %d rows", before, len(df))
    return df


def handle_missing(df, axis="rows"):
    """Drop rows or columns containing missing values."""
    if axis not in ("rows", "columns"):
        logger.error("Unsupported axis: %s", axis)
        raise ValueError(f"Unsupported axis: {axis}")

    if axis == "rows":
        before = len(df)
        df = df.dropna(axis=0)
        logger.debug("handle_missing: %d → %d rows", before, len(df))
    else:
        before = df.shape[1]
        df = df.dropna(axis=1)
        logger.debug("handle_missing: %d → %d columns", before, df.shape[1])

    return df


def remove_outliers(df, columns, method, threshold):
    """Remove outliers from the specified numeric columns."""
    if method not in ("iqr", "zscore"):
        logger.error("Unsupported outlier method: %s", method)
        raise ValueError(f"Unsupported outlier method: {method}")

    for column in columns:
        if column not in df.columns:
            logger.warning("Column not found: %s", column)
            continue

        if not pd.api.types.is_numeric_dtype(df[column]):
            logger.warning("Column is not numeric: %s", column)
            continue

        before = len(df)

        if method == "iqr":
            q1 = df[column].quantile(0.25)
            q3 = df[column].quantile(0.75)
            iqr = q3 - q1
            lower = q1 - threshold * iqr
            upper = q3 + threshold * iqr
        else:
            mean = df[column].mean()
            std = df[column].std()
            lower = mean - threshold * std
            upper = mean + threshold * std

        df = df[(df[column] >= lower) & (df[column] <= upper)]
        logger.debug(
            "%s: method=%s, threshold=%s, lower=%s, upper=%s, removed=%d",
            column, method, threshold, lower, upper, before - len(df),
        )

    return df


def process_data(df, config):
    """Apply the processing steps enabled in the configuration."""
    processing = config["processing"]

    if processing.get("remove_duplicates"):
        df = remove_duplicates(df)

    missing = processing.get("missing", {})
    if missing.get("enabled"):
        df = handle_missing(df, axis=missing["axis"])

    outliers = processing.get("outliers", {})
    if outliers.get("enabled"):
        df = remove_outliers(
            df,
            columns=outliers["columns"],
            method=outliers["method"],
            threshold=outliers["threshold"],
        )

    return df


def create_cleaning_report(df_before, df_after):
    """Return a dictionary summarizing the cleaning results."""
    rows_before, columns_before = df_before.shape
    rows_after, columns_after = df_after.shape
    return {
        "rows_before": rows_before,
        "rows_after": rows_after,
        "rows_removed": rows_before - rows_after,
        "columns_before": columns_before,
        "columns_after": columns_after,
        "columns_removed": columns_before - columns_after,
    }