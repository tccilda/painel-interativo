"""Gráficos mantêm unidades, fuso, proveniência e ausências sem criar valores."""

import json

import pandas as pd
import pytest

from components.charts import (
    calendar_profile_chart, daily_pattern_chart, degradation_chart,
    explorer_chart, history_chart,
    load_temperature_chart, monthly_chart, temperature_scatter,
    weekly_pattern_chart,
)
from services.pattern_service import aggregate_load_temperature


def sample_frame():
    return pd.DataFrame({
        "timestamp": pd.date_range("2026-01-01T00:00Z", periods=4, freq="h"),
        "observed_load": [100., 110., 120., 130.], "predicted_load": [None, None, 125., 135.],
        "seasonal_load": [None, None, 115., 125.], "temperature_c": [20., 21., 22., 23.],
        "station": ["Estação sintética"] * 4, "phase": ["histórico", "histórico", "previsão", "previsão"],
        "residual": [0., 0., -5., -5.],
    })


def test_explorer_separates_four_series_and_marks_issuance():
    frame = sample_frame()
    figure = explorer_chart(frame, pd.Timestamp("2026-01-01T01:00Z"))
    assert len(figure.data) == 4
    assert [trace.name for trace in figure.data] == [
        "Histórico", "Previsto", "Real", "Semana anterior",
    ]
    assert len(figure.layout.shapes) == 1
    assert "MWmed" in figure.layout.yaxis.title.text
    assert all("UTC-0300" in label for trace in figure.data for label in trace.customdata if label)
    json.loads(figure.to_json())


def test_future_explorer_omits_observed_target_legend_without_observations():
    frame = sample_frame()
    frame.loc[frame["phase"].eq("previsão"), "observed_load"] = float("nan")
    figure = explorer_chart(frame, pd.Timestamp("2026-01-01T01:00Z"))
    assert [trace.name for trace in figure.data] == [
        "Histórico", "Previsto", "Semana anterior",
    ]
    assert len(figure.data) == 3
    json.loads(figure.to_json())


@pytest.mark.parametrize("function", [history_chart, daily_pattern_chart, weekly_pattern_chart])
def test_existing_charts_support_dynamic_unit_without_changing_data(function):
    frame = sample_frame()
    original = frame.copy(deep=True)
    figure = function(frame, unit="MWmed")
    assert "MWmed" in figure.layout.yaxis.title.text
    assert all("MWmed" in trace.hovertemplate for trace in figure.data)
    pd.testing.assert_frame_equal(frame, original)
    json.loads(figure.to_json())


def test_history_chart_breaks_missing_hours():
    frame = sample_frame().iloc[[0, 1, 3]]
    figure = history_chart(frame)
    assert None in figure.data[0].y
    assert figure.data[0].connectgaps is False


def test_single_observation_and_isolated_points_remain_visible():
    isolated = history_chart(sample_frame().iloc[[0]])
    assert isolated.data[0].mode == "lines+markers"
    assert isolated.data[0].marker.size[0] > 0
    with_gap = history_chart(sample_frame().iloc[[0, 1, 3]])
    assert with_gap.data[0].marker.size[-1] > 0


def test_error_plot_uses_integer_step_instead_of_fractional_elapsed_lead():
    frame = pd.DataFrame({
        "model_label": ["24 h", "24 h", "48 h"], "horizon_hours": [24, 24, 48],
        "forecast_step": [1, 2, 1], "lead_hour": [.75, 1.75, .75], "mae": [1., 2., 3.],
    })
    figure = degradation_chart(frame)
    assert list(figure.data[0].x) == [1, 2]
    assert "Passo" in figure.layout.xaxis.title.text
    json.loads(figure.to_json())


@pytest.mark.parametrize("metric,unit,expected", [
    ("mae", "MWmed", [1., 3.]), ("rmse", "MWmed", [2., 4.]), ("mape", "%", [5., 6.]),
])
def test_error_metric_selection_preserves_values_units_and_missing_steps(metric, unit, expected):
    frame = pd.DataFrame({
        "model_label": ["24 h"] * 2, "horizon_hours": [24] * 2, "forecast_step": [1, 3],
        "mae": [1., 3.], "rmse": [2., 4.], "mape": [5., 6.],
        "n_pairs": [10, 8], "mape_valid_pairs": [9, 6], "mape_excluded_zeros": [1, 2],
    })
    figure = degradation_chart(frame, metric=metric)
    assert list(figure.data[0].x) == [1, None, 3]
    assert list(figure.data[0].y) == [expected[0], None, expected[1]]
    assert figure.layout.yaxis.title.text == f"{metric.upper()} ({unit})"
    assert "Pares totais" in figure.data[0].hovertemplate
    assert list(figure.data[0].customdata[0]) == [10, 9, 1]
    assert ("Pares MAPE" in figure.data[0].hovertemplate) is (metric == "mape")
    json.loads(figure.to_json())


def test_mape_hover_does_not_invent_its_valid_sample_count_for_legacy_input():
    frame = pd.DataFrame({"forecast_step": [1], "mape": [5.], "n_pairs": [10]})
    figure = degradation_chart(frame, metric="mape")
    assert "Pares totais" in figure.data[0].hovertemplate
    assert "Pares MAPE" not in figure.data[0].hovertemplate


