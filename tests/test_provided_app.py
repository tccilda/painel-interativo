"""UI do modo fornecido usando somente fixtures sintéticas do repositório.

Nenhum teste lê painel.zip ou arquivos particulares do grupo. As tabelas longas
e os resumos abaixo simulam os contratos de integração, não resultados reais.
"""

from dataclasses import replace
import json
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from services.analysis_service import build_evaluation_rows
from services.data_loader import DataBundle, load_data
from services.geography_service import KNOWN_REGIONAL_ARCHIVE_SHA256, TARGET_REGION


ROOT = Path(__file__).resolve().parents[1]
REGION = TARGET_REGION


def build_provided_fixture() -> DataBundle:
    """Dois horizontes em teste/forecast e validação somente agregada."""
    demo = load_data("demo", ROOT / "data")
    observations = demo.observations.assign(region=REGION)
    # O cenário continua artificial. Um único código municipal de estação
    # exercita o contrato geográfico, sem atribuir medições reais à fixture.
    first_station = demo.weather["station"].iloc[0]
    weather = demo.weather.loc[demo.weather["station"].eq(first_station)].assign(region=REGION, station="A621")
    calendar = demo.calendar.assign(region=REGION)
    runs = []
    for split in ("test_2025", "forecast_2026"):
        for horizon in (24, 48):
            # Escolhe um forecast de 2026 coberto pelo histórico, sem o último
            # cenário demonstrativo cujo alvo ainda não tem observado.
            source = min(
                (forecast for forecast in demo.forecasts
                 if forecast.dataset_split == split and forecast.horizon_hours == horizon),
                key=lambda forecast: forecast.issued_at,
            )
            runs.append(replace(
                source, model_name="integrado_24h" if horizon == 24 else "modelo_integrado_48h",
                model_version="não informada", region=REGION,
                source_path=Path(f"fixture/previsoes_{horizon}h_2025_2026.csv"),
            ))
    rows = build_evaluation_rows(runs, observations, weather, calendar, region=REGION, unit="MWmed")
    rows["source_file"] = rows["horizon_hours"].map(lambda value: f"fixture/previsoes_{value}h_2025_2026.csv")
    rows["issued_at_original"] = rows["issued_at"].dt.tz_convert("America/Sao_Paulo").dt.strftime("%Y-%m-%d %H:%M:%S")
    reported = []
    for horizon in (24, 48):
        segments = ["1-24h"] if horizon == 24 else ["1-24h", "25-48h", "1-48h"]
        for segment in segments:
            for method, model in (
                ("Modelo", "integrado_24h" if horizon == 24 else "modelo_integrado_48h"),
                ("Persistência", "baseline_persistencia"),
                ("Sazonal semanal", "baseline_sazonal_semanal"),
            ):
                # Números artificiais apenas para verificar a apresentação de
                # métricas reportadas sem fabricar curvas de validação.
                reported.append({
                    "etapa": "validacao_1s_2025", "modelo": model,
                    "bloco_horas": segment, "mae_mwmed": 10., "rmse_mwmed": 12., "mape_pct": 1.,
                    "n_origens": 2, "n_pares": 96 if segment == "1-48h" else 48,
                    "source_file": f"fixture/resumo_metricas_{horizon}h.csv",
                })
    return DataBundle(
        mode="provided", forecasts=[], observations=observations, issues=[], weather=weather, calendar=calendar,
        prediction_rows=rows, reported_metrics=pd.DataFrame(reported),
        provenance={"source": "Fixture municipal de contrato; somente dados sintéticos do repositório"},
    )


