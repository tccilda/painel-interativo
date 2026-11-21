"""Integração com o catálogo publicado e partições mínimas descartáveis."""

from dataclasses import replace
from datetime import date, timedelta
import hashlib
from io import BytesIO
import json
from pathlib import Path
import shutil
from types import SimpleNamespace

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from components import model_versions_views as views
from components.charts import calendar_profile_chart
from services import model_versions as versions
from services.pattern_service import calendar_profile

ROOT = Path(__file__).resolve().parents[1]


def prepare_index(tmp_path, *, extra_emissions=False):
    manifest = json.loads((versions.root() / versions.V5 / "MANIFESTO_v5.json").read_text(encoding="utf-8"))
    issue = pd.Timestamp("2025-07-01T03:00:00Z")
    entries = []
    source = {}
    for horizon in (24, 48):
        name = f"previsoes_{horizon}h_v5.csv"
        source[name] = manifest["arquivos"][name]["sha256"]
        partitions = {"2025-07": [(issue, "ols_estabilizado", 40_010.0)]}
        if extra_emissions:
            partitions["2025-07"].extend([
                (pd.Timestamp("2025-07-02T03:00:00Z"), "ols_estabilizado", 41_000.0),
                (pd.Timestamp("2025-07-02T03:00:30Z"), "ols_estabilizado", 41_030.0),
                (pd.Timestamp("2025-07-01T03:00:00Z"), "piloto_so_carga", 39_500.0),
            ])
            partitions["2025-08"] = [(pd.Timestamp("2025-08-01T03:00:00Z"), "ols_estabilizado", 42_000.0)]
        for month, emissions in partitions.items():
            path = tmp_path / f"{horizon}__hipotese_UTC__teste_2025__{month}.parquet"
            frames = [pd.DataFrame({
                "modelo": model, "origem_t": stamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "passo_h": range(1, horizon + 1), "eh_selecionado": int(model == "ols_estabilizado"),
                "instante_alvo": pd.date_range(stamp + timedelta(hours=1), periods=horizon, freq="h").strftime("%Y-%m-%dT%H:%M:%SZ"),
                "y_real": 40_000.0, "y_pred": prediction, "y_baseline_semanal": 39_800.0,
                "y_baseline_persistencia": 39_900.0, "fim_de_semana": 0, "eh_feriado": 0,
                "eh_ponto_facultativo": 0, "evento_versao_ids": "[]",
            }) for stamp, model, prediction in emissions]
            pd.concat(frames, ignore_index=True).to_parquet(path, index=False)
            entries.append(dict(file=path.name, sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                                bytes=path.stat().st_size, horizon=horizon, scenario="hipotese_UTC",
                                stage="teste_2025", month=month, rows=horizon * len(emissions)))
    (tmp_path / "index.json").write_text(json.dumps({"schema": 1, "source": source, "partitions": entries}))


def with_label(widgets, label):
    return next(widget for widget in widgets if widget.label == label)


def test_v5_starts_with_exact_horizons_and_older_aggregate_only(monkeypatch, tmp_path):
    prepare_index(tmp_path)
    monkeypatch.setenv("ENERGY_FORECAST_DETAIL_DIR", str(tmp_path))
    page = AppTest.from_file(ROOT / "streamlit_app.py", default_timeout=60).run()
    assert not page.exception
    assert page.selectbox(key="catalog_explorer_version").value == "V5"
    assert len(page.dataframe[0].value) == 24
    page.radio(key="v5_explorer_horizon").set_value(48).run()
    assert not page.exception and len(page.dataframe[0].value) == 48
    assert page.selectbox(key="catalog_explorer_version").options == ["V5"]
    assert all(widget.label != "Fonte" for widget in page.selectbox)
    method = next(item for item in page.expander if item.label == "Detalhes metodológicos")
    assert any("V2–V4 têm apenas métricas agregadas" in item.value for item in method.markdown)
    assert not any("V2–V4 têm apenas métricas agregadas" in item.value for item in page.caption)


