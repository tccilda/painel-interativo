"""Perfis observados e junções exatas de carga, meteorologia e calendário.

As entradas devem estar filtradas para a região e unidade de análise. Nenhuma
função interpola valores ou deduz feriados a partir de datas ausentes.
"""

from __future__ import annotations

from datetime import timedelta

import numpy as np
import pandas as pd


DEFAULT_TIMEZONE = "America/Sao_Paulo"


def _stable_mean(values: pd.Series) -> float:
    """Média sem somar diretamente cargas finitas muito grandes."""
    scale = float(values.abs().max())
    return float((values / scale).mean()) * scale if scale else 0.0


def _profile(observations: pd.DataFrame, key: str, timezone: str) -> pd.DataFrame:
    if observations.empty:
        return pd.DataFrame({"mean": pd.Series(dtype=float), "count": pd.Series(dtype="int64")}).rename_axis(key)
    frame = observations[["timestamp", "observed_load"]].copy()
    local = pd.to_datetime(frame["timestamp"], utc=True).dt.tz_convert(timezone)
    frame[key] = local.dt.hour if key == "hour" else local.dt.dayofweek
    return frame.groupby(key, sort=True)["observed_load"].agg(mean=_stable_mean, count="count")


def daily_profile(observations: pd.DataFrame, timezone: str = DEFAULT_TIMEZONE) -> pd.DataFrame:
    """Média por hora local; horas sem dados permanecem com média NaN."""
    result = _profile(observations, "hour", timezone).reindex(pd.RangeIndex(24, name="hour"))
    result["count"] = result["count"].fillna(0).astype("int64")
    return result


def weekly_profile(observations: pd.DataFrame, timezone: str = DEFAULT_TIMEZONE) -> pd.DataFrame:
    """Média por dia local, segunda=0; não adiciona dias sem observações."""
    return _profile(observations, "weekday", timezone)


def monthly_profile(observations: pd.DataFrame, timezone: str = DEFAULT_TIMEZONE) -> pd.DataFrame:
    """Evolução mensal por ano e mês civil."""
    if observations.empty:
        return pd.DataFrame({
            "month": pd.Series(dtype=str), "year": pd.Series(dtype="int64"),
            "mean": pd.Series(dtype=float), "count": pd.Series(dtype="int64"),
        })
    frame = observations[["timestamp", "observed_load"]].copy()
    local = pd.to_datetime(frame["timestamp"], utc=True).dt.tz_convert(timezone)
    frame["month"] = local.dt.strftime("%Y-%m")
    frame["year"] = local.dt.year
    return frame.groupby(["month", "year"], sort=True)["observed_load"].agg(
        mean=_stable_mean, count="count",
    ).reset_index()


def annual_profile(observations: pd.DataFrame, timezone: str = DEFAULT_TIMEZONE) -> pd.DataFrame:
    years = pd.to_datetime(observations["timestamp"], utc=True).dt.tz_convert(timezone).dt.year
    return observations.groupby(years.rename("year"))["observed_load"].agg(
        mean=_stable_mean, count="count",
    ).reset_index()


def _regional(frame: pd.DataFrame, region: str) -> pd.DataFrame:
    return frame.loc[frame["region"].eq(region)].copy() if "region" in frame else frame.copy()


def join_weather(
    observations: pd.DataFrame,
    weather: pd.DataFrame,
    region: str,
    station: str | None = None,
    timezone: str = DEFAULT_TIMEZONE,
) -> pd.DataFrame:
    """Associa por instante exato; média espacial é identificada explicitamente.

    ``timezone`` pertence à interface compartilhada, mas não altera as chaves:
    os instantes são comparados em UTC, sem arredondamento à hora mais próxima.
    """
    columns = ["timestamp", "observed_load", "temperature_c", "station"]
    if observations.empty or weather.empty:
        return pd.DataFrame(columns=columns)
    observed = _regional(observations, region)[["timestamp", "observed_load"]].copy()
    climate = _regional(weather, region)[["timestamp", "temperature_c", "station"]].copy()
    observed["timestamp"] = pd.to_datetime(observed["timestamp"], utc=True)
    climate["timestamp"] = pd.to_datetime(climate["timestamp"], utc=True)
    if observed["timestamp"].duplicated().any():
        raise ValueError("Há cargas duplicadas no mesmo instante da região selecionada.")
    if climate.duplicated(["timestamp", "station"]).any():
        raise ValueError("Há temperaturas duplicadas na mesma estação e instante.")
    if station is not None:
        climate = climate.loc[climate["station"].eq(station)]
    else:
        climate = climate.groupby("timestamp", sort=True)["temperature_c"].agg(_stable_mean).reset_index()
        climate["station"] = "Média das estações disponíveis"
    joined = observed.merge(climate, on="timestamp", how="inner", validate="one_to_one")
    return joined[columns].sort_values("timestamp").reset_index(drop=True)