@pytest.mark.parametrize("metric,unit", [("mae", "MWmed"), ("rmse", "MWmed"), ("mape", "%")])
def test_small_fractional_errors_keep_adaptive_axis_precision(metric, unit):
    frame = pd.DataFrame({
        "forecast_step": [1, 2, 3], metric: [0.10, 0.25, 0.75], "n_pairs": [10, 10, 10],
    })
    figure = degradation_chart(frame, metric=metric)
    # O formato inteiro ',.0f' faria marcas 0,5 e 1,0 repetirem o mesmo rótulo.
    assert figure.layout.yaxis.tickformat is None
    assert figure.layout.yaxis.title.text == f"{metric.upper()} ({unit})"
    assert list(figure.data[0].y) == [0.10, 0.25, 0.75]
    assert "%{y:,.2f}" in figure.data[0].hovertemplate
    assert "tickformat" not in json.loads(figure.to_json())["layout"]["yaxis"]


def test_error_plot_refuses_unknown_metric_and_keeps_undefined_mape_empty():
    with pytest.raises(ValueError, match="métrica"):
        degradation_chart(pd.DataFrame(), metric="accuracy")
    figure = degradation_chart(pd.DataFrame({"forecast_step": [1], "mape": [None]}), metric="mape")
    assert not figure.data and figure.layout.annotations


def test_weather_charts_show_celsius_and_separate_units():
    frame = sample_frame()
    scatter = temperature_scatter(frame)
    assert "°C" in scatter.layout.xaxis.title.text
    assert "MWmed" in scatter.layout.yaxis.title.text
    dual = load_temperature_chart(frame)
    assert "MWmed" in dual.layout.yaxis.title.text
    assert "°C" in dual.layout.yaxis2.title.text
    assert dual.data[1].yaxis == "y2"
    assert dual.data[0].connectgaps is False and dual.data[1].connectgaps is False
    json.loads(scatter.to_json())
    json.loads(dual.to_json())


def test_weather_scatter_uses_webgl_without_discarding_pairs_or_local_timestamps():
    frame = pd.concat([sample_frame()] * 1000, ignore_index=True)
    figure = temperature_scatter(frame)
    assert figure.data[0].type == "scattergl"
    assert len(figure.data[0].x) == len(frame)
    assert all("UTC-0300" in value for value in figure.data[0].customdata)
    assert "31/12/2025 21:00" in figure.data[0].customdata[0]
    assert "%{customdata}" in figure.data[0].hovertemplate


def test_daily_weather_chart_respects_period_boundaries_instead_of_hourly_gap_rule():
    frame = sample_frame().iloc[:2].copy()
    frame["timestamp"] = pd.to_datetime(["2026-01-01T03:00Z", "2026-01-02T03:00Z"])
    daily = aggregate_load_temperature(frame, frequency="daily")
    figure = load_temperature_chart(daily, frequency="daily")
    assert len(figure.data[0].y) == 2
    assert None not in figure.data[0].y
    assert "média" in figure.layout.yaxis.title.text
    assert "Pares: 1 / 24 h possíveis" in figure.data[0].customdata[0]
    json.loads(figure.to_json())


def test_calendar_chart_keeps_scopes_separate_and_hour_gaps():
    profile = pd.DataFrame({
        "hour": [0, 2, 0], "day_type": ["feriado"] * 3,
        "holiday_scope": ["municipal", "municipal", "nacional"],
        "mean": [100., 120., 200.], "count": [2, 2, 1],
    })
    figure = calendar_profile_chart(profile)
    assert len(figure.data) == 2
    assert any("municipal" in trace.name for trace in figure.data)
    assert any("nacional" in trace.name for trace in figure.data)
    assert pd.isna(figure.data[0].y[1])
    json.loads(figure.to_json())


def test_monthly_chart_orders_years_chronologically():
    frame = pd.DataFrame({"month": ["2026-01", "2024-01", "2025-01"], "year": [2026, 2024, 2025], "mean": [3., 1., 2.], "count": [4, 4, 4]})
    figure = monthly_chart(frame)
    times = pd.DatetimeIndex(figure.data[0].x)
    values = pd.Series(figure.data[0].y, index=times)
    assert figure.layout.xaxis.type == "date"
    assert values.dropna().tolist() == [1., 2., 3.]
    assert values.index.is_monotonic_increasing
    assert pd.isna(values.loc["2024-02-01"])
    assert figure.data[0].connectgaps is False
    json.loads(figure.to_json())


@pytest.mark.parametrize("function", [
    history_chart, daily_pattern_chart, weekly_pattern_chart,
    degradation_chart, temperature_scatter, load_temperature_chart,
    calendar_profile_chart, monthly_chart,
])
def test_empty_charts_explain_absence_without_dummy_series(function):
    figure = function(pd.DataFrame())
    assert len(figure.data) == 0
    assert len(figure.layout.annotations) == 1
    json.loads(figure.to_json())