def test_metrics_use_real_row_keys_and_paired_source():
    data = versions.metric_tables(str(versions.root()))
    assert set(data["globais"]["versao"]) == {*versions.VERSIONS, "piloto"}
    assert len(data["globais"]) == 540
    assert len(data["pares"]) == 118
    app = AppTest.from_string(
        "from components.model_versions_views import render_evolution\nrender_evolution()",
        default_timeout=60,
    ).run()
    assert not app.exception
    global_table, paired = (app.dataframe[j].value for j in (0, 1))
    assert pd.isna(global_table.loc[global_table["Versão"].eq("V1"), "MAE (MWmed)"].iloc[0])
    assert paired["n_pares_comuns"].tolist() == [104760]
    assert json.loads(app.dataframe[1].proto.columns)["n_pares_comuns"]["label"] == "Pares comuns"
    assert paired["delta_mae_mwmed"].iloc[0] == data["pares"].loc[
        data["pares"]["cenario"].eq("hipotese_UTC") & data["pares"]["horizonte_h"].eq(24)
        & data["pares"]["etapa"].eq("teste_2025") & data["pares"]["modelo"].eq("ols_estabilizado"),
        "delta_mae_mwmed"].iloc[0]


def test_audited_calendar_uses_versioned_ids_and_separate_pending_rows():
    app = AppTest.from_string(
        "from app_pages.sazonalidade import _render_profiles\n"
        "from components.model_versions_views import render_seasonality\n"
        "render_seasonality(_render_profiles)",
        default_timeout=60,
    ).run()
    assert not app.exception and len(app.get("plotly_chart")) >= 6
    events = next(df.value for df in app.dataframe if "evento_versao_id" in df.value)
    assert events["data_local"].str.fullmatch(r"\d{2}/\d{2}/\d{4}").all()
    assert any("motivo_pendencia" in df.value for df in app.dataframe)
    note = next(box for box in app.expander if box.label == "Temperatura observada e série dos modelos V5")
    assert all(word in note.markdown[0].value for word in ("contexto", "A621", "A601", "temp_rj_c", "causal"))
    categories = next(widget for widget in app.multiselect if widget.label == "Categorias de calendário")
    assert "Ponto facultativo · Administração pública federal + Municipal" in categories.options


@pytest.mark.parametrize("scenario", ["hipotese_UTC", "hipotese_Sao_Paulo"])
def test_coexisting_calendar_acts_keep_both_scopes_and_count_each_hour_once(scenario):
    data = versions.load_scenario(str(versions.root()), scenario)
    row = SimpleNamespace(
        eh_feriado=0, eh_ponto_facultativo=1, fim_de_semana=0,
        evento_versao_ids='["EV-20250619-FED-PF-01", "EV-20250619-MRJ-PF-01"]',
    )
    kind, scopes, name = versions.classify(row, data.events)
    assert kind == "ponto_facultativo" and name == "Corpus Christi"
    assert set(scopes.split("+")) == {"federal_administracao", "municipal"}

    local = data.calendar["timestamp"].dt.tz_convert(versions.TZ)
    corpus = data.calendar.loc[local.dt.strftime("%Y-%m-%d").eq("2025-06-19")]
    assert len(corpus) == 24 and corpus["holiday_scope"].eq(scopes).all()
    assert data.calendar["holiday_scope"].eq(scopes).sum() == 96
    corpus_combined = data.calendar.loc[data.calendar["holiday_scope"].str.contains(r"\+")
                                        & data.calendar["event_name"].str.contains("Corpus Christi")]
    assert len(corpus_combined) == 120
    assert set(corpus_combined["event_name"]) == {"Corpus Christi", "Dia após Corpus Christi"}

    profile = calendar_profile(data.observations, data.calendar, versions.REGION)
    assert profile["count"].sum() == len(data.observations) == 24837
    figure = json.loads(calendar_profile_chart(profile).to_json())
    names = {trace["name"] for trace in figure["data"]}
    assert {"Facultativo · administração pública federal + municipal",
            "Feriado · administração pública federal"}.issubset(names)


