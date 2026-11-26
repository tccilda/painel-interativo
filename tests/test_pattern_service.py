"""Agregações locais, meteo exata e calendário de proveniência explícita."""

from datetime import date

import pandas as pd
import pytest

from services.pattern_service import aggregate_load_temperature, calendar_profile, daily_profile, join_weather, monthly_profile, weekly_profile


def observations(timestamps, values, region="A"):
    return pd.DataFrame({
        "timestamp": pd.to_datetime(timestamps, utc=True), "observed_load": values,
        "region": region, "unit": "MWmed",
    })


def test_daily_profile_uses_local_hour_and_known_mean_without_mutation():
    frame = observations(["2026-01-05T03:00Z", "2026-01-06T03:00Z", "2026-01-05T02:00Z"], [100., 200., 50.])
    original = frame.copy(deep=True)
    profile = daily_profile(frame)
    assert profile.loc[0, "mean"] == pytest.approx(150)
    assert profile.loc[0, "count"] == 2
    assert profile.loc[23, "mean"] == pytest.approx(50)
    assert pd.isna(profile.loc[1, "mean"])
    assert profile.loc[1, "count"] == 0
    pd.testing.assert_frame_equal(frame, original)


def test_weekly_profile_crosses_utc_day_and_orders_monday_before_sunday():
    frame = observations(["2026-01-05T02:00Z", "2026-01-05T03:00Z"], [20., 40.])
    result = weekly_profile(frame)
    assert result.index.tolist() == [0, 6]
    assert result.loc[0, "mean"] == 40
    assert result.loc[6, "mean"] == 20
    assert weekly_profile(frame, "UTC").index.tolist() == [0]


def test_profiles_keep_years_and_local_months_distinct():
    frame = observations(["2024-02-01T02:00Z", "2025-01-01T03:00Z", "2026-01-01T03:00Z"], [10., 20., 30.])
    monthly = monthly_profile(frame)
    assert monthly["month"].tolist() == ["2024-01", "2025-01", "2026-01"]
    assert monthly["year"].tolist() == [2024, 2025, 2026]
    assert monthly["mean"].tolist() == [10., 20., 30.]


def test_empty_profiles_preserve_schema_and_never_report_zero_mean():
    empty = pd.DataFrame()
    daily = daily_profile(empty)
    assert len(daily) == 24
    assert daily["mean"].isna().all()
    assert daily["count"].eq(0).all()
    assert weekly_profile(empty).empty
    assert monthly_profile(empty).empty


def test_profile_mean_handles_large_finite_values():
    frame = observations(["2026-01-01T03:00Z", "2026-01-02T03:00Z"], [1e308, 1e308])
    assert daily_profile(frame).loc[0, "mean"] == pytest.approx(1e308)


def weather_frame():
    return pd.DataFrame({
        "timestamp": pd.to_datetime(["2026-01-01T00:00Z", "2026-01-01T00:00Z", "2026-01-01T01:30Z", "2026-01-01T00:00Z"], utc=True),
        "temperature_c": [20., 30., 99., 999.], "station": ["S1", "S2", "S1", "B1"],
        "region": ["A", "A", "A", "B"],
    })


def test_weather_join_is_exact_and_mean_between_stations_is_identified():
    frame = observations(["2025-12-31T21:00-03:00", "2026-01-01T01:00Z"], [100., 200.])
    result = join_weather(frame, weather_frame(), "A")
    assert len(result) == 1
    assert result.iloc[0]["temperature_c"] == pytest.approx(25)
    assert result.iloc[0]["observed_load"] == 100
    assert result.iloc[0]["station"] == "Média das estações disponíveis"


def test_weather_station_selection_does_not_average_others():
    frame = observations(["2026-01-01T00:00Z"], [100.])
    result = join_weather(frame, weather_frame(), "A", "S2")
    assert result["temperature_c"].tolist() == [30.]
    assert result["station"].tolist() == ["S2"]
    assert join_weather(frame, weather_frame(), "A", "missing").empty


