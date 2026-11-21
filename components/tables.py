"""Tabelas com valores numéricos preservados e exibição brasileira."""

import pandas as pd
import streamlit as st

from components.metrics_cards import format_number


def data_table(frame: pd.DataFrame, decimals: int = 2, height: int | str = "auto", integer_columns: tuple[str, ...] = (), *, labels: dict[str, str] | None = None) -> None:
    numeric = frame.select_dtypes(include="number").columns
    formats = {}
    for column in numeric:
        places = 0 if column in integer_columns or pd.api.types.is_integer_dtype(frame[column].dtype) else decimals
        formats[column] = lambda value, places=places: format_number(value, places)
    styled = frame.style.format(formats, na_rep="N/D")
    st.dataframe(styled, hide_index=True, width="stretch", height=height, column_config=labels)


def csv_bytes(frame: pd.DataFrame) -> bytes:
    """Exporta os números originais, sem usar as strings arredondadas da tela."""
    return frame.to_csv(index=False, lineterminator="\n").encode("utf-8-sig")