def test_clean_checkout_ships_real_v5_sample(monkeypatch, tmp_path):
    monkeypatch.setenv("ENERGY_FORECAST_DETAIL_DIR", str(tmp_path))
    monkeypatch.setenv("ENERGY_FORECAST_DETAIL_URL", "")
    index = versions.detail_index()
    assert len(index) == 12 and all(item["preview"] for item in index)
    assert sum(item["rows"] for item in index) == 432
    page = AppTest.from_file(ROOT / "streamlit_app.py", default_timeout=60).run()
    assert not page.exception and len(page.dataframe[0].value) == 24
    method = next(item for item in page.expander if item.label == "Detalhes metodológicos")
    text = " ".join(item.value for item in method.markdown)
    assert all(phrase in text for phrase in (
        "12 exemplos reais", "métricas calculadas com os dados do recorte completo",
        "duas hipóteses", "UTC e São Paulo", "aparecem no horário de São Paulo",
        "informação de contexto", "A621 e A601", "até 1 h antes", "sem preencher lacunas",
        "temp_rj_c", "leitura anterior", "atos já conhecidos no momento da emissão",
    ))
    temperature = next(card for card in page.metric if card.label == "Temperatura em t₀")
    assert all(word in temperature.proto.help for word in ("contexto", "1 h", "ffill", "temp_rj_c", "causal"))
    assert any("temp_rj_c" in item.value for item in method.markdown)
    assert not any("12 exemplos reais" in item.value for item in page.caption)
    month = with_label(page.selectbox, "Mês da emissão (amostra V5)")
    assert month.options == ["07/2025"] and month.value == "2025-07"
    issue = with_label(page.selectbox, "Hora da emissão (horário de São Paulo)")
    assert issue.options == ["00:00"] and issue.value == "2025-07-01T03:00:00Z"
    details = with_label(page.expander, "Valores horários e calendário")
    assert any("Estimador exibido" in item.value and "ols_estabilizado" in item.value
               and "escolhido na avaliação" in item.value for item in details.markdown)
    assert page.selectbox(key="catalog_explorer_version").options == ["V5"]


@pytest.mark.parametrize("horizon", [24, 48])
@pytest.mark.parametrize("scenario", ["hipotese_UTC", "hipotese_Sao_Paulo"])
def test_v5_preview_uses_the_current_stage_on_every_transition(monkeypatch, tmp_path, scenario, horizon):
    monkeypatch.setenv("ENERGY_FORECAST_DETAIL_DIR", str(tmp_path))
    monkeypatch.setenv("ENERGY_FORECAST_DETAIL_URL", "")
    page = AppTest.from_file(ROOT / "streamlit_app.py", default_timeout=60).run()
    page.selectbox(key="v5_explorer_scenario").set_value(scenario)
    page.radio(key="v5_explorer_horizon").set_value(horizon).run()
    partitions = {entry["stage"]: entry for entry in versions.detail_index()
                  if (entry["scenario"], entry["horizon"]) == (scenario, horizon)}
    for stage, day in [
        ("teste_2025", "2025-07-01"), ("validacao_1s2025", "2025-01-01"),
        ("retrospectiva_2026", "2026-01-01"), ("teste_2025", "2025-07-01"),
    ]:
        page.selectbox(key="v5_explorer_stage").set_value(stage).run()
        assert not page.exception and not page.warning
        assert len(page.metric) == 4 and len(page.get("plotly_chart")) == 1
        issue = with_label(page.selectbox, "Hora da emissão (horário de São Paulo)")
        assert issue.options == ["00:00"] and issue.value == f"{day}T03:00:00Z"
        assert with_label(page.selectbox, "Data da emissão").value == date.fromisoformat(day)
        values = page.dataframe[0].value
        assert len(values) == horizon
        assert values["Alvo local"].iloc[0].startswith(f"{date.fromisoformat(day):%d/%m/%Y} 01:00")
        expected = pd.read_parquet(versions.partition_path(partitions[stage]), columns=["passo_h", "y_pred"])
        assert values["Previsto (MWmed)"].tolist() == expected.sort_values("passo_h")["y_pred"].tolist()