def test_weather_rejects_duplicates_instead_of_multiplying_loads():
    frame = observations(["2026-01-01T00:00Z"], [100.])
    weather = weather_frame()
    with pytest.raises(ValueError, match="duplicadas"):
        join_weather(frame, pd.concat([weather, weather.iloc[[0]]]), "A")
    with pytest.raises(ValueError, match="duplicadas"):
        join_weather(pd.concat([frame, frame]), weather, "A")


def test_empty_weather_join_preserves_columns():
    assert join_weather(pd.DataFrame(), pd.DataFrame(), "A").columns.tolist() == ["timestamp", "observed_load", "temperature_c", "station"]


def test_calendar_uses_local_date_and_keeps_scopes_separate():
    frame = observations(["2026-01-05T02:00Z", "2026-01-05T03:00Z", "2026-01-06T03:00Z"], [50., 100., 200.])
    calendar = pd.DataFrame({
        "date": [date(2026, 1, 4), date(2026, 1, 5), date(2026, 1, 6)],
        "region": ["A", "A", "A"], "day_type": ["fim_de_semana", "feriado", "ponto_facultativo"],
        "holiday_scope": ["nenhum", "municipal", "estadual"], "event_name": ["", "Sintético", "Sintético"],
    })
    profile = calendar_profile(frame, calendar, "A")
    sunday = profile.loc[profile.day_type.eq("fim_de_semana")].iloc[0]
    assert sunday["hour"] == 23 and sunday["mean"] == 50
    assert set(profile.holiday_scope) == {"nenhum", "municipal", "estadual"}
    assert profile["count"].sum() == 3


def test_missing_calendar_is_unknown_not_an_invented_workday_or_holiday():
    frame = observations(["2026-01-05T03:00Z"], [100.])
    profile = calendar_profile(frame, pd.DataFrame(), "A")
    assert profile.day_type.tolist() == ["nao_informado"]
    assert profile.holiday_scope.tolist() == ["nao_informado"]


@pytest.mark.parametrize("dates", [
    [date(2026, 1, 5), date(2026, 1, 5)],
    [date(2026, 1, 5), pd.Timestamp("2026-01-05T23:59:00")],
])
def test_duplicate_calendar_classifications_are_rejected_after_local_date_cast(dates):
    frame = observations(["2026-01-05T03:00Z"], [100.])
    calendar = pd.DataFrame({
        "date": dates, "region": ["A"] * 2, "day_type": ["feriado"] * 2,
        "holiday_scope": ["nacional"] * 2, "event_name": ["Evento1", "Evento2"],
    })
    with pytest.raises(ValueError, match="duplicadas"):
        calendar_profile(frame, calendar, "A")


def paired_frame(timestamps, loads=None, temperatures=None):
    return pd.DataFrame({
        "timestamp": pd.to_datetime(timestamps, utc=True),
        "observed_load": [100.] * len(timestamps) if loads is None else loads,
        "temperature_c": [20.] * len(timestamps) if temperatures is None else temperatures,
        "station": "Estação de teste",
    })


def test_daily_visual_means_use_same_valid_pairs_and_keep_empty_days_nan():
    frame = paired_frame(
        ["2026-03-01T03:00Z", "2026-03-01T05:00Z", "2026-03-01T06:00Z", "2026-03-01T07:00Z", "2026-03-03T03:00Z"],
        [100., 300., 1000., None, 500.], [10., 30., None, 100., 50.],
    )
    original = frame.copy(deep=True)
    daily = aggregate_load_temperature(frame, "daily")
    assert daily.n_pairs.tolist() == [2, 0, 1]
    assert daily.expected_hours.tolist() == [24., 24., 24.]
    assert daily.observed_load.iloc[0] == pytest.approx(200.)
    assert daily.temperature_c.iloc[0] == pytest.approx(20.)
    assert pd.isna(daily.observed_load.iloc[1]) and pd.isna(daily.temperature_c.iloc[1])
    assert daily.timestamp.iloc[0] == pd.Timestamp("2026-03-01T03:00Z")
    assert daily.period_end.iloc[0] == pd.Timestamp("2026-03-02T03:00Z")
    assert daily.n_pairs.sum() == 3
    pd.testing.assert_frame_equal(frame, original)


