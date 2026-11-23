"""Tabelas com valores numéricos preservados e exibição brasileira."""

import pandas as pd
import streamlit as st

from components.metrics_cards import format_number


def data_table(
    frame: pd.DataFrame, decimals: int = 2, height: int | str = "auto",
    integer_columns: tuple[str, ...] = (), *, labels: dict[str, str] | None = None,
    alt: str | None = None,
) -> None:
    # A grade nativa recebe a representação final para mostrar N/D inclusive em colunas numéricas.
    display = frame.astype("string").fillna("N/D").replace("", "N/D")
    for column in frame.select_dtypes(include="number"):
        places = 0 if column in integer_columns or pd.api.types.is_integer_dtype(frame[column]) else decimals
        display[column] = frame[column].map(lambda value: format_number(value, places))
    st.dataframe(display, hide_index=True, width="stretch", height=height, column_config=labels, alt=alt)


def csv_bytes(frame: pd.DataFrame) -> bytes:
    """Exporta os números originais, sem usar as strings arredondadas da tela."""
    return frame.to_csv(index=False, lineterminator="\n").encode("utf-8-sig")
