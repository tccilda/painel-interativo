"""Seleção temporal do histórico, sem interpolação ou preenchimento de lacunas."""

from datetime import date, timedelta

import pandas as pd

def _availability_cutoff(as_of: pd.Timestamp | None) -> pd.Timestamp:
    cutoff = pd.Timestamp.now(tz="UTC") if as_of is None else pd.Timestamp(as_of)
    if pd.isna(cutoff) or cutoff.tzinfo is None:
        raise ValueError("O instante de disponibilidade deve conter fuso horário.")
    return cutoff.tz_convert("UTC")


def future_observation_count(
    observations: pd.DataFrame, region: str | None = None,
    *, unit: str | None = None, as_of: pd.Timestamp | None = None,
) -> int:
    if observations.empty:
        return 0
    selected = observations if region is None else observations.loc[observations["region"] == region]
    if unit is not None:
        selected = selected.loc[selected["unit"] == unit]
    return int(selected["timestamp"].gt(_availability_cutoff(as_of)).sum())


def region_history(
    observations: pd.DataFrame, region: str | None,
    *, unit: str | None = None, as_of: pd.Timestamp | None = None,
) -> pd.DataFrame:
    if observations.empty or region is None:
        return observations.iloc[:0].copy()
    selected = observations.loc[
        (observations["region"] == region)
        & observations["timestamp"].le(_availability_cutoff(as_of))
    ].sort_values("timestamp").reset_index(drop=True)
    if unit is not None:
        selected = selected.loc[selected["unit"] == unit].copy()
    elif selected["unit"].nunique() > 1:
        raise ValueError("Selecione uma única unidade para consultar o histórico.")
    return selected


def filter_history(
    observations: pd.DataFrame, start: date, end: date,
    timezone: str = "America/Sao_Paulo",
) -> pd.DataFrame:
    if end < start:
        raise ValueError("A data final deve ser igual ou posterior à inicial.")
    if observations.empty:
        return observations.copy()
    first = pd.Timestamp(start).tz_localize(timezone).tz_convert("UTC")
    stop = pd.Timestamp(end + timedelta(days=1)).tz_localize(timezone).tz_convert("UTC")
    return observations.loc[
        (observations["timestamp"] >= first) & (observations["timestamp"] < stop)
    ].copy()