def test_v5_explorer_updates_month_date_and_model_in_the_same_session(monkeypatch, tmp_path):
    prepare_index(tmp_path, extra_emissions=True)
    monkeypatch.setenv("ENERGY_FORECAST_DETAIL_DIR", str(tmp_path))
    monkeypatch.setenv("ENERGY_FORECAST_DETAIL_URL", "")
    page = AppTest.from_file(ROOT / "streamlit_app.py", default_timeout=60).run()

    def assert_prediction(timestamp, prediction):
        assert not page.exception and not page.warning
        assert with_label(page.selectbox, "Hora da emissão (horário de São Paulo)").value == timestamp
        assert page.dataframe[0].value["Previsto (MWmed)"].eq(prediction).all()

    assert_prediction("2025-08-01T03:00:00Z", 42_000.0)
    with_label(page.selectbox, "Mês da emissão").set_value("2025-07").run()
    issue = with_label(page.selectbox, "Hora da emissão (horário de São Paulo)")
    assert len(set(issue.options)) == 2
    issue.set_value("2025-07-02T03:00:00Z").run()
    assert_prediction("2025-07-02T03:00:00Z", 41_000.0)
    with_label(page.selectbox, "Data da emissão").set_value(date(2025, 7, 1)).run()
    assert_prediction("2025-07-01T03:00:00Z", 40_010.0)
    assert with_label(page.selectbox, "Hora da emissão (horário de São Paulo)").options == ["00:00"]
    with_label(page.selectbox, "Estimador").set_value("piloto_so_carga").run()
    assert_prediction("2025-07-01T03:00:00Z", 39_500.0)
    assert any("piloto_so_carga" in item.value and "usado no piloto" in item.value
               for item in with_label(page.expander, "Valores horários e calendário").markdown)


@pytest.mark.parametrize("version", ["Todas", "v5"])
@pytest.mark.parametrize("stage", ["teste_2025", "retrospectiva_2026"])
def test_evolution_explains_when_24h_has_no_alternative_estimators(version, stage):
    page = AppTest.from_string(
        "from components.model_versions_views import render_evolution; render_evolution()", default_timeout=60,
    ).run()
    page.selectbox(key="evolution_version").set_value(version)
    page.selectbox(key="evolution_stage").set_value(stage)
    page.selectbox(key="evolution_role").set_value("Alternativa").run()
    assert not page.exception and not page.get("plotly_chart")
    assert any("Não há estimadores alternativos disponíveis neste recorte de 24 h" in item.value for item in page.info)
    page.selectbox(key="evolution_stage").set_value("validacao_1s2025").run()
    assert page.get("plotly_chart")
    assert not any("Não há estimadores alternativos" in item.value for item in page.info)


def test_seasonality_keeps_filters_when_switching_hypothesis(monkeypatch):
    app = AppTest.from_string(
        "from app_pages.sazonalidade import _render_profiles\n"
        "from components.model_versions_views import render_seasonality\n"
        "render_seasonality(_render_profiles)",
        default_timeout=60,
    ).run()
    analysis_period = (date(2024, 6, 1), date(2025, 9, 30))
    climate_period = (date(2025, 6, 1), date(2025, 6, 30))
    with_label(app.date_input, "Período da análise").set_value(analysis_period)
    with_label(app.multiselect, "Anos").set_value([2025]).run()
    categories = [("dia_util", "nenhum"), ("ponto_facultativo", "federal_administracao+municipal")]
    with_label(app.date_input, "Intervalo climático").set_value(climate_period)
    with_label(app.radio, "Resolução temporal").set_value("hourly")
    with_label(app.multiselect, "Categorias de calendário").set_value(categories).run()
    for scenario in ("hipotese_Sao_Paulo", "hipotese_UTC"):
        app.selectbox(key="v5_patterns_scenario").set_value(scenario).run()
        assert not app.exception
        assert with_label(app.date_input, "Período da análise").value == analysis_period
        assert with_label(app.multiselect, "Anos").value == [2025]
        assert with_label(app.date_input, "Intervalo climático").value == climate_period
        assert with_label(app.radio, "Resolução temporal").value == "hourly"
        assert with_label(app.multiselect, "Categorias de calendário").value == categories
        history = with_label(app.expander, "Histórico horário").get("plotly_chart")[0]
        assert "%Y" in json.loads(history.proto.spec)["layout"]["xaxis"]["tickformat"]

    load_scenario = versions.load_scenario
    first = date(2025, 6, 21)

    def shorter_scenario(directory, scenario):
        data = load_scenario(directory, scenario)
        timestamps = data.observations["timestamp"].dt.tz_convert(versions.TZ)
        return replace(data, observations=data.observations.loc[timestamps.dt.date.ge(first)])

    monkeypatch.setattr(versions, "load_scenario", shorter_scenario)
    app.selectbox(key="v5_patterns_scenario").set_value("hipotese_Sao_Paulo").run()
    assert not app.exception
    assert with_label(app.date_input, "Período da análise").value == (first, analysis_period[1])
    assert with_label(app.multiselect, "Anos").value == [2025]
    assert with_label(app.date_input, "Intervalo climático").value == (first, climate_period[1])
    assert with_label(app.radio, "Resolução temporal").value == "hourly"
    assert with_label(app.multiselect, "Categorias de calendário").value == categories[:1]