@pytest.fixture(autouse=True)
def refuse_personal_archive_access(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Os AppTests fornecidos não podem ler o ZIP pessoal do usuário.")
    monkeypatch.setattr("services.archive_loader.load_archive_bundle", forbidden)


def render_provided_page(module: str, horizon: int = 24, archive_hash: str | None = None) -> AppTest:
    script = f'''
import streamlit as st
from components.sidebar import SidebarSettings
from services.forecast_catalog import forecast_catalog
from tests.test_provided_app import REGION, build_provided_fixture
from app_pages.{module} import render
st.set_page_config(layout="wide")
bundle = build_provided_fixture()
archive_hash = {archive_hash!r}
if archive_hash is not None:
    bundle.provenance["archive_sha256"] = archive_hash
st.session_state["data_bundle"] = bundle
st.session_state["forecast_catalog"] = forecast_catalog(bundle)
st.session_state["original_observations"] = bundle.observations.copy(deep=True)
st.session_state["original_prediction_rows"] = bundle.prediction_rows.copy(deep=True)
st.session_state["original_reported_metrics"] = bundle.reported_metrics.copy(deep=True)
st.session_state["app_settings"] = SidebarSettings("provided", {horizon}, REGION, unit="MWmed")
if "selected_horizon" not in st.session_state:
    st.session_state["selected_horizon"] = {horizon}
render()
'''
    return AppTest.from_string(script).run(timeout=60)


@pytest.mark.parametrize("horizon", [24, 48])
def test_provided_explorer_materializes_selected_horizon_and_calculates_available_mae(horizon):
    page = render_provided_page("explorador", horizon)
    assert not page.exception
    assert not page.error
    assert not any("Modo demonstração" in item.value for item in page.warning)
    errors = [metric for metric in page.metric if metric.label == "MAE da emissão"]
    assert len(errors) == 1
    assert errors[0].value != "N/D" and "MWmed" in errors[0].value
    forecasts = [table.value for table in page.dataframe if "Previsto (MWmed)" in table.value.columns]
    assert len(forecasts) == 1 and len(forecasts[0]) == horizon
    assert page.get("download_button")
    assert len(page.get("plotly_chart")) == 1


def test_provided_performance_keeps_summary_only_validation_separate_from_test_curves():
    page = render_provided_page("desempenho")
    assert not page.exception
    assert not page.error
    assert not any("Modo demonstração" in item.value for item in page.warning)
    assert page.selectbox(key="performance_split_provided").value == "test_2025"
    summary = page.dataframe[0].value
    assert len(summary) == 6
    assert summary["Origem"].eq("Calculado").all()
    assert page.get("plotly_chart")
    worst = [table.value for table in page.dataframe if "Erro absoluto (MWmed)" in table.value.columns]
    assert len(worst) == 1 and 0 < len(worst[0]) <= 30
    assert worst[0]["Real (MWmed)"].notna().all()

    page.selectbox(key="performance_split_provided").set_value("validation_2025").run(timeout=60)
    assert not page.exception
    assert not page.error
    validation = page.dataframe[0].value
    assert validation["Origem"].eq("Resumo").all()
    assert validation["MAE (MWmed)"].eq(10.).all()
    assert any("pareamento ponto a ponto não foi verificado" in item.value for item in page.warning)
    assert not page.get("plotly_chart")
    assert any("Sem previsões individuais" in item.value for item in page.info)
    assert len(page.dataframe) == 2

    page.selectbox(key="performance_split_provided").set_value("test_2025").run(timeout=60)
    assert not page.exception
    assert not page.error
    assert page.get("plotly_chart")
    worst = [table.value for table in page.dataframe if "Erro absoluto (MWmed)" in table.value.columns]
    assert len(worst) == 1 and 0 < len(worst[0]) <= 30
    assert worst[0]["Real (MWmed)"].notna().all()
    assert page.get("download_button")


def test_provided_seasonality_displays_weather_and_calendar_without_demo_banner():
    page = render_provided_page("sazonalidade")
    assert not page.exception
    assert not page.error
    assert not any("Modo demonstração" in item.value for item in page.warning)
    assert set(page.multiselect[0].value) == {2024, 2025, 2026}
    charts = [json.loads(chart.proto.spec) for chart in page.get("plotly_chart")]
    assert len(charts) == 8
    annual = next(spec for spec in charts if spec["layout"].get("title", {}).get("text")
                  == "Média anual no período selecionado")
    assert annual["data"][0]["x"] == ["2024", "2025", "2026"]
    scatter = next(spec for spec in charts if spec["data"][0]["type"] == "scattergl")
    assert len(scatter["data"][0]["customdata"]) > 0


@pytest.mark.parametrize("module", ["explorador", "desempenho", "sazonalidade"])
def test_known_regional_archive_is_blocked_before_any_municipal_analysis_without_mutating_input(module):
    page = render_provided_page(module, archive_hash=KNOWN_REGIONAL_ARCHIVE_SHA256)
    assert not page.exception
    assert any("incompatível com o recorte municipal" in item.value for item in page.error)
    assert any("Sudeste/Centro-Oeste" in item.value for item in page.error)
    assert not page.metric
    assert not page.dataframe
    assert not page.get("plotly_chart")
    assert not page.get("download_button")
    original = page.session_state["data_bundle"]
    assert not original.observations.empty and not original.prediction_rows.empty and not original.reported_metrics.empty
    pd.testing.assert_frame_equal(original.observations, page.session_state["original_observations"])
    pd.testing.assert_frame_equal(original.prediction_rows, page.session_state["original_prediction_rows"])
    pd.testing.assert_frame_equal(original.reported_metrics, page.session_state["original_reported_metrics"])