def test_weekly_visual_bins_begin_monday_in_local_timezone():
    frame = paired_frame(["2026-01-05T02:00Z", "2026-01-05T03:00Z"], [100., 200.])
    weekly = aggregate_load_temperature(frame, "weekly")
    assert weekly.timestamp.tolist() == [pd.Timestamp("2025-12-29T03:00Z"), pd.Timestamp("2026-01-05T03:00Z")]
    assert weekly.period_end.tolist() == [pd.Timestamp("2026-01-05T03:00Z"), pd.Timestamp("2026-01-12T03:00Z")]
    assert weekly.n_pairs.tolist() == [1, 1]
    assert weekly.expected_hours.tolist() == [168., 168.]
    assert weekly.observed_load.tolist() == [100., 200.]


@pytest.mark.parametrize("frequency,start,stop,hours", [
    ("daily", "2026-03-08", "2026-03-09", 23),
    ("daily", "2026-11-01", "2026-11-02", 25),
    ("weekly", "2026-03-02", "2026-03-09", 167),
    ("weekly", "2026-10-26", "2026-11-02", 169),
])
def test_visual_period_counts_respect_dst_boundaries(frequency, start, stop, hours):
    first = pd.Timestamp(start, tz="America/New_York").tz_convert("UTC")
    end = pd.Timestamp(stop, tz="America/New_York").tz_convert("UTC")
    frame = paired_frame(pd.date_range(first, periods=hours, freq="h"))
    result = aggregate_load_temperature(frame, frequency, "America/New_York")
    assert len(result) == 1
    assert result.timestamp.iloc[0] == first
    assert result.period_end.iloc[0] == end
    assert result.n_pairs.iloc[0] == hours
    assert result.expected_hours.iloc[0] == hours
    assert result.observed_load.iloc[0] == pytest.approx(100)


def test_hourly_visual_view_preserves_timestamps_and_never_completes_pairs():
    frame = paired_frame(["2026-01-01T03:00Z", "2026-01-01T05:00Z"], [100., 200.], [20., None])
    result = aggregate_load_temperature(frame)
    assert result.timestamp.tolist() == frame.timestamp.tolist()
    assert result.n_pairs.tolist() == [1, 0]
    assert pd.isna(result.observed_load.iloc[1]) and pd.isna(result.temperature_c.iloc[1])
    assert len(result) == len(frame)


def test_visual_aggregation_rejects_duplicate_instants_naive_times_and_unknown_frequency():
    frame = paired_frame(["2026-01-01T03:00Z"])
    with pytest.raises(ValueError, match="único par"):
        aggregate_load_temperature(pd.concat([frame, frame]))
    naive = frame.copy()
    naive["timestamp"] = naive["timestamp"].dt.tz_localize(None)
    with pytest.raises(ValueError, match="fuso"):
        aggregate_load_temperature(naive)
    with pytest.raises(ValueError, match="Frequência"):
        aggregate_load_temperature(frame, "monthly")


def test_empty_visual_aggregation_keeps_typed_time_columns():
    result = aggregate_load_temperature(pd.DataFrame(), "weekly")
    assert result.empty
    assert {"timestamp", "period_end", "n_pairs", "expected_hours", "observed_load", "temperature_c", "station"} == set(result.columns)
    assert str(result.timestamp.dtype) == "datetime64[ns, UTC]"


def test_visual_means_handle_large_finite_loads_without_changing_hourly_source():
    frame = paired_frame(["2026-01-01T03:00Z", "2026-01-01T04:00Z"], [1e308, 1e308])
    result = aggregate_load_temperature(frame, "daily")
    assert result.observed_load.iloc[0] == pytest.approx(1e308)
    assert result.n_pairs.iloc[0] == 2