def test_v5_evaluation_uses_one_month_and_filters_real_episodes(monkeypatch, tmp_path):
    monkeypatch.setenv("ENERGY_FORECAST_DETAIL_DIR", str(tmp_path))
    monkeypatch.setenv("ENERGY_FORECAST_DETAIL_URL", "")
    app = AppTest.from_string(
        "from components.model_versions_views import render_evolution\nrender_evolution()", default_timeout=60,
    ).run()
    app.radio(key="evolution_horizon").set_value(48).run()
    app.selectbox(key="evolution_block").set_value("25–48 h").run()
    app.toggle(key="v5_query_episodes").set_value(True).run()
    assert not app.exception and not app.warning
    assert any("Maiores erros horários da amostra exibida" in item.value for item in app.markdown)
    assert any(all(word in item.value for word in ("episódios", "A621", "A601", "contexto", "temp_rj_c"))
               for item in app.caption)
    episodes = next(table.value for table in app.dataframe if "Erro absoluto (MWmed)" in table.value)
    assert set(episodes["Passo"]) == set(range(25, 49))
    assert episodes["Erro absoluto (MWmed)"].is_monotonic_decreasing
    pd.testing.assert_series_equal(episodes["Erro absoluto (MWmed)"],
                                  (episodes["Observado (MWmed)"] - episodes["Previsto (MWmed)"]).abs(),
                                  check_names=False)
    exports = [item.proto.label for item in app.get("download_button")]
    assert {"Exportar episódios", "Exportar métricas do recorte", "Exportar pares comuns"}.issubset(exports)
    first_month = with_label(app.selectbox, "Mês da emissão (amostra V5)")
    assert first_month.value == "2025-07"
    app.selectbox(key="evolution_stage").set_value("validacao_1s2025").run()
    next_month = with_label(app.selectbox, "Mês da emissão (amostra V5)")
    assert not app.warning and next_month.value == "2025-01"
    assert next_month.key != first_month.key
    app.selectbox(key="evolution_stage").set_value("teste_2025")
    app.selectbox(key="evolution_version").set_value("v1").run()
    assert not app.exception and app.selectbox(key="evolution_scenario").value == "sem_cenario_bruto"
    assert app.dataframe[0].value["Versão"].tolist() == ["V1"]


@pytest.mark.parametrize(("role", "stage", "horizon", "model"), [
    ("Piloto", "teste_2025", 24, "piloto_so_carga"),
    ("Alternativa", "validacao_1s2025", 24, "ridge_10"),
    ("Alternativa", "validacao_1s2025", 24, "ridge_100"),
    ("Alternativa", "validacao_1s2025", 48, "ridge_1"),
])
def test_preview_distinguishes_missing_estimator_from_missing_observations(
    monkeypatch, tmp_path, role, stage, horizon, model,
):
    monkeypatch.setenv("ENERGY_FORECAST_DETAIL_DIR", str(tmp_path))
    monkeypatch.setenv("ENERGY_FORECAST_DETAIL_URL", "")
    app = AppTest.from_string(
        "from components.model_versions_views import render_evolution; render_evolution()", default_timeout=60,
    ).run()
    app.selectbox(key="evolution_stage").set_value(stage)
    app.radio(key="evolution_horizon").set_value(horizon)
    app.selectbox(key="evolution_role").set_value(role).run()
    app.selectbox(key="evolution_model").set_value(model).run()
    app.toggle(key="v5_query_episodes").set_value(True).run()
    assert not app.exception and not app.warning
    assert any("prévia V5 não inclui previsões horárias" in item.value and model in item.value for item in app.info)
    assert not any("carga observada" in item.value for item in app.info)
    assert app.dataframe[0].value["MAE (MWmed)"].notna().any()

    app.selectbox(key="evolution_role").set_value("Selecionado")
    monkeypatch.setattr(versions, "episode_rows", lambda *args: pd.DataFrame())
    app.run()
    assert any("Nenhum par com carga observada" in item.value for item in app.info)