def aggregate_load_temperature(
    frame: pd.DataFrame,
    frequency: str = "hourly",
    timezone: str = DEFAULT_TIMEZONE,
) -> pd.DataFrame:
    """Agrega somente para visualização os pares exatos previamente filtrados.

    O chamador aplica região, unidade e disponibilidade temporal antes desta
    função. As médias de carga e temperatura usam os mesmos pares válidos.
    Dias e semanas seguem o calendário local; semanas começam na segunda-feira.
    ``period_end`` é exclusivo e ``expected_hours`` respeita mudanças de fuso.
    Períodos vazios permanecem com médias NaN e contagem zero, sem interpolação.
    """
    columns = [
        "timestamp", "observed_load", "temperature_c", "station", "n_pairs",
        "expected_hours", "period_end",
    ]
    if frequency not in {"hourly", "daily", "weekly"}:
        raise ValueError("Frequência visual inválida; use hourly, daily ou weekly.")
    if frame.empty:
        result = pd.DataFrame(columns=columns)
        for column in ("timestamp", "period_end"):
            result[column] = pd.Series(dtype="datetime64[ns, UTC]")
        return result
    missing = sorted({"timestamp", "observed_load", "temperature_c"}.difference(frame.columns))
    if missing:
        raise ValueError(f"Os pares de carga e temperatura não contêm: {', '.join(missing)}.")
    source = frame[["timestamp", "observed_load", "temperature_c"]].copy()
    if isinstance(source["timestamp"].dtype, pd.DatetimeTZDtype):
        source["timestamp"] = source["timestamp"].dt.tz_convert("UTC")
    else:
        instants = [pd.Timestamp(value) for value in source["timestamp"]]
        if any(pd.isna(value) or value.tzinfo is None for value in instants):
            raise ValueError("Os instantes dos pares devem conter fuso horário.")
        source["timestamp"] = pd.to_datetime(instants, utc=True)
    if source["timestamp"].isna().any():
        raise ValueError("Os instantes dos pares devem ser válidos.")
    if source["timestamp"].duplicated().any():
        raise ValueError("A visualização exige um único par por instante; selecione uma estação ou sua média explícita.")
    for column in ("observed_load", "temperature_c"):
        try:
            source[column] = pd.to_numeric(source[column], errors="raise").astype(float)
        except (ValueError, TypeError, OverflowError) as exc:
            raise ValueError("Carga e temperatura devem ser numéricas.") from exc
        if np.isinf(source[column]).any():
            raise ValueError("Carga e temperatura não podem conter valores infinitos.")
    if source["observed_load"].dropna().lt(0).any():
        raise ValueError("Carga observada não pode ser negativa.")
    source = source.sort_values("timestamp").reset_index(drop=True)
    stations = frame["station"].dropna().astype(str).unique() if "station" in frame else []
    station_label = str(stations[0]) if len(stations) == 1 else "Múltiplas estações" if len(stations) > 1 else "Não informada"
    paired = source[["observed_load", "temperature_c"]].notna().all(axis=1)
    # Um valor isolado de carga ou clima não participa de nenhuma das médias.
    source.loc[~paired, ["observed_load", "temperature_c"]] = np.nan
    if frequency == "hourly":
        result = source.copy()
        result["n_pairs"] = paired.astype(int)
        result["expected_hours"] = 1.0
        result["period_end"] = result["timestamp"] + timedelta(hours=1)
    else:
        local = source["timestamp"].dt.tz_convert(timezone).dt.tz_localize(None)
        source["_period"] = local.dt.normalize() if frequency == "daily" else local.dt.to_period("W-SUN").dt.start_time
        starts = pd.date_range(source["_period"].min(), source["_period"].max(), freq="D" if frequency == "daily" else "W-MON")
        final_boundary = starts[-1].to_pydatetime() + timedelta(days=1 if frequency == "daily" else 7)
        boundaries = pd.DatetimeIndex([*starts, final_boundary]).tz_localize(
            timezone, ambiguous=True, nonexistent="shift_forward",
        ).tz_convert("UTC")
        valid = source.loc[paired]
        summary = valid.groupby("_period", sort=True).agg(
            observed_load=("observed_load", _stable_mean),
            temperature_c=("temperature_c", _stable_mean),
            n_pairs=("observed_load", "count"),
        ).reindex(starts)
        result = summary.reset_index(drop=True)
        result["timestamp"] = boundaries[:-1]
        result["period_end"] = boundaries[1:]
        result["n_pairs"] = result["n_pairs"].fillna(0).astype(int)
        result["expected_hours"] = (
            result["period_end"].astype("int64") - result["timestamp"].astype("int64")
        ) / 3_600_000_000_000
    result["station"] = station_label
    return result[columns]


def calendar_profile(
    observations: pd.DataFrame,
    calendar: pd.DataFrame,
    region: str,
    timezone: str = DEFAULT_TIMEZONE,
) -> pd.DataFrame:
    """Perfil horário por categoria e escopo informados, sem inventar eventos."""
    columns = ["hour", "day_type", "holiday_scope", "mean", "count"]
    if observations.empty:
        return pd.DataFrame(columns=columns)
    observed = _regional(observations, region)[["timestamp", "observed_load"]].copy()
    local = pd.to_datetime(observed["timestamp"], utc=True).dt.tz_convert(timezone)
    observed["date"] = local.dt.date
    observed["hour"] = local.dt.hour
    if calendar.empty:
        observed["day_type"] = "nao_informado"
        observed["holiday_scope"] = "nao_informado"
    elif "timestamp" in calendar:
        events = _regional(calendar, region)[["timestamp", "day_type", "holiday_scope"]]
        observed = observed.merge(events, on="timestamp", how="left", validate="one_to_one")
        observed[["day_type", "holiday_scope"]] = observed[["day_type", "holiday_scope"]].fillna("nao_informado")
    else:
        events = _regional(calendar, region)[["date", "day_type", "holiday_scope"]].copy()
        events["date"] = pd.to_datetime(events["date"]).dt.date
        if events["date"].duplicated().any():
            raise ValueError("Há classificações de calendário duplicadas para a mesma região e data local.")
        observed = observed.merge(events, on="date", how="left", validate="many_to_one")
        observed[["day_type", "holiday_scope"]] = observed[["day_type", "holiday_scope"]].fillna("nao_informado")
    return observed.groupby(["hour", "day_type", "holiday_scope"], sort=True)["observed_load"].agg(
        mean=_stable_mean, count="count",
    ).reset_index()[columns]
