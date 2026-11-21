"""Integração com o catálogo publicado e partições mínimas descartáveis."""

from datetime import timedelta
import hashlib
import json
from pathlib import Path
import shutil

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from services import model_versions as versions

ROOT = Path(__file__).resolve().parents[1]


def prepare_index(tmp_path):
    manifest = json.loads((versions.root() / versions.V5 / "MANIFESTO_v5.json").read_text(encoding="utf-8"))
    issue = pd.Timestamp("2025-07-01T03:00:00Z")
    entries = []
    source = {}
    for horizon in (24, 48):
        name = f"previsoes_{horizon}h_v5.csv"
        source[name] = manifest["arquivos"][name]["sha256"]
        path = tmp_path / f"{horizon}__hipotese_UTC__teste_2025__2025-07.parquet"
        pd.DataFrame({
            "modelo": "ols_estabilizado", "origem_t": issue.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "passo_h": range(1, horizon + 1), "eh_selecionado": 1,
            "instante_alvo": pd.date_range(issue + timedelta(hours=1), periods=horizon, freq="h").strftime("%Y-%m-%dT%H:%M:%SZ"),
            "y_real": 40_000.0, "y_pred": 40_010.0, "y_baseline_semanal": 39_800.0,
            "y_baseline_persistencia": 39_900.0, "fim_de_semana": 0, "eh_feriado": 0,
            "eh_ponto_facultativo": 0, "evento_versao_ids": "[]",
        }).to_parquet(path, index=False)
        entries.append(dict(file=path.name, sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                            bytes=path.stat().st_size, horizon=horizon, scenario="hipotese_UTC",
                            stage="teste_2025", month="2025-07", rows=horizon))
    (tmp_path / "index.json").write_text(json.dumps({"schema": 1, "source": source, "partitions": entries}))


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


def test_clean_checkout_ships_real_v5_sample(monkeypatch, tmp_path):
    monkeypatch.setenv("ENERGY_FORECAST_DETAIL_DIR", str(tmp_path))
    monkeypatch.setenv("ENERGY_FORECAST_DETAIL_URL", "")
    index = versions.detail_index()
    assert len(index) == 12 and all(item["preview"] for item in index)
    assert sum(item["rows"] for item in index) == 432
    page = AppTest.from_file(ROOT / "streamlit_app.py", default_timeout=60).run()
    assert not page.exception and len(page.dataframe[0].value) == 24
    method = next(item for item in page.expander if item.label == "Detalhes metodológicos")
    assert any("12 emissões reais" in item.value for item in method.markdown)
    assert not any("12 emissões reais" in item.value for item in page.caption)
    assert page.selectbox(key="v5_month").label == "Mês da emissão (amostra V5)"
    assert page.selectbox(key="v5_month").options == ["07/2025"]
    assert page.selectbox(key="v5_month").value == "2025-07"
    assert page.selectbox(key="catalog_explorer_version").options == ["V5"]


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
    episodes = next(table.value for table in app.dataframe if "Erro absoluto (MWmed)" in table.value)
    assert set(episodes["Passo"]) == set(range(25, 49))
    assert episodes["Erro absoluto (MWmed)"].is_monotonic_decreasing
    pd.testing.assert_series_equal(episodes["Erro absoluto (MWmed)"],
                                  (episodes["Observado (MWmed)"] - episodes["Previsto (MWmed)"]).abs(),
                                  check_names=False)
    exports = [item.proto.label for item in app.get("download_button")]
    assert {"Exportar episódios", "Exportar métricas do recorte", "Exportar pares comuns"}.issubset(exports)
    app.selectbox(key="evolution_version").set_value("v1").run()
    assert not app.exception and app.selectbox(key="evolution_scenario").value == "sem_cenario_bruto"
    assert app.dataframe[0].value["Versão"].tolist() == ["V1"]


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
