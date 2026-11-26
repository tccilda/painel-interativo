"""Tabelas com valores numéricos preservados e exibição brasileira."""

import pandas as pd
import streamlit as st

from components.metrics_cards import format_number


def data_table(
    frame: pd.DataFrame, decimals: int = 2, height: int | str = "auto",
    integer_columns: tuple[str, ...] = (), *, labels: dict[str, str] | None = None,
    alt: str | None = None, column_decimals: dict[str, int] | None = None,
) -> None:
    numeric = list(frame.select_dtypes(include="number").columns)
    sorted_frame = frame
    if numeric and len(frame) > 1:
        directions = {True: "crescente", False: "decrescente"}
        options = [None, *((column, ascending) for column in numeric for ascending in directions)]
        choices = {None: "Ordem original"}
        for column, ascending in options[1:]:
            heading = (labels or {}).get(column, column)
            choices[(column, ascending)] = f"{heading} · {directions[ascending]}"
        with st.expander("Ordenar tabela"):
            selection = st.selectbox(
                "Ordenação numérica", options, format_func=choices.__getitem__,
                help="Ordena pelos valores originais. Ausências ficam no fim. O cabeçalho da grade ordena o texto exibido.",
            )
        if selection is not None:
            column, ascending = selection
            sorted_frame = frame.sort_values(
                column, ascending=ascending, kind="stable", na_position="last",
                key=lambda values: values.replace([float("-inf"), float("inf")], float("nan")),
            )
    display = sorted_frame.astype("string").fillna("N/D").replace("", "N/D")
    for column in numeric:
        places = 0 if column in integer_columns or pd.api.types.is_integer_dtype(frame[column]) else decimals
        places = (column_decimals or {}).get(column, places)
        display[column] = sorted_frame[column].map(lambda value: format_number(value, places))
    st.dataframe(display, hide_index=True, width="stretch", height=height, column_config=labels, alt=alt)


def csv_bytes(frame: pd.DataFrame) -> bytes:
    """Exporta os números originais, sem usar as strings arredondadas da tela."""
    return frame.to_csv(index=False, lineterminator="\n").encode("utf-8-sig")