def test_availability_respects_catalog_dimensions_and_preserves_general_rules():
    app = AppTest.from_string(
        "from components.model_versions_views import render_evolution; render_evolution()", default_timeout=60,
    ).run()
    app.selectbox(key="evolution_version").set_value("v3")
    app.radio(key="evolution_horizon").set_value(48).run()
    app.selectbox(key="evolution_block").set_value("25–48 h").run()
    catalog = app.dataframe[-1].value
    assert set(catalog["versao"]) == {"v3"}
    assert set(catalog["bloco_horas"].dropna()) == {"25–48 h"}
    assert catalog["bloco_horas"].isna().any()
    labels = json.loads(app.dataframe[-1].proto.columns)
    assert labels["casas_decimais"]["label"].startswith("Precisão")
    assert labels["dependencia"]["label"] == "Dependência"
    assert 2 in catalog["casas_decimais"].values

    app.selectbox(key="evolution_role").set_value("Piloto").run()
    catalog = app.dataframe[-1].value
    assert set(catalog["modelo"]) == {"piloto_so_carga"}

    app.selectbox(key="evolution_version").set_value("v5").run()
    assert not app.exception
    assert any("catálogo histórico de disponibilidade" in item.value for item in app.caption)
    assert all("dependencia" not in item.value for item in app.dataframe)


def test_historical_pilot_opens_with_results_and_marks_retrospective_out_of_design():
    app = AppTest.from_string(
        "from components.model_versions_views import render_evolution; render_evolution()", default_timeout=60,
    ).run()
    app.selectbox(key="evolution_version").set_value("piloto").run()
    assert not app.exception
    role = next(widget for widget in app.selectbox if widget.label == "Grupo de estimadores")
    assert role.value == "Piloto"
    assert app.selectbox(key="evolution_scenario").options == ["Carimbo original · fuso não documentado (Piloto/V1)"]
    metrics = app.dataframe[0].value
    assert metrics["Estimador"].tolist() == ["piloto_so_carga"]
    assert metrics["MAE (MWmed)"].iloc[0] == pytest.approx(1203.71, abs=0.01)
    app.selectbox(key="evolution_stage").set_value("retrospectiva_2026").run()
    assert not app.exception and app.dataframe[0].value["MAE (MWmed)"].isna().all()
    assert any("Retrospectiva 2026 está fora do desenho" in item.value for item in app.info)
    catalog = app.dataframe[-1].value
    assert set(catalog["versao"]) == {"piloto"}
    assert set(catalog["status"]) == {"fora_do_desenho"}


@pytest.mark.parametrize(("role", "stage", "scenario", "model"), [
    ("Piloto", "teste_2025", "hipotese_UTC", "piloto_so_carga"),
    ("Referência", "validacao_1s2025", "hipotese_Sao_Paulo", "persistencia"),
])
def test_version_axis_keeps_near_equal_values_readable_and_exports_full_precision(
    monkeypatch, role, stage, scenario, model,
):
    encoded = []
    csv_bytes = views.csv_bytes

    def capture_csv(frame):
        data = csv_bytes(frame)
        encoded.append(data)
        return data

    monkeypatch.setattr(views, "csv_bytes", capture_csv)
    app = AppTest.from_string(
        "from components.model_versions_views import render_evolution; render_evolution()", default_timeout=60,
    ).run()
    axis = json.loads(app.get("plotly_chart")[0].proto.spec)["layout"]["yaxis"]
    assert "range" not in axis  # OLS com variação real conserva a escala automática.
    app.selectbox(key="evolution_role").set_value(role)
    app.selectbox(key="evolution_scenario").set_value(scenario)
    app.selectbox(key="evolution_stage").set_value(stage).run()
    encoded.clear()
    app.selectbox(key="evolution_model").set_value(model).run()
    assert not app.exception
    axis = json.loads(app.get("plotly_chart")[0].proto.spec)["layout"]["yaxis"]
    assert axis["tickformat"] == ",.2f"
    lower, upper = axis["range"]
    assert upper - lower == pytest.approx(0.1)
    values = versions.read_csv(BytesIO(encoded[0]))["mae_mwmed"]
    original = versions.metric_tables(str(versions.root()))["globais"].query(
        "cenario == @scenario and etapa == @stage and modelo == @model and horizonte_h == 24"
    )
    assert values.tolist() == original["mae_mwmed"].tolist()
    assert 0 < values.max() - values.min() < 3e-12
    assert lower < values.min() <= values.max() < upper


