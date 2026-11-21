"""Selection, summaries and exact-time evaluation of one forecast issuance.

All joins use UTC instants. A forecast is never shifted to fit observations,
and future targets do not acquire observed values through interpolation.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from contracts.forecast_schema import Forecast


EVALUATION_COLUMNS = [
    "timestamp",
    "predicted_load",
    "observed_load",
    "residual",
    "absolute_error",
    "lead_hour",
    "issued_at",
    "horizon_hours",
    "region",
    "unit",
    "dataset_split",
]


def _utc_timestamp(value: object, field: str) -> pd.Timestamp:
    """Normalize an aware timestamp, refusing implicit local/UTC assumptions."""
    try:
        result = pd.Timestamp(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{field}: timestamp inválido.") from exc
    if pd.isna(result) or result.tzinfo is None:
        raise ValueError(f"{field}: informe data/hora com fuso horário.")
    return result.tz_convert("UTC")


def _finite_loads(values: pd.Series, field: str) -> pd.Series:
    if values.map(lambda item: isinstance(item, (bool, np.bool_))).any():
        raise ValueError(f"{field}: valores booleanos não são cargas.")
    try:
        result = pd.to_numeric(values, errors="raise").astype(float)
    except (ValueError, TypeError, OverflowError) as exc:
        raise ValueError(f"{field}: as cargas devem ser números finitos.") from exc
    if not np.isfinite(result.to_numpy()).all() or (result < 0).any():
        raise ValueError(f"{field}: as cargas devem ser finitas e não negativas.")
    return result


def _prediction_frame(forecast: Forecast) -> pd.DataFrame:
    """Defend calculations even when a caller constructs Forecast manually."""
    if (
        type(forecast.horizon_hours) is not int
        or forecast.horizon_hours not in (24, 48)
    ):
        raise ValueError("O horizonte deve ser 24 ou 48 horas.")
    if forecast.unit not in ("MW", "MWmed"):
        raise ValueError("A unidade da previsão deve ser MW ou MWmed, sem conversão implícita.")
    if not isinstance(forecast.region, str) or not forecast.region.strip():
        raise ValueError("A previsão deve identificar a região.")
    issued_at = _utc_timestamp(forecast.issued_at, "issued_at")
    required = {"timestamp", "predicted_load"}
    if not required.issubset(forecast.predictions.columns):
        raise ValueError("A previsão deve conter timestamp e predicted_load.")
    frame = forecast.predictions[["timestamp", "predicted_load"]].copy()
    if len(frame) != forecast.horizon_hours:
        raise ValueError("A quantidade de previsões deve corresponder ao horizonte.")
    frame["timestamp"] = pd.to_datetime(
        [_utc_timestamp(value, "timestamp") for value in frame["timestamp"]],
        utc=True,
    )
    frame["predicted_load"] = _finite_loads(frame["predicted_load"], "predicted_load")
    if frame["timestamp"].duplicated().any():
        raise ValueError("A previsão contém timestamps duplicados.")
    if not (frame["timestamp"] > issued_at).all():
        raise ValueError("Todos os alvos devem ser posteriores à emissão da previsão.")
    if (frame["timestamp"].iloc[0] - issued_at).value > 3_600_000_000_000:
        raise ValueError("A primeira previsão deve ocorrer até uma hora após a emissão.")
    differences = frame["timestamp"].diff().dropna()
    if not differences.dt.total_seconds().eq(3600).all():
        raise ValueError("As previsões devem estar ordenadas em intervalos de uma hora.")
    return frame.reset_index(drop=True)


def forecast_summary(forecast: Forecast) -> dict[str, float | pd.Timestamp]:
    """Return descriptive forecast values, never performance estimates."""
    frame = _prediction_frame(forecast)
    peak = frame.loc[frame["predicted_load"].idxmax()]
    loads = frame["predicted_load"].to_numpy(dtype=float)
    scale = float(loads.max())
    # Scaling keeps a finite mean even when the unscaled sum exceeds float64.
    mean_load = float(np.mean(loads / scale) * scale) if scale else 0.0
    return {
        "mean_load": mean_load,
        "peak_load": float(peak["predicted_load"]),
        "peak_timestamp": peak["timestamp"],
        "min_load": float(frame["predicted_load"].min()),
    }


def export_forecast_csv(forecast: Forecast) -> bytes:
    """Export the selected full run, preserving issuance and model provenance."""
    frame = _prediction_frame(forecast)
    frame["timestamp"] = frame["timestamp"].map(lambda value: value.isoformat())
    frame["issued_at"] = _utc_timestamp(forecast.issued_at, "issued_at").isoformat()
    frame["issued_at_original"] = forecast.issued_at_original or frame["issued_at"].iloc[0]
    frame["model_name"] = forecast.model_name
    frame["model_version"] = forecast.model_version
    frame["horizon_hours"] = forecast.horizon_hours
    frame["region"] = forecast.region
    frame["unit"] = forecast.unit
    frame["dataset_split"] = getattr(forecast, "dataset_split", "unspecified")
    frame["source_file"] = forecast.source_path.name if forecast.source_path is not None else ""
    return frame.to_csv(index=False, lineterminator="\n").encode("utf-8-sig")


def _empty_evaluation() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "timestamp": pd.Series(dtype="datetime64[ns, UTC]"),
            "predicted_load": pd.Series(dtype=float),
            "observed_load": pd.Series(dtype=float),
            "residual": pd.Series(dtype=float),
            "absolute_error": pd.Series(dtype=float),
            "lead_hour": pd.Series(dtype=float),
            "issued_at": pd.Series(dtype="datetime64[ns, UTC]"),
            "horizon_hours": pd.Series(dtype=int),
            "region": pd.Series(dtype=str),
            "unit": pd.Series(dtype=str),
            "dataset_split": pd.Series(dtype=str),
        }
    )


def normalize_observations(observations: pd.DataFrame) -> pd.DataFrame:
    """Validate observed series without converting MW and MWmed into each other."""
    required = ["timestamp", "observed_load", "region", "unit"]
    if observations.empty:
        return pd.DataFrame({
            "timestamp": pd.Series(dtype="datetime64[ns, UTC]"),
            "observed_load": pd.Series(dtype=float),
            "region": pd.Series(dtype=str),
            "unit": pd.Series(dtype=str),
        })
    if not set(required).issubset(observations.columns):
        raise ValueError("As observações devem conter timestamp, observed_load, region e unit.")
    observed = observations[required].copy()
    if isinstance(observed["timestamp"].dtype, pd.DatetimeTZDtype):
        observed["timestamp"] = observed["timestamp"].dt.tz_convert("UTC")
        if observed["timestamp"].isna().any():
            raise ValueError("As observações contêm timestamps inválidos.")
    else:
        observed["timestamp"] = pd.to_datetime(
            [_utc_timestamp(value, "timestamp observado") for value in observed["timestamp"]], utc=True,
        )
    observed["observed_load"] = _finite_loads(observed["observed_load"], "observed_load")
    if not observed["unit"].isin(("MW", "MWmed")).all():
        raise ValueError("A unidade de todas as observações deve ser MW ou MWmed.")
    if not observed["region"].map(
        lambda value: isinstance(value, str) and bool(value.strip())
    ).all():
        raise ValueError("Todas as observações devem identificar a região.")
    if observed.duplicated(["region", "unit", "timestamp"]).any():
        raise ValueError("Há observações duplicadas para a mesma região, unidade e instante.")
    return observed.sort_values(["region", "unit", "timestamp"]).reset_index(drop=True)


def prepare_evaluation(
    forecast: Forecast,
    observations: pd.DataFrame,
    *,
    as_of: pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Match one issuance/horizon with actually available corresponding loads.

    Only exact timestamp + region + unit matches are retained. ``as_of`` is the
    latest instant considered observable and defaults to the current UTC time.
    Residual is observed minus predicted load, in the declared unit. ``lead_hour`` is elapsed
    hours from issuance, which can be fractional for non-hourly issuance times.
    """
    predictions = _prediction_frame(forecast)
    issued_at = _utc_timestamp(forecast.issued_at, "issued_at")
    cutoff = (
        pd.Timestamp.now(tz="UTC")
        if as_of is None
        else _utc_timestamp(as_of, "as_of")
    )
    if observations.empty:
        return _empty_evaluation()
    observed = normalize_observations(observations)
    observed = observed.loc[
        observed["region"].eq(forecast.region)
        & observed["unit"].eq(forecast.unit)
        & observed["timestamp"].le(cutoff),
        ["timestamp", "observed_load"],
    ]
    predictions = predictions.loc[predictions["timestamp"].le(cutoff)]
    aligned = predictions.merge(observed, on="timestamp", how="inner", validate="one_to_one")
    if aligned.empty:
        return _empty_evaluation()
    aligned["residual"] = aligned["observed_load"] - aligned["predicted_load"]
    aligned["absolute_error"] = aligned["residual"].abs()
    aligned["lead_hour"] = (aligned["timestamp"] - issued_at).dt.total_seconds() / 3600
    aligned["issued_at"] = issued_at
    aligned["horizon_hours"] = forecast.horizon_hours
    aligned["region"] = forecast.region
    aligned["unit"] = forecast.unit
    aligned["dataset_split"] = getattr(forecast, "dataset_split", "unspecified")
    return aligned[EVALUATION_COLUMNS].sort_values("timestamp").reset_index(drop=True)
