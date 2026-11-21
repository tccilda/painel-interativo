"""Integração real Streamlit das três abas, isolada dos arquivos de pesquisa."""

import json
from datetime import timedelta
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from services import data_loader
from components.metrics_cards import format_number
from services.geography_service import TARGET_REGION


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def isolate_real_files(tmp_path, monkeypatch):
    original_loader = data_loader.load_data
    for directory in ("historical", "predictions", "weather", "calendar"):
        (tmp_path / directory).mkdir()

    def load_isolated(mode):
        return original_loader(mode, tmp_path) if mode == "real" else original_loader(mode)

    monkeypatch.setattr(data_loader, "load_data", load_isolated)
    monkeypatch.setattr(data_loader, "DATA_DIR", tmp_path)
    return tmp_path


def render_page(module: str, mode: str = "demo", horizon: int = 24) -> AppTest:
    script = f'''
import streamlit as st
from components.sidebar import SidebarSettings
from services.data_loader import load_data
from app_pages.{module} import render
st.set_page_config(layout="wide")
bundle = load_data({mode!r})
region = bundle.forecasts[0].region if bundle.forecasts else (bundle.observations["region"].iloc[0] if not bundle.observations.empty else None)
unit = bundle.forecasts[0].unit if bundle.forecasts else (bundle.observations["unit"].iloc[0] if not bundle.observations.empty else "MWmed")
st.session_state["data_bundle"] = bundle
st.session_state["app_settings"] = SidebarSettings({mode!r}, {horizon}, region, unit=unit)
st.session_state["selected_horizon"] = {horizon}
render()
'''
    return AppTest.from_string(script).run(timeout=60)


def test_entrypoint_horizon_and_source_switch(monkeypatch):
    monkeypatch.delenv("ENERGY_FORECAST_ALLOW_DEMO", raising=False)
    app = AppTest.from_file(ROOT / "streamlit_app.py").run(timeout=60)
    assert not app.exception
    assert app.title[0].value == "Monitor de Previsão"
    assert any(item.value == "*Painel Interativo de Previsão de Demanda Energética*" for item in app.markdown)
    assert app.header[0].value == "Explorador de Previsões"
    assert all(widget.label != "Fonte" for widget in app.selectbox)
    assert not any("Modo demonstração" in item.value for item in app.warning)
    assert not app.metric
    assert not app.dataframe
    assert not app.get("plotly_chart")
    assert any("Nenhuma previsão" in item.value for item in app.info)
    monkeypatch.setenv("ENERGY_FORECAST_ALLOW_DEMO", "true")
    app.run(timeout=60)
    app.selectbox(key="source_mode").set_value("Demonstração").run(timeout=60)
    assert not app.exception
    assert any("Modo demonstração" in item.value for item in app.warning)
    assert len(app.dataframe[0].value) == 24
    app.radio[0].set_value(48).run(timeout=60)
    assert not app.exception
    assert len(app.dataframe[0].value) == 48
    app.selectbox(key="source_mode").set_value("Arquivos dos modelos").run(timeout=60)
    assert not app.exception
    assert not app.metric
    assert any("Nenhuma previsão" in item.value for item in app.info)


@pytest.mark.parametrize("has_imported,expected", [(False, "Arquivos dos modelos"), (True, "Base do grupo (CSV)")])
def test_source_selector_defaults_to_real_and_resets_stale_demo_session(has_imported, expected):
    script = f'''
import streamlit as st
from components.sidebar import select_data_mode
st.session_state["selected_source_result"] = select_data_mode(has_imported={has_imported!r})
'''
    page = AppTest.from_string(script)
    page.session_state["source_mode"] = "Demonstração"
    page.run(timeout=60)
    assert not page.exception
    if has_imported:
        assert page.selectbox(key="source_mode").value == expected
        assert "Demonstração" not in page.selectbox(key="source_mode").options
    else:
        assert not page.selectbox
    assert page.session_state["selected_source_result"] == ("provided" if has_imported else "real")


