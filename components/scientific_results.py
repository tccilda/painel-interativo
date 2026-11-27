"""Apresentação dos resultados científicos a partir dos dados originais."""

from datetime import timedelta
from urllib.error import URLError

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components.charts import NAVY, PLOTLY_CONFIG, TEAL, explorer_chart
from components.metrics_cards import format_number, metric_cards
from components.page_frame import available_choice, model_label, scope_label
from components.tables import data_table
from services import model_versions as versions
from services.scientific_results import (
    ISSUE_COLUMNS, NEW_YEAR_STAGE, SCENARIOS, common_issue_metrics, issue_frame,
    new_year_issue, reference_metrics, scope_rows, time_sensitivity,
)


def _number(value, suffix):
    label = format_number(value, 2)
    return label if label == "N/D" else f"{label} {suffix}"


def _describe(row):
    version = row["versao"].upper() if row["versao"] != "piloto" else "Piloto histórico"
    return (f"{version} · {model_label(row['modelo'])} · {row['horizonte_h']} h · {row['bloco_horas']} · "
            f"{versions.STAGES[row['etapa']]} · {versions.SCENARIOS[row['cenario']]}")


def render_headline(frame, selected):
    st.markdown("#### Resultados frente às referências")
    if selected is None:
        st.caption("N/D para este recorte. Selecione um estimador com métricas disponíveis para comparar com as referências.")
        return
    st.caption(f"{_describe(selected)} · {selected['alvo_id']}")
    table = reference_metrics(frame, selected)
    cards = []
    for index, (name, row) in enumerate(table.iterrows()):
        metric = _number(row["mae_mwmed"], "MWmed")
        detail = f"{format_number(row['n_pares'], 0)} pares"
        if index:
            detail += f" · Redução do MAE: {_number(row['reducao_pct'], '%')}"
        cards.append({"label": model_label(name), "value": metric, "help": detail})
    metric_cards(cards)
    st.caption(
        "Pares por método e redução do MAE do modelo frente a cada referência. "
        "A comparação é descritiva e usa métricas agregadas do mesmo recorte. As contagens não comprovam a identidade dos pares."
    )
    values = table["mae_mwmed"].dropna()
    if values.empty:
        return
    labels = [model_label(name) for name in table.index]
    result = table["reducao_pct"]
    st.write(" · ".join(
        f"{model_label(name)}: {format_number(row['n_pares'], 0)} pares"
        + (f", redução de {_number(result.at[name], '%')}" if name != table.index[0] else "")
        for name, row in table.iterrows()
    ))
    figure = go.Figure(go.Bar(
        x=labels, y=table["mae_mwmed"], marker_color=[TEAL, NAVY, NAVY],
        hovertemplate="%{x}<br>MAE: %{y:,.2f} MWmed<extra></extra>",
    ))
    figure.update_layout(height=275, margin={"t": 15, "b": 48}, separators=",.",
                         yaxis={"title": "MAE (MWmed)", "range": [0, max(1.0, values.max() * 1.08)]})
    st.plotly_chart(figure, width="stretch", config=PLOTLY_CONFIG)


def render_time_sensitivity(frame, selected):
    with st.expander("Sensibilidade à hipótese de horário"):
        st.write(
            "UTC e São Paulo são interpretações alternativas dos carimbos originais do ONS. "
            "A interface exibe as horas civis no horário de São Paulo para ambas. "
            "O fuso oficial e a convenção da hora de carga continuam em aberto (CON-01)."
        )
        if selected is None or selected["cenario"] not in SCENARIOS:
            st.caption("N/D: o recorte não dispõe da combinação de estimador e hipóteses UTC e São Paulo.")
            return
        table, counts = time_sensitivity(frame, selected)
        st.caption(
            f"{selected['versao'].upper()} · {model_label(selected['modelo'])} · {selected['horizonte_h']} h · "
            f"{selected['bloco_horas']} · {versions.STAGES[selected['etapa']]} · "
            f"UTC: {format_number(counts.iloc[0], 0)} pares · São Paulo: {format_number(counts.iloc[1], 0)} pares."
        )
        data_table(table, decimals=4, alt="Sensibilidade descritiva entre as duas hipóteses")
        st.caption(
            "Variação relativa = 100 × (São Paulo − UTC) / UTC. A diferença do MAPE está em pontos percentuais. "
            "Os agregados são descritivos e usam pares de cada hipótese. Proximidade de valores não estabelece equivalência estatística."
        )


