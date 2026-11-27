"""Recortes científicos derivados dos agregados e de uma emissão de referência."""

from math import isfinite

import pandas as pd

from services import model_versions as versions
from services.metrics_service import calculate_metrics


SCENARIOS = ("hipotese_UTC", "hipotese_Sao_Paulo")
REFERENCES = ("sazonal_semanal", "persistencia")
ISSUE_COLUMNS = dict(zip(
    ("ols_estabilizado", *REFERENCES),
    ("predicted_load", "seasonal_load", "persistence_load"),
    strict=True,
))
SCOPE = ("alvo_id", "unidade", "versao", "escopo_avaliacao", "etapa", "horizonte_h", "bloco_horas")
NEW_YEAR_STAGE = "retrospectiva_2026"


def scope_rows(frame, **filters):
    return frame.loc[frame[list(filters)].eq(pd.Series(filters)).fillna(False).all(axis=1)]


def percent_delta(difference, baseline):
    """Variação em relação a uma base positiva, sem arredondamento ou limite de sinal."""
    if pd.isna(difference) or pd.isna(baseline) or not isfinite(difference) or not isfinite(baseline) or baseline <= 0:
        return None
    return 100 * (difference / baseline)


def reference_metrics(frame, selected):
    """Empilha apenas o estimador e referências com a mesma chave de recorte."""
    scope = {key: selected[key] for key in (*SCOPE, "cenario")}
    names = [selected["modelo"], *REFERENCES]
    refs = scope_rows(frame, **scope)
    items = refs.loc[refs["modelo"].isin(names)].set_index("modelo").reindex(names)
    return items[["mae_mwmed", "n_pares"]].assign(
        reducao_pct=[None, *(percent_delta(items.at[name, "mae_mwmed"] - selected["mae_mwmed"],
                                          items.at[name, "mae_mwmed"]) for name in REFERENCES)]
    )


def time_sensitivity(frame, selected):
    """Contrasta agregados do mesmo desenho para duas interpretações dos carimbos."""
    scope = {key: selected[key] for key in (*SCOPE, "modelo")}
    scenarios = scope_rows(frame, **scope).set_index("cenario").reindex(SCENARIOS)
    rows = []
    for code, label in versions.METRICS.items():
        utc, sp = scenarios[code]
        delta = sp - utc
        rows.append({
            "Indicador": label, "UTC": utc, "São Paulo": sp, "São Paulo − UTC": delta,
            "Magnitude da diferença": abs(delta), "Variação relativa (%)": percent_delta(delta, utc),
        })
    return pd.DataFrame(rows), scenarios["n_pares"]


def common_issue_metrics(future, methods):
    """Calcula cada estimador sobre os mesmos alvos e a mesma máscara de zeros para MAPE."""
    common = future.dropna(subset=["observed_load", *methods.values()])
    results = {}
    for name, column in methods.items():
        aligned = common[["observed_load", column]].rename(columns={column: "predicted_load"})
        results[name] = calculate_metrics(aligned)
    return common, results


def new_year_issue(scenario, horizon):
    """Consulta a emissão de Ano-Novo declarada no manifesto V5, via uma partição verificada."""
    reference = versions.manifest_issues()
    samples = [row for row in reference
               if (row["cenario"], row["etapa"], row["horizonte_h"], row["passos"]) ==
               (scenario, NEW_YEAR_STAGE, horizon, horizon)
               and pd.Timestamp(row["origem_t"]).tz_convert(versions.TZ).strftime("%Y-%m-%d") == "2026-01-01"]
    if len(samples) != 1:
        raise ValueError("O manifesto deve identificar uma única emissão de Ano-Novo para o recorte.")
    issue = samples[0]["origem_t"]
    entry = next((row for row in versions.detail_index()
                  if (row["scenario"], row["stage"], row["horizon"], row["month"]) ==
                  (scenario, NEW_YEAR_STAGE, horizon, "2026-01")), None)
    if entry is None:
        raise FileNotFoundError("A partição de janeiro de 2026 está indisponível neste recorte.")
    detail = versions.forecast_detail(versions.partition_path(entry), entry["sha256"], horizon,
                                      "ols_estabilizado", issue)
    return pd.Timestamp(issue), detail


def issue_frame(detail, *, as_of=None):
    future = detail.rename(columns={
        "instante_alvo": "timestamp", "y_real": "observed_load", "y_pred": "predicted_load",
        "y_baseline_semanal": "seasonal_load", "y_baseline_persistencia": "persistence_load",
    }).assign(timestamp=lambda frame: pd.to_datetime(frame["timestamp"], utc=True), phase="previsão")
    cutoff = pd.Timestamp.now(tz="UTC") if as_of is None else as_of
    future.loc[future["timestamp"].gt(cutoff), "observed_load"] = float("nan")
    return future