def test_source_selector_allows_demo_only_when_explicitly_enabled_and_revokes_it_safely():
    script = '''
import streamlit as st
from components.sidebar import select_data_mode
allow_demo = st.checkbox("Habilitação local explícita", value=True)
st.session_state["selected_source_result"] = select_data_mode(allow_demo=allow_demo)
'''
    page = AppTest.from_string(script).run(timeout=60)
    assert page.selectbox(key="source_mode").value == "Arquivos dos modelos"
    page.selectbox(key="source_mode").set_value("Demonstração").run(timeout=60)
    assert page.session_state["selected_source_result"] == "demo"
    page.checkbox[0].set_value(False).run(timeout=60)
    assert not page.exception
    assert not page.selectbox
    assert page.session_state["selected_source_result"] == "real"


@pytest.mark.parametrize("horizon", [24, 48])
def test_explorer_has_full_horizon_and_no_invented_error(horizon):
    page = render_page("explorador", horizon=horizon)
    assert not page.exception
    assert len(page.dataframe[0].value) == horizon
    assert page.get("download_button")
    assert next(metric for metric in page.metric if metric.label == "MAE da emissão").value == "N/D"
    _assert_peak_matches_hourly_table(page)
    assert page.get("plotly_chart")
    page.selectbox(key="explorer_split_demo").set_value("test_2025").run(timeout=60)
    assert not page.exception
    _assert_peak_matches_hourly_table(page)
    table = page.dataframe[0].value
    target = pd.to_datetime(table["Hora prevista"], format="%d/%m/%Y %H:%M %z", utc=True)
    actual = page.session_state["data_bundle"].observations.set_index("timestamp")["observed_load"].reindex(target)
    assert actual.notna().all()
    expected_mae = abs(actual.to_numpy() - table["Previsto (MWmed)"].to_numpy()).mean()
    assert next(metric for metric in page.metric if metric.label == "MAE da emissão").value == f"{format_number(expected_mae, 2)} MWmed"


def _assert_peak_matches_hourly_table(page):
    table = page.dataframe[0].value
    peak_index = table["Previsto (MWmed)"].idxmax()
    assert next(metric for metric in page.metric if metric.label == "Pico previsto").value == f"{format_number(table.loc[peak_index, 'Previsto (MWmed)'])} MWmed"
    peak_time = pd.to_datetime(table.loc[peak_index, "Hora prevista"], format="%d/%m/%Y %H:%M %z")
    assert next(metric for metric in page.metric if metric.label == "Horário do pico").value == peak_time.strftime("%H:%M · %d/%m")


def plot_specs(page):
    return [json.loads(chart.proto.spec) for chart in page.get("plotly_chart")]


def test_performance_compares_splits_segments_and_references():
    page = render_page("desempenho")
    assert not page.exception
    summary = page.dataframe[0].value
    assert len(summary) == 6
    assert sum(summary["Modelo / janela"].str.startswith("Modelo")) == 4
    assert any(summary["Modelo / janela"].str.startswith("Persistência"))
    assert any(summary["Modelo / janela"].str.startswith("Sazonal semanal"))
    assert summary[["MAE (MWmed)", "RMSE (MWmed)", "MAPE (%)"]].notna().all().all()
    assert summary["Origem"].eq("Sintético").all()
    assert any("Modo demonstração" in item.value for item in page.warning)
    assert page.get("plotly_chart")
    assert len(page.dataframe[-1].value) <= 30
    assert page.selectbox(key="performance_split_demo").value == "test_2025"
    for metric, unit in (("RMSE", "MWmed"), ("MAPE", "%")):
        page.radio(key="degradation_metric").set_value(metric).run(timeout=60)
        assert not page.exception
        assert plot_specs(page)[0]["layout"]["yaxis"]["title"]["text"] == f"{metric} ({unit})"
    page.selectbox(key="performance_split_demo").set_value("forecast_2026").run(timeout=60)
    assert not page.exception
    assert len(page.dataframe[0].value) == 6