def test_v1_episode_month_follows_the_current_stage(monkeypatch, tmp_path):
    monkeypatch.setattr(versions, "legacy_path", lambda: tmp_path / "painel.zip")
    monkeypatch.setattr(views, "_legacy", lambda *args: (None, None))
    monkeypatch.setattr(versions, "legacy_episode_rows", lambda *args: pd.DataFrame())
    monkeypatch.setattr(versions, "legacy_episode_source", lambda bundle, stage, horizon: pd.DataFrame({
        "model_name": ["ols_bruto"], "month_issued": ["2025-07" if stage == "teste_2025" else "2026-01"],
    }))
    page = AppTest.from_string(
        "import streamlit as st; from components.model_versions_views import _episode_section; "
        "stage = st.selectbox('Etapa', ['teste_2025', 'retrospectiva_2026']); "
        "_episode_section('sem_cenario_bruto', stage, 24, '1–24 h', None)", default_timeout=60,
    ).run()
    page.toggle(key="v1_query_episodes").set_value(True).run()
    assert not page.exception and not page.warning
    first_month = with_label(page.selectbox, "Mês da emissão")
    assert first_month.value == "2025-07"
    with_label(page.selectbox, "Etapa").set_value("retrospectiva_2026").run()
    next_month = with_label(page.selectbox, "Mês da emissão")
    assert not page.exception and not page.warning
    assert next_month.value == "2026-01" and next_month.key != first_month.key


def test_compact_manifest_rejects_tampered_metrics(tmp_path):
    for folder in (versions.OLD, versions.V5):
        source = versions.root() / folder
        target = tmp_path / folder
        target.mkdir()
        for path in source.glob("*"):
            if path.is_file() and (path.name.startswith(("metricas_", "MANIFESTO"))):
                shutil.copyfile(path, target / path.name)
    with (tmp_path / versions.V5 / "metricas_globais_v5.csv").open("ab") as changed:
        changed.write(b"\n")
    with pytest.raises(ValueError, match="SHA-256 divergente: metricas_globais_v5.csv"):
        versions.metric_tables(str(tmp_path))


def test_https_detail_fetches_only_requested_partition_and_checks_hash(monkeypatch, tmp_path):
    source = tmp_path / "storage"
    source.mkdir()
    prepare_index(source)
    index = source / "index.json"
    monkeypatch.setenv("ENERGY_FORECAST_DETAIL_DIR", str(tmp_path / "unmounted"))
    base = "https://storage.example.test/releases/forecast"
    monkeypatch.setenv("ENERGY_FORECAST_DETAIL_URL", base)
    monkeypatch.setenv("ENERGY_FORECAST_DETAIL_SHA256", hashlib.sha256(index.read_bytes()).hexdigest())
    monkeypatch.setattr(versions.tempfile, "gettempdir", lambda: str(tmp_path))
    downloaded = []

    def open_storage(url, *, timeout):
        assert url.startswith(base + "/")
        name = url.removeprefix(base + "/")
        downloaded.append(name)
        return (source / name).open("rb")

    monkeypatch.setattr(versions, "urlopen", open_storage)
    first, second = versions.detail_index()
    assert downloaded == ["index.json"]
    assert not first["preview"] and not second["preview"]
    path = versions.partition_path(first)
    assert downloaded == ["index.json", first["file"]]
    assert path.read_bytes() == (source / first["file"]).read_bytes()
    (source / second["file"]).write_bytes(b"particao corrompida")
    with pytest.raises(ValueError, match="SHA-256 divergente"):
        versions.partition_path(second)