def render_new_year(frame, *, default_scenario, default_horizon):
    with st.expander("Estudo de caso · Ano-Novo de 2026"):
        if not st.toggle("Carregar emissão de Ano-Novo", key="science_load_new_year"):
            return
        left, right = st.columns(2)
        with left:
            scenario = available_choice("Hipótese do episódio", list(SCENARIOS), key="science_case_scenario",
                                        format_func=versions.SCENARIOS.__getitem__, default=default_scenario)
        with right:
            horizon = st.radio("Horizonte do episódio", [24, 48], index=[24, 48].index(default_horizon),
                               horizontal=True, format_func=lambda hours: f"{hours} h", key="science_case_horizon")
        try:
            issued, detail = new_year_issue(scenario, horizon)
            observed = versions.load_scenario(str(versions.root()), scenario)
            labels = [versions.classify(row, observed.events) for row in detail.itertuples(index=False)]
        except (OSError, ValueError, KeyError, URLError) as error:
            st.warning(f"Emissão de Ano-Novo indisponível: {error}")
            return

        future = issue_frame(detail)
        history = observed.observations.loc[observed.observations["timestamp"].between(
            issued - timedelta(hours=72), issued, inclusive="right"), ["timestamp", "observed_load"]]
        columns = ["timestamp", "observed_load", "predicted_load", "seasonal_load", "persistence_load", "phase"]
        chart_data = pd.concat([history.assign(phase="histórico"), future[columns]], ignore_index=True)
        figure = explorer_chart(chart_data, issued)
        st.caption(
            f"V5 · OLS estabilizado · {horizon} h independentes · {versions.SCENARIOS[scenario]} · "
            f"emissão em {issued.tz_convert(versions.TZ):%d/%m/%Y às %H:%M} no horário de São Paulo."
        )
        st.plotly_chart(figure, width="stretch", config=PLOTLY_CONFIG)

        common, metrics = common_issue_metrics(future, ISSUE_COLUMNS)
        full = scope_rows(frame, alvo_id=versions.TARGET, unidade="MWmed", versao="v5",
                          escopo_avaliacao="retrospectiva_nao_cego", etapa=NEW_YEAR_STAGE, cenario=scenario, horizonte_h=horizon,
                          bloco_horas=f"1–{horizon} h").set_index("modelo").reindex(list(ISSUE_COLUMNS))
        summary = pd.DataFrame([{
            "Método": model_label(name), "MAE da emissão (MWmed)": result["mae"], "MAPE da emissão (%)": result["mape"],
            "MAE do recorte (MWmed)": full.at[name, "mae_mwmed"], "MAPE do recorte (%)": full.at[name, "mape_pct"],
            "Pares no recorte": full.at[name, "n_pares"], "Pares MAPE no recorte": full.at[name, "n_mape_validos"],
        } for name, result in metrics.items()])
        st.caption(f"{len(common)} de {horizon} alvos comuns para MAE · {common['observed_load'].ne(0).sum()} para MAPE. "
                   "As métricas agregadas vêm do recorte completo da retrospectiva.")
        data_table(summary, alt="Métricas pareadas da emissão de Ano-Novo e agregados do recorte")
        if not common.empty:
            errors = common["predicted_load"].sub(common["observed_load"]).abs()
            worst = common.loc[errors.idxmax()]
            stamp = worst["timestamp"].tz_convert(versions.TZ)
            st.write(f"Maior erro absoluto do OLS: **{_number(errors.max(), 'MWmed')}**, no passo **{worst['passo_h']}**, "
                     f"em **{stamp:%d/%m/%Y às %H:%M}** (horário de São Paulo).")
        else:
            st.caption("Maior erro absoluto do OLS · N/D sem alvos comuns.")

        events = future.assign(
            Data=future["timestamp"].dt.tz_convert(versions.TZ).dt.strftime("%d/%m/%Y"),
            Âmbito=[scope_label(row[1]) for row in labels],
            Eventos=[row[2] for row in labels],
        )
        events = events.loc[events["Eventos"].ne(""), ["Data", "Âmbito", "Eventos", "evento_versao_ids"]]
        if events.empty:
            st.caption("Nenhum evento ativo identificado nos alvos desta emissão.")
        else:
            grouped = events.value_counts(sort=False).rename("Horas").reset_index()
            data_table(grouped.rename(columns={"evento_versao_ids": "IDs dos eventos"}),
                       alt="Eventos de calendário nos alvos do caso de Ano-Novo")
        seasonal = metrics["sazonal_semanal"]["mae"]
        ols = metrics["ols_estabilizado"]["mae"]
        if (seasonal is not None and ols is not None and seasonal < ols
                and full.at["ols_estabilizado", "mae_mwmed"] < full.at["sazonal_semanal", "mae_mwmed"]):
            st.write("A referência sazonal semanal teve MAE menor nesta emissão. O OLS teve MAE menor no recorte completo.")
        st.caption("Um resultado agregado favorável pode coexistir com erros maiores em emissões específicas. "
                   "A presença de eventos no episódio descreve seu contexto e, por si só, não permite inferir causalidade.")


