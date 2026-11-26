"""Temporal alignment and export preserve the identity of a selected run."""

from __future__ import annotations

from dataclasses import replace
from io import BytesIO
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from contracts.forecast_schema import Forecast
from services.forecast_service import (
    export_forecast_csv,
    forecast_summary,
    prepare_evaluation,
)


@pytest.fixture
def forecast() -> Forecast:
    return Forecast(
        model_name="Modelo de teste",
        model_version="1.0",
        horizon_hours=24,
        region="Região A",
        unit="MW",
        issued_at=pd.Timestamp("2025-01-01T00:00:00Z"),
        predictions=pd.DataFrame(
            {
                "timestamp": pd.date_range("2025-01-01T01:00:00Z", periods=24, freq="h"),
                "predicted_load": [100.0 + i for i in range(24)],
            }
        ),
    )


def observation_frame(forecast: Forecast) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "timestamp": forecast.predictions["timestamp"],
            "observed_load": forecast.predictions["predicted_load"] + 2,
            "region": forecast.region,
            "unit": "MW",
        }
    )


def test_evaluation_keeps_mw_and_mwmed_separate(forecast):
    mwmed = replace(forecast, unit="MWmed")
    observations = observation_frame(forecast)
    assert prepare_evaluation(mwmed, observations).empty
    observations["unit"] = "MWmed"
    result = prepare_evaluation(mwmed, observations)
    assert len(result) == 24
    assert result["unit"].eq("MWmed").all()


def test_summary_reports_values_and_peak_timestamp(forecast):
    result = forecast_summary(forecast)
    assert result["mean_load"] == pytest.approx(111.5)
    assert result["min_load"] == 100
    assert result["peak_load"] == 123
    assert result["peak_timestamp"] == pd.Timestamp("2025-01-02T00:00:00Z")


def test_export_contains_full_selected_run_and_provenance(forecast):
    result = export_forecast_csv(forecast)
    assert result.startswith(b"\xef\xbb\xbf")
    frame = pd.read_csv(BytesIO(result))
    assert len(frame) == 24
    assert frame["horizon_hours"].eq(24).all()
    assert frame["region"].eq(forecast.region).all()
    assert frame["unit"].eq("MW").all()
    assert frame["model_name"].eq(forecast.model_name).all()
    assert frame["issued_at"].nunique() == 1
    assert pd.Timestamp(frame["issued_at"].iloc[0]) == forecast.issued_at
    assert pd.Timestamp(frame["timestamp"].iloc[-1]) == forecast.predictions["timestamp"].iloc[-1]


def test_export_preserves_original_timezone_and_source_filename(forecast):
    original = "2024-12-31T21:00:00-03:00"
    run = replace(forecast, issued_at_original=original, source_path=Path("data/predictions/modelo_24h.json"))
    frame = pd.read_csv(BytesIO(export_forecast_csv(run)))
    assert frame["issued_at_original"].eq(original).all()
    assert frame["source_file"].eq("modelo_24h.json").all()
    assert frame["issued_at"].map(pd.Timestamp).eq(pd.Timestamp(original)).all()


def test_summary_mean_stays_finite_for_large_finite_loads(forecast):
    frame = forecast.predictions.copy()
    frame["predicted_load"] = 1e308
    run = replace(forecast, predictions=frame)
    with np.errstate(over="raise", invalid="raise"):
        summary = forecast_summary(run)
    assert summary["mean_load"] == 1e308


def test_evaluation_matches_timezone_equivalent_instants(forecast):
    observations = observation_frame(forecast)
    observations["timestamp"] = observations["timestamp"].dt.tz_convert("America/Sao_Paulo")
    result = prepare_evaluation(forecast, observations, as_of=pd.Timestamp("2025-01-03T00:00:00Z"))
    assert len(result) == 24
    assert result["residual"].eq(2).all()
    assert result["absolute_error"].eq(2).all()
    assert result["lead_hour"].tolist() == list(range(1, 25))
    assert result["issued_at"].eq(forecast.issued_at).all()
    assert result["horizon_hours"].eq(24).all()
    assert str(result["timestamp"].dt.tz) == "UTC"


