"""Valida os resultados derivados usando as chaves científicas e a amostra pública."""

import json

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from services import model_versions as versions
from services.scientific_results import (
    ISSUE_COLUMNS, SCENARIOS, common_issue_metrics, issue_frame, new_year_issue,
    percent_delta, reference_metrics, scope_rows, time_sensitivity,
)


@pytest.fixture(scope="module")
def global_metrics():
    return versions.metric_tables(str(versions.root()))["globais"]


@pytest.mark.parametrize(("horizon", "expected", "pairs"), [
    (24, [1080.642989, 2022.868259, 5508.190076], 104760),
    (48, [1262.653717, 2025.189851, 5853.314444], 209520),
])
def test_reference_results_use_original_compatible_aggregates(global_metrics, horizon, expected, pairs):
    model = scope_rows(global_metrics, versao="v5", modelo="ols_estabilizado", cenario=SCENARIOS[1],
                       etapa="teste_2025", horizonte_h=horizon, bloco_horas=f"1–{horizon} h").iloc[0]
    rows = reference_metrics(global_metrics, model)
    assert rows["mae_mwmed"].tolist() == pytest.approx(expected)
    assert rows["n_pares"].tolist() == [pairs] * 3
    assert rows["reducao_pct"].iloc[1:].tolist() == pytest.approx(
        [100 * (reference - expected[0]) / reference for reference in expected[1:]]
    )


@pytest.mark.parametrize(("delta", "base", "expected"), [
    (5, 10, 50), (-1, 10, -10), (0, 10, 0), (1, 0, None), (None, 3, None),
    (2, float("nan"), None), (float("inf"), 5, None),
])
def test_signed_percentage(delta, base, expected):
    assert percent_delta(delta, base) == expected


def test_reference_selection_preserves_missing_and_signed_results(global_metrics):
    frame = global_metrics.copy()
    scope = {"versao": "v5", "cenario": SCENARIOS[1], "etapa": "teste_2025",
             "horizonte_h": 48, "bloco_horas": "25–48 h"}
    rows = scope_rows(frame, **scope)
    model = rows.loc[rows.modelo.eq("ols_estabilizado")].iloc[0]
    seasonal = rows.loc[rows.modelo.eq("sazonal_semanal")].index
    persistence = rows.loc[rows.modelo.eq("persistencia")].index
    frame.loc[seasonal, "mae_mwmed"] = model["mae_mwmed"] / 2
    frame.loc[persistence, "unidade"] = "MW"
    results = reference_metrics(frame, model)
    assert results.at["sazonal_semanal", "reducao_pct"] == -100
    assert pd.isna(results.at["persistencia", "mae_mwmed"])
    assert pd.isna(results.at["persistencia", "reducao_pct"])
    frame.loc[seasonal, "mae_mwmed"] = 0
    assert pd.isna(reference_metrics(frame, model).at["sazonal_semanal", "reducao_pct"])


def test_time_sensitivity_compares_same_estimator_by_scope(global_metrics):
    selected = scope_rows(global_metrics, versao="v5", modelo="ols_estabilizado", cenario=SCENARIOS[0],
                          etapa="teste_2025", horizonte_h=24, bloco_horas="1–24 h").iloc[0]
    table, counts = time_sensitivity(global_metrics, selected)
    assert table["Indicador"].tolist() == list(versions.METRICS.values())
    assert counts.tolist() == [104760, 104760]
    assert table.loc[0, "São Paulo"] == pytest.approx(1080.642989)
    assert table.loc[0, "São Paulo − UTC"] == pytest.approx(-5.28, abs=0.01)
    assert table.loc[0, "Magnitude da diferença"] == abs(table.loc[0, "São Paulo − UTC"])
    assert table.loc[0, "Variação relativa (%)"] == pytest.approx(-0.486, abs=0.01)
    table, counts = time_sensitivity(global_metrics.loc[global_metrics.cenario.ne(SCENARIOS[1])], selected)
    assert pd.isna(counts.iloc[1]) and table["Variação relativa (%)"].isna().all()