def render_version_examples(frame, paired):
    st.write("Estabilidade numérica diz respeito à solução do ajuste, e o erro preditivo é medido sobre os alvos da avaliação.")
    scope = {
        "alvo_id": versions.TARGET, "unidade": "MWmed", "cenario": "hipotese_Sao_Paulo",
        "horizonte_h": 48, "bloco_horas": "1–48 h", "escopo_avaliacao": "retrospectiva_nao_cego",
    }
    examples = scope_rows(frame, **scope, etapa="teste_2025", papel="Selecionado")
    older = examples.set_index("versao").reindex(["v2", "v3", "v4"])
    st.caption("Exemplos publicados · Hipótese São Paulo · 48 h completas.")
    if older["mae_mwmed"].notna().all():
        v2, v3, v4 = older["mae_mwmed"]
        st.write(f"No teste de 2025, a V2 ({model_label(older.at['v2', 'modelo'])}) teve MAE de "
                 f"{_number(v2, 'MWmed')} e a V3 ({model_label(older.at['v3', 'modelo'])}), de "
                 f"{_number(v3, 'MWmed')}. São agregados descritivos de estimadores selecionados em cada versão.")
        st.write(f"V3 e V4 exibem {_number(v3, 'MWmed')} e {_number(v4, 'MWmed')} nesse recorte. "
                 "A concordância na precisão exibida é uma observação sobre os agregados. "
                 "A correção da verificação de posto na V4 constitui uma mudança de diagnóstico.")
    rows = scope_rows(paired, **scope, versao="v5", versao_ref="v4", modelo="ols_estabilizado",
                      modelo_ref="ols_estabilizado", tipo_comparacao="mesmo_estimador")
    for row in rows.itertuples(index=False):
        delta = row.delta_mae_mwmed
        st.write(f"{versions.STAGES[row.etapa]} · V5 − V4 (OLS estabilizado): {_number(delta, 'MWmed')} "
                 f"de MAE em {format_number(row.n_pares_comuns, 0)} pares comuns. "
                 "Sinal negativo indica MAE menor na V5.")