def test_evaluation_never_interpolates_missing_observations(forecast):
    observations = observation_frame(forecast).iloc[[0, 2, 5]].copy()
    result = prepare_evaluation(forecast, observations, as_of=pd.Timestamp("2025-01-03T00:00:00Z"))
    assert result["lead_hour"].tolist() == [1, 3, 6]


def test_evaluation_excludes_other_region(forecast):
    observations = observation_frame(forecast)
    observations["region"] = "Região B"
    assert prepare_evaluation(forecast, observations).empty


def test_evaluation_excludes_targets_not_yet_observable(forecast):
    observations = observation_frame(forecast)
    result = prepare_evaluation(forecast, observations, as_of=pd.Timestamp("2025-01-01T05:00:00Z"))
    assert result["lead_hour"].tolist() == [1, 2, 3, 4, 5]


def test_future_forecast_has_no_evaluation_even_if_file_has_future_observations(forecast):
    observations = observation_frame(forecast)
    assert prepare_evaluation(forecast, observations, as_of=forecast.issued_at).empty


def test_empty_observations_keep_evaluation_schema(forecast):
    result = prepare_evaluation(forecast, pd.DataFrame())
    assert result.empty
    assert {"residual", "issued_at", "horizon_hours", "timestamp"}.issubset(result.columns)


def test_evaluation_refuses_duplicate_observations_after_normalization(forecast):
    observations = observation_frame(forecast)
    observations = pd.concat([observations, observations.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="duplicadas"):
        prepare_evaluation(forecast, observations)


@pytest.mark.parametrize("unit", ["kW", "MWh", "mw"])
def test_evaluation_refuses_inconsistent_units(forecast, unit):
    observations = observation_frame(forecast)
    observations["unit"] = unit
    with pytest.raises(ValueError, match="unidade"):
        prepare_evaluation(forecast, observations)


def test_evaluation_refuses_naive_observation_timestamps(forecast):
    observations = observation_frame(forecast)
    observations["timestamp"] = observations["timestamp"].dt.tz_localize(None)
    with pytest.raises(ValueError, match="fuso"):
        prepare_evaluation(forecast, observations)


def test_evaluation_refuses_invalid_issuance_relation(forecast):
    invalid = replace(forecast, issued_at=forecast.predictions["timestamp"].iloc[0])
    with pytest.raises(ValueError, match="posteriores"):
        prepare_evaluation(invalid, pd.DataFrame())


def test_services_refuse_horizon_shifted_far_from_issuance(forecast):
    invalid = replace(forecast, issued_at=pd.Timestamp("2024-12-25T00:00:00Z"))
    with pytest.raises(ValueError, match="primeira previsão"):
        prepare_evaluation(invalid, pd.DataFrame())
    with pytest.raises(ValueError, match="primeira previsão"):
        forecast_summary(invalid)
    with pytest.raises(ValueError, match="primeira previsão"):
        export_forecast_csv(invalid)


def test_first_target_one_nanosecond_beyond_hour_is_refused(forecast):
    invalid = replace(forecast, issued_at=pd.Timestamp("2024-12-31T23:59:59.999999999Z"))
    with pytest.raises(ValueError, match="primeira previsão"):
        forecast_summary(invalid)


def test_evaluation_refuses_naive_cutoff(forecast):
    with pytest.raises(ValueError, match="fuso"):
        prepare_evaluation(forecast, pd.DataFrame(), as_of=pd.Timestamp("2025-01-03"))


def test_evaluation_keeps_fractional_elapsed_lead_time(forecast):
    run = replace(forecast, issued_at=pd.Timestamp("2025-01-01T00:15:00Z"))
    result = prepare_evaluation(run, observation_frame(run), as_of=pd.Timestamp("2025-01-03T00:00:00Z"))
    assert result["lead_hour"].iloc[0] == 0.75


def test_services_do_not_mutate_inputs(forecast):
    observations = observation_frame(forecast)
    original_predictions = forecast.predictions.copy(deep=True)
    original_observations = observations.copy(deep=True)
    prepare_evaluation(forecast, observations)
    export_forecast_csv(forecast)
    pd.testing.assert_frame_equal(forecast.predictions, original_predictions)
    pd.testing.assert_frame_equal(observations, original_observations)