@pytest.mark.parametrize(("scenario", "horizon", "mae", "worst_step"), [
    (SCENARIOS[0], 24, 2340.2350, 10), (SCENARIOS[1], 24, 1828.4911, 13),
    (SCENARIOS[0], 48, 3196.5415, 34), (SCENARIOS[1], 48, 2529.1311, 37),
])
def test_new_year_uses_exact_manifest_issue_and_common_targets(monkeypatch, tmp_path, scenario, horizon, mae, worst_step):
    monkeypatch.setenv("ENERGY_FORECAST_DETAIL_DIR", str(tmp_path))
    monkeypatch.setenv("ENERGY_FORECAST_DETAIL_URL", "")
    issued, detail = new_year_issue(scenario, horizon)
    assert issued.tz_convert(versions.TZ).strftime("%Y-%m-%d %H:%M") == "2026-01-01 00:00"
    future = issue_frame(detail, as_of=pd.Timestamp("2026-02-01T00:00Z"))
    common, metrics = common_issue_metrics(future, ISSUE_COLUMNS)
    assert len(common) == horizon
    assert {r["mape_valid_pairs"] for r in metrics.values()} == {horizon}
    assert metrics["ols_estabilizado"]["mae"] == pytest.approx(mae, abs=0.0001)
    worst = common.loc[common.predicted_load.sub(common.observed_load).abs().idxmax()]
    assert worst["passo_h"] == worst_step
    assert detail["evento_versao_ids"].str.contains("EV-20260101").any()
    assert metrics["sazonal_semanal"]["mae"] < metrics["ols_estabilizado"]["mae"]


def test_science_views_follow_performance_controls_and_load_case_on_demand(monkeypatch, tmp_path):
    monkeypatch.setenv("ENERGY_FORECAST_DETAIL_DIR", str(tmp_path))
    monkeypatch.setenv("ENERGY_FORECAST_DETAIL_URL", "")
    app = AppTest.from_string(
        "from components.model_versions_views import render_evolution; render_evolution()", default_timeout=60
    ).run()
    app.selectbox(key="evolution_scenario").set_value(SCENARIOS[1]).run()
    assert not app.exception
    assert [card.value for card in app.metric] == ["1.080,64 MWmed", "2.022,87 MWmed", "5.508,19 MWmed"]
    assert [card.delta for card in app.metric[1:]] == ["46,58% · redução do MAE", "80,38% · redução do MAE"]
    assert any("104.760 pares" in item.value for item in app.caption)
    chart = json.loads(app.get("plotly_chart")[0].proto.spec)
    assert chart["data"][0]["type"] == "bar" and chart["layout"]["yaxis"]["range"][0] == 0
    sensitivity = next(box for box in app.expander if box.label == "Sensibilidade à hipótese de horário")
    assert sensitivity.dataframe[0].value["São Paulo"].iloc[0] == "1.080,6430"
    app.radio(key="evolution_horizon").set_value(48).run()
    assert app.metric[0].value == "1.262,65 MWmed"
    assert [card.delta for card in app.metric[1:]] == ["37,65% · redução do MAE", "78,43% · redução do MAE"]
    assert len(next(box for box in app.expander if "Estudo de caso" in box.label).get("plotly_chart")) == 0

    app.toggle(key="science_load_new_year").set_value(True).run()
    app.selectbox(key="science_case_scenario").set_value(SCENARIOS[0]).run()
    case = next(box for box in app.expander if "Estudo de caso" in box.label)
    assert not app.exception
    assert case.dataframe[0].value["MAE da emissão (MWmed)"].iloc[0] == "3.196,54"
    assert case.dataframe[0].value["Pares no recorte"].iloc[0] == "347.760"
    assert any("passo **34**" in row.value and "02/01/2026 às 10:00" in row.value for row in case.markdown)
    plot = json.loads(case.get("plotly_chart")[0].proto.spec)
    assert {trace["name"] for trace in plot["data"]} == {"Histórico", "Previsto", "Real", "Semana anterior", "Persistência"}



def test_visible_reduction_preserves_negative_sign_and_unavailable_reference(monkeypatch):
    from components import scientific_results

    table = pd.DataFrame(
        {"mae_mwmed": [12.0, 10.0, None], "n_pares": [100, 100, None], "reducao_pct": [None, -20.0, None]},
        index=["ols_estabilizado", "sazonal_semanal", "persistencia"],
    )
    monkeypatch.setattr(scientific_results, "reference_metrics", lambda frame, selected: table)
    app = AppTest.from_string(
        "from components.scientific_results import render_headline\n"
        "render_headline(None, dict(versao='v5', modelo='ols_estabilizado', horizonte_h=24, "
        "bloco_horas='1–24 h', etapa='teste_2025', cenario='hipotese_UTC', alvo_id='ONS_SECO_piloto'))"
    ).run()
    assert not app.exception
    assert app.metric[1].delta == "-20,00% · redução do MAE"
    assert app.metric[2].value == "N/D"
    assert app.metric[2].delta == "N/D · redução do MAE"