def test_seasonality_includes_weather_calendar_and_three_years():
    page = render_page("sazonalidade")
    assert not page.exception
    assert set(page.multiselect[0].value) == {2024, 2025, 2026}
    assert len(page.get("plotly_chart")) == 8
    assert not page.error


def test_climate_filters_change_only_climate_and_keep_all_scatter_pairs():
    page = render_page("sazonalidade")
    assert not page.exception
    initial = plot_specs(page)
    source_profiles = [spec["data"][0]["y"] for spec in initial[:3]]
    scatter = next(spec for spec in initial if spec["data"][0]["type"] == "scattergl")
    initial_count = len(scatter["data"][0]["customdata"])
    page.radio(key="climate_resolution_demo").set_value("hourly").run(timeout=60)
    assert not page.exception
    hourly = plot_specs(page)
    hourly_scatter = next(spec for spec in hourly if spec["data"][0]["type"] == "scattergl")
    hourly_series = next(spec for spec in hourly if "yaxis2" in spec["layout"])
    assert len(hourly_scatter["data"][0]["customdata"]) == initial_count
    assert len(hourly_series["data"][0]["y"]) <= 168
    assert [spec["data"][0]["y"] for spec in hourly[:3]] == source_profiles
    period_control = next(control for control in page.date_input if control.label == "Intervalo climático")
    last = period_control.value[-1]
    period_control.set_value((last - timedelta(days=6), last)).run(timeout=60)
    assert not page.exception
    week = plot_specs(page)
    week_scatter = next(spec for spec in week if spec["data"][0]["type"] == "scattergl")
    assert len(week_scatter["data"][0]["customdata"]) < initial_count
    page.radio(key="climate_resolution_demo").set_value("weekly").run(timeout=60)
    assert not page.exception
    weekly = next(spec for spec in plot_specs(page) if "yaxis2" in spec["layout"])
    assert len(weekly["data"][0]["y"]) <= 2
    assert "semanal" in weekly["layout"]["title"]["text"]


@pytest.mark.parametrize("module", ["explorador", "desempenho", "sazonalidade"])
def test_real_empty_pages_have_explanatory_states(module):
    page = render_page(module, mode="real")
    assert not page.exception
    assert not page.metric
    assert not page.get("plotly_chart")
    assert page.info


def test_model_files_enable_performance_without_weather_or_calendar(isolate_real_files):
    root = isolate_real_files
    payload = json.loads((ROOT / "data/demo/forecast_backtest_24h.json").read_text(encoding="utf-8"))
    payload.update(model_name="Modelo de teste", region="Município do Rio de Janeiro")
    (root / "predictions/modelo24.json").write_text(json.dumps(payload), encoding="utf-8")
    observations = pd.read_csv(ROOT / "data/demo/historical.csv")
    observations["region"] = "Município do Rio de Janeiro"
    observations.to_csv(root / "historical/observado.csv", index=False)
    page = render_page("desempenho", mode="real")
    assert not page.exception
    summary = page.dataframe[0].value
    assert summary.loc[summary["Modelo / janela"].str.startswith("Modelo 24"), "MAE (MWmed)"].notna().all()
    coverage = page.dataframe[1].value
    assert coverage["Pares"].min() == 24
    assert set(coverage["Método"]) == {"Modelo", "Persistência", "Sazonal semanal"}
    assert not any("Modo demonstração" in item.value for item in page.warning)


def test_history_only_source_excludes_future_and_keeps_climate_empty(isolate_real_files):
    path = isolate_real_files / "historical/observado.csv"
    path.write_text(
        "timestamp,observed_load,region,unit\n"
        f"2026-01-01T00:00:00Z,100.0,{TARGET_REGION},MWmed\n"
        f"2100-01-01T00:00:00Z,900.0,{TARGET_REGION},MWmed\n", encoding="utf-8",
    )
    page = render_page("sazonalidade", mode="real")
    assert not page.exception
    assert any("registros futuros" in item.value for item in page.warning)
    assert any("Sem temperatura" in item.value for item in page.info)
    assert page.multiselect[0].value == [2025]
