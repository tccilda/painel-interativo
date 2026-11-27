"""Controles e visões do catálogo experimental V1–V5."""

from datetime import timedelta
from urllib.error import URLError

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from components.charts import PLOTLY_CONFIG, WEEKDAYS, explorer_chart
from components.metrics_cards import format_number, metric_cards
from components.page_frame import CALENDAR_CONTEXT, DAY_LABELS, available_choice, model_label, scope_label
from components.scientific_results import render_headline, render_new_year, render_time_sensitivity, render_version_examples
from components.tables import csv_bytes, data_table
from services import model_versions as versions
from services.analysis_service import largest_errors, temperature_at_issue
from services.forecast_catalog import forecast_catalog
from services.scientific_results import common_issue_metrics, issue_frame


TARGET_CONTEXT = f"A série {versions.TARGET} mede a carga regional do {versions.REGION}, em MWmed."

TEMPERATURE_CONTEXT = (
    "A média aritmética das medições disponíveis de A621 e A601 é informação de contexto, "
    "sem preenchimento de lacunas. Os modelos V5 usaram a série composta de temperatura do Rio de Janeiro, "
    "com A621 prioritária, A601 como alternativa na mesma hora e preenchimento causal com a leitura anterior "
    "nas duas lacunas simultâneas da série auditada."
)
TEMPERATURE_AT_ISSUE = (
    "O cartão usa a última medição disponível de cada estação até t₀, com até 1 h de defasagem."
)

PREVIEW_METRICS = (
    "Cada emissão tem 24 ou 48 alvos. As métricas da aba Avaliação de Desempenho e Erros "
    "usam os recortes completos, com 103.032 a 347.760 pares de emissão e hora prevista."
)
CLOCK_CONTEXT = (
    "UTC e São Paulo são duas hipóteses para interpretar o carimbo original do ONS. "
    "As diferenças agregadas de erro do OLS foram pequenas, abaixo de 1% em relação à hipótese UTC. "
    "O fuso oficial e a convenção do intervalo da carga seguem em aberto (CON-01)."
)


def choice(label, options, key, labels=None, *, default=None):
    return available_choice(label, options, key=key, format_func=labels.__getitem__ if labels else str, default=default)


def month_choice(label, months, key):
    options = sorted(months, reverse=True)
    labels = {month: f"{month[5:]}/{month[:4]}" for month in options}
    reference = next((month for month in options if months[month].get("reference_origin")), None) if isinstance(months, dict) else None
    return choice(label, options, key, labels, default=reference)


def preview_coverage(entries):
    issues = sum(entry["rows"] // entry["horizon"] for entry in entries)
    return f"A amostra V5 inclui {format_number(issues, 0)} emissões reais neste recorte. {PREVIEW_METRICS}"


@st.cache_resource(show_spinner=False)
def _legacy(path, sha):
    bundle = versions.legacy_bundle(path, sha)
    return bundle, forecast_catalog(bundle)


def render_explorer(legacy_render):
    st.header("Explorador de Previsões")
    available = ["V5", "V1"] if versions.legacy_available() else ["V5"]
    version = choice("Versão", available, "catalog_explorer_version")
    try:
        if version == "V1":
            from components.sidebar import SidebarSettings

            path = versions.legacy_path()
            if path is None:
                st.info("Previsões V1 indisponíveis nesta instalação. Configure o pacote legado descrito no guia de integração.")
                return
            bundle, catalog = _legacy(path, versions.LEGACY_SHA)
            if catalog.empty:
                st.warning("O pacote legado V1 não pôde ser carregado.")
                return
            with st.expander("Limitações da V1"):
                st.write("O fuso original não está documentado. O horário exibido usa uma interpretação do leitor legado. A emissão e o alvo não devem ser pareados com V2–V5 por esses carimbos.")
            settings = SidebarSettings("v1", 24, versions.REGION)
            legacy_render((bundle, settings), catalog)
            return
        _render_v5(legacy_available="V1" in available)
    except (OSError, ValueError, KeyError, URLError) as error:
        st.warning(f"Fonte detalhada indisponível: {error}")


def _render_v5(*, legacy_available):
    index = versions.detail_index()
    if not index:
        st.info("O índice das previsões detalhadas V5 está indisponível. As métricas e a série auditada continuam disponíveis nas outras abas.")
        return
    preview = index[0]["preview"]
    columns = st.columns([1.3, 1.2, 0.8, 0.9])
    with columns[0]:
        scenario = choice("Hipótese de horário", list(versions.SCENARIOS)[:2], "v5_explorer_scenario", versions.SCENARIOS)
    with columns[1]:
        stage = choice("Conjunto", list(versions.STAGES), "v5_explorer_stage", versions.STAGES)
    with columns[2]:
        horizon = st.radio("Horizonte", [24, 48], horizontal=True, format_func=lambda hours: f"{hours} h", key="v5_explorer_horizon")
    with columns[3]:
        history_hours = st.selectbox("Histórico anterior", [72, 48, 120, 168], format_func=lambda v: f"{v} h", key="v5_explorer_history", placeholder="Selecione uma opção")
    entries = {e["month"]: e for e in index if (e["scenario"], e["stage"], e["horizon"]) == (scenario, stage, horizon)}
    if preview:
        st.caption(preview_coverage(entries.values()))
    if not entries:
        st.info("Nenhuma emissão no recorte selecionado.")
        return
    slice_key = f"{scenario}_{stage}_{horizon}"
    cols = st.columns(4)
    with cols[0]:
        month = month_choice("Mês da emissão (amostra V5)" if preview else "Mês da emissão", entries, f"v5_month_{slice_key}")
    entry = entries[month]
    path = versions.partition_path(entry)
    catalog = versions.issues_for_models(path, entry["sha256"])
    models = sorted(catalog["modelo"].unique(), key=lambda name: (not catalog.loc[catalog["modelo"].eq(name), "eh_selecionado"].eq(1).any(), name))
    with cols[1]:
        model = available_choice("Estimador", models, format_func=model_label, key=f"v5_model_{slice_key}_{month}")
    model_key = f"{slice_key}_{month}_{model}"
    options = catalog.loc[catalog["modelo"].eq(model), "origem_t"]
    times = pd.to_datetime(options, utc=True).dt.tz_convert(versions.TZ)
    dates = sorted(times.dt.date.unique(), reverse=True)
    reference = entry.get("reference_origin")
    reference_dates = times.loc[options.eq(reference)].dt.date
    reference_day = reference_dates.iloc[0] if not reference_dates.empty else None
    with cols[2]:
        day = available_choice("Data da emissão", dates, default=reference_day,
                               format_func=lambda value: value.strftime("%d/%m/%Y"), key=f"v5_date_{model_key}")
    with cols[3]:
        day_times = times.loc[times.dt.date.eq(day)]
        labels = day_times.dt.strftime("%H:%M")
        labels = labels.where(~labels.duplicated(keep=False), day_times.dt.strftime("%H:%M:%S %z"))
        issue = choice("Hora da emissão (horário de São Paulo)", sorted(options.loc[day_times.index], reverse=True),
                       f"v5_issue_{model_key}_{day}", dict(zip(options.loc[day_times.index], labels)), default=reference)
    data = versions.forecast_detail(path, entry["sha256"], horizon, model, issue)
    observed = versions.load_scenario(str(versions.root()), scenario)
    t0 = pd.Timestamp(issue)
    _render_forecast(data, observed, t0, horizon, scenario, stage, history_hours, preview=preview)

    with st.expander("Detalhes metodológicos"):
        st.write(TARGET_CONTEXT)
        st.write("V2–V4 têm apenas métricas agregadas, em Avaliação de Desempenho e Erros.")
        if not legacy_available:
            st.write("As previsões horárias da V1 estão disponíveis em instalações com o ZIP legado.")
        st.write("As previsões V5 foram produzidas em uma avaliação retrospectiva, com dados já fechados.")
        st.write(f"{CLOCK_CONTEXT} A emissão e as horas previstas aparecem no horário de São Paulo.")
        st.write(f"A temperatura do cartão é informação de contexto. {TEMPERATURE_AT_ISSUE} {TEMPERATURE_CONTEXT}")
        st.write("A classificação do calendário usa os atos já conhecidos no momento da emissão, conforme a hipótese de horário escolhida.")
        st.write(CALENDAR_CONTEXT)
        st.write(
            "O OLS estabilizado é uma regressão linear por mínimos quadrados, com padronização ajustada "
            "no treino e tolerância numérica explícita. Teve o menor MAE na validação do primeiro semestre "
            "de 2025 nos dois horizontes e hipóteses. Em 48 h, o MAE do Ridge 1 ficou a menos de 0,50 MWmed "
            "do OLS em todas as etapas e hipóteses do horizonte inteiro."
        )
        st.write(
            "Um experimento futuro separado pode comparar XGBoost e LightGBM com OLS, Ridge e as referências "
            "simples, usando os mesmos pares, atributos disponíveis na emissão, ajustes em janelas anteriores "
            "e um novo período reservado para teste. A avaliação exibida abrange modelos lineares e referências simples."
        )

def _render_forecast(data, observed, t0, horizon, scenario, stage, history_hours, *, preview):
    future = issue_frame(data)
    previous = observed.observations
    previous = previous.loc[(previous["timestamp"] <= t0) & (previous["timestamp"] > t0 - timedelta(hours=history_hours))]
    columns = ["timestamp", "observed_load", "predicted_load", "seasonal_load", "persistence_load", "phase"]
    frame = pd.concat([previous.assign(phase="histórico").reindex(columns=columns), future[columns]], ignore_index=True)
    peak = future.loc[future["predicted_load"].idxmax()]
    temperature = temperature_at_issue(observed.weather, t0, versions.REGION)
    labels = [versions.classify(row, observed.events) for row in data.itertuples(index=False)]
    mae = (future.predicted_load - future.observed_load).abs().mean()
    metric_cards([
        {"label": "Pico previsto", "value": f"{format_number(peak.predicted_load)} MWmed"},
        {"label": "Horário do pico", "value": peak.timestamp.tz_convert(versions.TZ).strftime("%H:%M · %d/%m")},
        {"label": "Temperatura em t₀", "value": f"{format_number(temperature['temperature_c'])} °C" if temperature else "N/D",
         "help": f"{TEMPERATURE_CONTEXT} {TEMPERATURE_AT_ISSUE}"},
        {"label": "MAE da emissão", "value": f"{format_number(mae, 2)} MWmed" if pd.notna(mae) else "N/D",
         "help": f"{future.observed_load.count()} de {horizon} horas com carga observada."},
    ])
    model = data["modelo"].iloc[0]
    _reference_comparison(future, model, t0, horizon, stage, scenario, preview=preview)
    figure = explorer_chart(frame, t0)
    st.plotly_chart(figure, width="stretch", config=PLOTLY_CONFIG)
    with st.expander("Valores horários e calendário"):
        counts = pd.Series([DAY_LABELS[x[0]] for x in labels]).value_counts(sort=False)
        st.write(" · ".join(f"{kind}: {count} h" for kind, count in counts.items()))
        role = "escolhido na avaliação deste recorte" if data["eh_selecionado"].iloc[0] else (
            "usado no piloto" if model == "piloto_so_carga" else "avaliado como alternativa"
        )
        st.write(f"Estimador exibido · {model_label(model)} ({role})")
        exported = data.assign(versao="v5", alvo_id=versions.TARGET, horizonte_h=horizon, cenario=scenario,
                               etapa=stage, unidade="MWmed", y_real=future["observed_load"])
        display = exported.assign(calendario=[DAY_LABELS[x[0]] for x in labels],
                                  ambito=[scope_label(x[1]) for x in labels],
                                  eventos=[x[2] for x in labels])
        display["instante_local"] = future["timestamp"].dt.tz_convert(versions.TZ).dt.strftime("%d/%m/%Y %H:%M %z")
        export = display.assign(ambito=[scope_label(x[1], territory=False) for x in labels])
        headings = {"passo_h": "Passo", "instante_local": "Alvo local", "y_real": "Observado (MWmed)",
                    "y_pred": "Previsto (MWmed)", "y_baseline_semanal": "Semanal (MWmed)",
                    "y_baseline_persistencia": "Persistência (MWmed)", "calendario": "Calendário",
                    "ambito": "Âmbito", "eventos": "Eventos", "evento_versao_ids": "IDs de evento"}
        display["instante_local"] = display["instante_local"].str.slice(stop=-6)
        st.caption("Horas dos alvos no horário de São Paulo.")
        data_table(display[list(headings)].rename(columns=headings), alt="Valores horários e calendário da emissão")
        st.download_button("Exportar emissão V5", csv_bytes(export), file_name=f"v5_{horizon}h.csv", mime="text/csv")


def _reference_comparison(future, model, t0, horizon, stage, scenario, *, preview):
    references = {"sazonal_semanal": "seasonal_load", "persistencia": "persistence_load"}
    methods = {model: "predicted_load", **{name: column for name, column in references.items() if name != model}}
    global_methods = ["ols_estabilizado", *references]
    common, metrics = common_issue_metrics(future, methods)
    local_time = t0.tz_convert(versions.TZ).strftime("%d/%m/%Y às %H:%M")
    st.markdown("#### Comparação com as referências")
    st.caption(f"V5 · {versions.REGION} · {versions.STAGES[stage]} · {horizon} h · {versions.SCENARIOS[scenario]}")
    issue_column, global_column = st.columns(2)
    issue_column.markdown("**Emissão selecionada**")
    issue_column.caption(
        f"{local_time} (horário de São Paulo) · {len(common)} de {horizon} alvos em comum para o MAE · "
        f"{common['observed_load'].ne(0).sum()} para o MAPE."
    )
    rows = []
    for name, result in metrics.items():
        rows.append({"Estimador": model_label(name), "MAE (MWmed)": result["mae"], "MAPE (%)": result["mape"]})
    with issue_column:
        data_table(pd.DataFrame(rows), alt="MAE e MAPE da emissão selecionada")

    global_column.markdown("**Resumo do recorte completo**")
    if model != "ols_estabilizado":
        global_column.caption("O resumo apresenta o OLS estabilizado, estimador selecionado na avaliação V5, e as duas referências.")
    try:
        global_metrics = versions.metric_tables(str(versions.root()))["globais"]
        selected = _filter(global_metrics, horizon, stage, scenario)
        selected = selected.loc[
            selected["versao"].eq("v5") & selected["bloco_horas"].eq(f"1–{horizon} h")
            & selected["modelo"].isin(global_methods)
        ].set_index("modelo").reindex(global_methods)
    except (OSError, ValueError, KeyError) as error:
        global_column.caption(f"Métricas do recorte completo indisponíveis: {error}")
    else:
        columns = {"n_pares": "Pares", "n_mape_validos": "Pares MAPE",
                   "mae_mwmed": "MAE (MWmed)", "mape_pct": "MAPE (%)"}
        if selected[["n_pares", "n_mape_validos"]].nunique(dropna=False).eq(1).all() and selected["n_pares"].notna().all():
            global_column.caption(f"Os três métodos usam {format_number(selected['n_pares'].iloc[0], 0)} pares de emissão e hora prevista para o MAE.")
        with global_column:
            data_table(
                selected[list(columns)].rename(columns=columns).assign(
                    Estimador=[model_label(name) for name in selected.index],
                )[["Estimador", *columns.values()]],
                integer_columns=("Pares", "Pares MAPE"), alt="Métricas do recorte completo da V5",
            )
    if preview:
        st.caption(
            "O OLS teve MAE e MAPE menores que as duas referências em 2 dos 12 exemplos originais do manifesto e em 12 dos 12 "
            "recortes completos. Cada exemplo mostra só uma emissão, enquanto cada recorte completo reúne "
            "todas as emissões avaliadas naquela combinação."
        )
    st.caption(
        "MAE é o erro absoluto médio. MAPE é o erro percentual absoluto médio e usa observados diferentes "
        "de zero. A Sazonal semanal repete a carga de 168 h antes do alvo. A Persistência repete a carga na emissão."
    )


def _filter(frame, horizon, stage, scenario):
    return frame.loc[frame["horizonte_h"].eq(horizon) & frame["etapa"].eq(stage) & frame["cenario"].eq(scenario)]


def render_evolution():
    st.header("Avaliação de Desempenho e Erros")
    st.subheader("Evolução dos Modelos")
    try:
        tables = versions.metric_tables(str(versions.root()))
    except (OSError, ValueError, KeyError) as error:
        st.warning(f"Métricas indisponíveis: {error}")
        return
    cols = st.columns([1.1, 0.8, 1.3, 1.3, 1])
    with cols[0]:
        version = choice("Versão da avaliação", ["Todas", *versions.VERSIONS, "piloto"], "evolution_version",
                         {"Todas": "Todas", **{v: v.upper() for v in versions.VERSIONS}, "piloto": "Piloto histórico"})
    with cols[1]:
        horizon = st.radio("Horizonte", [24, 48], horizontal=True, format_func=lambda hours: f"{hours} h", key="evolution_horizon")
    with cols[2]:
        scenarios = list(versions.SCENARIOS)
        if version != "Todas":
            available = tables["globais"].loc[tables["globais"]["versao"].eq(version), "cenario"]
            scenarios = [s for s in scenarios if s in set(available)]
        scenario = choice("Hipótese de horário", scenarios, "evolution_scenario", versions.SCENARIOS)
    with cols[3]:
        stage = choice("Etapa", list(versions.STAGES), "evolution_stage", versions.STAGES)
    with cols[4]:
        block = choice("Bloco", ["1–24 h"] if horizon == 24 else ["1–48 h", "1–24 h", "25–48 h"], "evolution_block")
    left, right = st.columns(2)
    with left:
        if version == "piloto":
            role = choice("Grupo de estimadores", ["Piloto", "Referência"], "evolution_pilot_role")
        else:
            role = choice("Grupo de estimadores", ["Selecionado", "Alternativa", "Piloto", "Referência"], "evolution_role")
    with right:
        metric = choice("Indicador dos gráficos", list(versions.METRICS), "evolution_metric", versions.METRICS)
    if version == "piloto" and stage == "retrospectiva_2026":
        st.info("Retrospectiva 2026 está fora do desenho do Piloto histórico.")
    population = _filter(tables["globais"], horizon, stage, scenario)
    population = population.loc[population["bloco_horas"].eq(block) & population["papel"].eq(role)]
    if version != "Todas":
        population = population.loc[population["versao"].eq(version)]
    model = None
    if role != "Selecionado":
        models = sorted(population["modelo"].unique())
        if models:
            model = available_choice("Estimador", models, format_func=model_label, key="evolution_model")
            population = population.loc[population["modelo"].eq(model)]
    if population["versao"].duplicated().any():
        st.warning("Há mais de uma linha para a mesma versão no recorte. Selecione um estimador único.")
        return
    focus = population.loc[population["versao"].eq("v5" if version == "Todas" else version)]
    selected = focus.iloc[0] if len(focus) == 1 else None
    render_headline(tables["globais"], selected if role != "Referência" else None)
    st.markdown("#### Comparação entre versões")
    order = list(versions.VERSIONS) if version == "Todas" else [version]
    if version == "Todas" and role == "Piloto" and scenario == "sem_cenario_bruto":
        order.insert(0, "piloto")
    display = population.set_index("versao").reindex(order).reset_index()
    display["versao"] = display["versao"].map(version_label)
    display["modelo"] = display["modelo"].map(model_label, na_action="ignore")
    values = display[metric].dropna()
    if not values.empty:
        fig = px.bar(
            display, x="versao", y=metric,
            hover_data={"modelo": True, "n_pares": ":,.0f", metric: ":,.4f"},
            labels={"versao": "Versão", "modelo": "Estimador", "n_pares": "Pares",
                    metric: versions.METRICS[metric]},
        )
        fig.update_yaxes(range=[0, max(1.0, values.max() * 1.08)], tickformat=",.2f")
        fig.update_layout(height=300, margin={"t": 15}, separators=",.")
        fig.update_xaxes(categoryorder="array", categoryarray=[version_label(v) for v in order])
        st.plotly_chart(fig, width="stretch", config=PLOTLY_CONFIG)
        st.caption("Valores absolutos com os pares de cada versão. A seção V4 × V5 mostra diferenças calculadas sobre pares comuns, quando disponíveis.")
    elif display["modelo"].isna().all() and not (version == "piloto" and stage == "retrospectiva_2026"):
        if role == "Alternativa":
            st.info(f"Não há estimadores alternativos disponíveis neste recorte de {horizon} h.")
        else:
            st.info("Não há estimadores deste grupo no recorte selecionado.")
    data_table(display[["versao", "modelo", "n_pares", "n_mape_validos", *versions.METRICS]].rename(columns={
        "versao": "Versão", "modelo": "Estimador", "n_pares": "Pares", "n_mape_validos": "Pares MAPE", **versions.METRICS
    }), decimals=4, integer_columns=("Pares", "Pares MAPE"))
    st.download_button("Exportar métricas do recorte", csv_bytes(population.loc[population["versao"].isin(order)]),
                       file_name="metricas_do_recorte.csv", mime="text/csv")
    steps = tables["por_passo"]
    _step_chart(steps.loc[steps["versao"].isin(order)], horizon, stage, scenario, block, role, model, metric)
    if version in ("Todas", "v4", "v5"):
        _paired_section(tables["pares"], horizon, stage, scenario, block, role, model, population)
    _horizon_summary(tables["globais"], stage, scenario, version)
    render_time_sensitivity(tables["globais"], selected)
    render_new_year(tables["globais"], default_scenario=scenario, default_horizon=horizon)
    if version in ("Todas", "v5") and scenario != "sem_cenario_bruto" and role != "Referência":
        selected = population.loc[population["versao"].eq("v5"), "modelo"]
        if not selected.empty:
            _episode_section(scenario, stage, horizon, block, selected.iloc[0])
    if version in ("Todas", "v1") and scenario == "sem_cenario_bruto" and role == "Selecionado":
        _episode_section(scenario, stage, horizon, block, None)
    with st.expander("Métricas por hora ou mês do alvo"):
        granularity = choice("Agrupamento civil", ["por_hora", "por_mes"], "evolution_civil",
                             {"por_hora": "Hora do dia", "por_mes": "Mês"})
        civil_key = "hora_alvo_local" if granularity == "por_hora" else "mes_alvo_local"
        civil = _filter(tables[granularity], horizon, stage, scenario)
        civil = civil.loc[civil["bloco_horas"].eq(block) & civil["papel"].eq(role) & civil["versao"].isin(order)]
        if model is not None:
            civil = civil.loc[civil["modelo"].eq(model)]
        if civil.empty:
            st.caption("N/D neste recorte.")
        else:
            display_civil = civil[["versao", "modelo", civil_key, "n_pares", *versions.METRICS]].copy()
            if granularity == "por_mes":
                display_civil[civil_key] = pd.to_datetime(display_civil[civil_key], format="%Y-%m").dt.strftime("%m/%Y")
            else:
                display_civil[civil_key] = display_civil[civil_key].map(lambda hour: f"{hour:02.0f} h", na_action="ignore")
            st.caption("Horas e meses no horário de São Paulo.")
            display_civil["versao"] = display_civil["versao"].map(version_label)
            display_civil["modelo"] = display_civil["modelo"].map(model_label)
            data_table(display_civil, height=320, labels={
                "versao": "Versão", "modelo": "Estimador", civil_key: "Hora local" if granularity == "por_hora" else "Mês",
                "n_pares": "Pares", **versions.METRICS,
            })
    with st.expander("Disponibilidade e detalhes metodológicos"):
        st.write(TARGET_CONTEXT)
        st.write("A comparação V4 × V5 usa os pares comuns fornecidos. Os deltas são V5 − V4 e a variação do MAPE é expressa em pontos percentuais.")
        st.write("V1 tem carimbo bruto sem fuso documentado e fica em recorte próprio. V2–V4 incluem agregados; V1 e V5 têm detalhe quando a fonte correspondente está configurada. As duas hipóteses de V2–V5 seguem abertas.")
        st.write("N/D representa ausência no recorte. MAE e RMSE em MWmed; MAPE em %. Os blocos 1–24 e 25–48 pertencem ao modelo de 48 h. Validação, teste e retrospectiva de 2026 são exibidos separadamente.")
        st.write("Validação: primeiro semestre de 2025. Teste: segundo semestre de 2025. Retrospectiva: período de 2026 coberto pelos snapshots.")
        st.write(CLOCK_CONTEXT)
        st.markdown(
            "- **V1** integrou carga, temperatura e calendário estático. O carimbo original tem fuso sem documentação.\n"
            "- **V2** reconstruiu os dados brutos, priorizou A621 com apoio de A601 e adotou grade comum para as duas hipóteses. "
            "O calendário passou a considerar os atos conhecidos na emissão, ainda sem tratar revogações. "
            "Ridge 1 foi selecionado em 48 h.\n"
            "- **V3** ajustou a padronização no treino, explicitou a tolerância do OLS e acrescentou verificações "
            "dos dados disponíveis na emissão. O OLS estabilizado foi selecionado também em 48 h.\n"
            "- **V4** corrigiu a verificação do posto da matriz para incidir no OLS, explicitou rótulos e metadados "
            "e registrou os pares de origem e passo em uma reexecução de referência.\n"
            "- **V5** versionou os atos, com vigência e revogação quando documentadas, incorporou eventos locais "
            "verificados e publicou previsões e métricas. A comparação V4 × V5 usa pares e estimadores em comum."
        )
        render_version_examples(tables["globais"], tables["pares"])
        if version in ("Todas", "v5"):
            st.caption("Esta tabela consulta o catálogo histórico de disponibilidade (Piloto e V1–V4). A V5 tem métricas e cobertura em seções próprias nesta aba.")
        subset = _filter(tables["disponibilidade"], horizon, stage, scenario)
        lo, hi = _block_steps(block)
        subset = subset.loc[subset["versao"].isin(order)
                            & (subset["bloco_horas"].eq(block) | subset["bloco_horas"].isna())
                            & (subset["passo_h"].between(lo, hi) | subset["passo_h"].isna())]
        if model is not None:
            subset = subset.loc[subset["modelo"].eq(model) | subset["modelo"].isna()]
        if subset.empty:
            st.caption("Nenhum registro no catálogo histórico para este recorte.")
        else:
            columns = {
                "versao": "Versão", "modelo": "Estimador", "tabela": "Tabela", "bloco_horas": "Bloco",
                "passo_h": "Passo", "hora_alvo_local": "Hora local", "mes_alvo_local": "Mês",
                "campo": "Campo", "status": "Situação", "casas_decimais": "Precisão (casas decimais)",
                "dependencia": "Dependência", "motivo": "Motivo",
            }
            display_catalog = subset[list(columns)].assign(
                versao=subset["versao"].map(version_label),
                modelo=subset["modelo"].map(model_label, na_action="ignore"),
                hora_alvo_local=subset["hora_alvo_local"].map(lambda hour: f"{hour:02.0f} h", na_action="ignore"),
            ).replace({
                "tabela": {
                    "metricas_globais.csv": "Métricas globais", "metricas_por_hora.csv": "Métricas por hora",
                    "metricas_por_mes.csv": "Métricas por mês", "metricas_por_passo.csv": "Métricas por passo",
                },
                "campo": {"__linha__": "Linha inteira", "erro_medio_mwmed": "Erro médio (MWmed)", **versions.METRICS},
                "dependencia": {
                    "fora_do_desenho": "Fora do desenho", "fuso_original": "Fuso original",
                    "pares_originais_ou_reexecucao": "Pares originais ou reexecução",
                },
                "status": {"fora_do_desenho": "Fora do desenho", "indisponivel": "Indisponível", "publicado": "Publicado"},
            })
            data_table(display_catalog, height=320, integer_columns=("passo_h", "casas_decimais"), labels=columns,
                       alt="Disponibilidade no catálogo histórico")


def version_label(version):
    return "Piloto histórico" if version == "piloto" else version.upper()


def _block_steps(block):
    return (25, 48) if block == "25–48 h" else (1, 48 if block == "1–48 h" else 24)


def _step_chart(frame, horizon, stage, scenario, block, role, model, metric):
    st.markdown("#### Erro por passo")
    lo, hi = _block_steps(block)
    steps = _filter(frame, horizon, stage, scenario)
    steps = steps.loc[steps["papel"].eq(role) & steps["passo_h"].between(lo, hi)]
    if model is not None:
        steps = steps.loc[steps["modelo"].eq(model)]
    if steps.empty or not steps[metric].notna().any():
        st.caption("N/D neste recorte.")
        return
    fig = go.Figure()
    for (v, name), run in steps.groupby(["versao", "modelo"], sort=True):
        grid = run.set_index("passo_h").reindex(range(lo, hi + 1))
        fig.add_trace(go.Scatter(x=grid.index, y=grid[metric], name=f"{version_label(v)} · {model_label(name)}", mode="lines+markers",
                                 connectgaps=False, customdata=grid["n_pares"],
                                 hovertemplate="%{x} h · %{y:.4f}<br>Pares: %{customdata}<extra>%{fullData.name}</extra>"))
    fig.update_layout(xaxis_title="Passo (h)", yaxis_title=versions.METRICS[metric], height=340, margin={"t": 15}, separators=",.")
    if lo == 1 and hi == 48:
        fig.add_vline(x=24.5, line_dash="dot", line_color="#52657A")
    st.plotly_chart(fig, width="stretch", config=PLOTLY_CONFIG)


def _paired_section(frame, horizon, stage, scenario, block, role, model, population):
    st.markdown("#### V4 × V5 · pares comuns")
    pairs = _filter(frame, horizon, stage, scenario)
    pairs = pairs.loc[pairs["bloco_horas"].eq(block)]
    if role == "Selecionado":
        v4 = population.loc[population["versao"].eq("v4"), "modelo"]
        v5 = population.loc[population["versao"].eq("v5"), "modelo"]
        pairs = pairs.loc[pairs["modelo"].isin(v5) & pairs["modelo_ref"].isin(v4)]
    elif model is not None:
        pairs = pairs.loc[pairs["modelo"].eq(model)]
    else:
        pairs = pairs.iloc[:0]
    if pairs.empty:
        st.caption("N/D para a seleção atual.")
        return
    pairs = pairs.assign(
        delta_mae_pct=pairs["delta_mae_mwmed"].div(pairs["mae_mwmed_v4"].where(pairs["mae_mwmed_v4"].gt(0))).mul(100),
        delta_rmse_pct=pairs["delta_rmse_mwmed"].div(pairs["rmse_mwmed_v4"].where(pairs["rmse_mwmed_v4"].gt(0))).mul(100),
    )
    labels = {
        "tipo_comparacao": "Tipo de comparação", "modelo_ref": "Estimador V4", "modelo": "Estimador V5",
        "n_pares_comuns": "Pares comuns", "n_mape_validos_comuns": "Pares MAPE",
        "n_excluidos_v4": "Excluídos V4", "n_excluidos_v5": "Excluídos V5",
        "mae_mwmed_v4": "MAE V4 (MWmed)", "mae_mwmed_v5": "MAE V5 (MWmed)",
        "delta_mae_mwmed": "Δ MAE (MWmed)", "delta_mae_pct": "Δ MAE (%)",
        "rmse_mwmed_v4": "RMSE V4 (MWmed)", "rmse_mwmed_v5": "RMSE V5 (MWmed)",
        "delta_rmse_mwmed": "Δ RMSE (MWmed)", "delta_rmse_pct": "Δ RMSE (%)",
        "mape_pct_v4": "MAPE V4 (%)", "mape_pct_v5": "MAPE V5 (%)", "delta_mape_pp": "Δ MAPE (p.p.)",
    }
    display = pairs[list(labels)].assign(
        modelo=pairs["modelo"].map(model_label), modelo_ref=pairs["modelo_ref"].map(model_label),
    ).replace({"tipo_comparacao": {"mesmo_estimador": "Mesmo estimador"}})
    data_table(display, decimals=4, labels=labels)
    st.download_button("Exportar pares comuns", csv_bytes(pairs), file_name="metricas_v4_v5_pares_comuns.csv", mime="text/csv")


def _horizon_summary(frame, stage, scenario, version):
    if version == "Todas":
        version = "v1" if scenario == "sem_cenario_bruto" else "v5"
    rows = frame.loc[frame["etapa"].eq(stage) & frame["cenario"].eq(scenario)
                     & frame["versao"].eq(version) & frame["papel"].isin(["Selecionado", "Referência"])]
    with st.expander(f"24 h × 48 h e referências · {version_label(version)}"):
        st.write("Resultados descritivos por horizonte e bloco. Cada linha conserva os seus próprios pares.")
        if rows.empty:
            st.write("N/D")
            return
        headings = {"horizonte_h": "Horizonte (h)", "bloco_horas": "Bloco", "papel": "Grupo",
                    "modelo": "Estimador", "n_pares": "Pares", "n_mape_validos": "Pares MAPE", **versions.METRICS}
        data_table(rows.sort_values(["horizonte_h", "bloco_horas", "papel"]).assign(modelo=rows["modelo"].map(model_label))[list(headings)].rename(columns=headings),
                   decimals=4, integer_columns=("Pares", "Pares MAPE"))
        st.download_button("Exportar os dois horizontes", csv_bytes(rows), file_name="metricas_por_horizonte.csv", mime="text/csv")


def _episode_section(scenario, stage, horizon, block, model):
    is_legacy = scenario == "sem_cenario_bruto"
    version = "v1" if is_legacy else "v5"
    with st.expander(f"Maiores erros por emissão · {version_label(version)}"):
        if not is_legacy:
            st.caption(f"Nos episódios, a temperatura é observada no horário do alvo. {TEMPERATURE_CONTEXT}")
        if not st.toggle("Consultar episódios", key=f"{version}_query_episodes"):
            return
        lo, hi = _block_steps(block)
        try:
            if is_legacy:
                path = versions.legacy_path() if stage != "validacao_1s2025" else None
                if path is None:
                    st.info("Nenhuma previsão individual V1 disponível neste recorte.")
                    return
                bundle, _ = _legacy(path, versions.LEGACY_SHA)
                subset = versions.legacy_episode_source(bundle, stage, horizon)
                if subset.empty:
                    st.info("Nenhuma previsão individual V1 disponível neste recorte.")
                    return
                model = subset["model_name"].iloc[0]
                month = month_choice("Mês da emissão", subset["month_issued"].unique(),
                                     f"v1_episode_month_{stage}_{horizon}_{block}_{model}")
                rows = versions.legacy_episode_rows(bundle, subset, month, lo, hi)
                preview = False
            else:
                entries = {e["month"]: e for e in versions.detail_index()
                           if (e["scenario"], e["stage"], e["horizon"]) == (scenario, stage, horizon)}
                if not entries:
                    st.info("Nenhuma emissão disponível neste recorte.")
                    return
                preview = next(iter(entries.values()))["preview"]
                if preview:
                    st.markdown("#### Maiores erros horários da amostra exibida")
                    st.caption(f"{preview_coverage(entries.values())} A consulta ordena os erros horários do mês e bloco selecionados.")
                month = month_choice("Mês da emissão (amostra V5)" if preview else "Mês da emissão",
                                     entries, f"v5_episode_month_{scenario}_{stage}_{horizon}_{block}_{model}")
                entry = entries[month]
                path = versions.partition_path(entry)
                if preview and not versions.issues_for_models(path, entry["sha256"])["modelo"].eq(model).any():
                    st.info(f"A prévia V5 não inclui previsões horárias para {model_label(model)} neste recorte.")
                    return
                rows = versions.episode_rows(path, entry["sha256"], model, lo, hi, scenario)
        except (OSError, ValueError, KeyError, URLError) as error:
            st.warning(f"Episódios indisponíveis: {error}")
            return
        if rows.empty:
            st.info("Nenhum par com carga observada disponível para este estimador.")
            return
        columns = st.columns(3)
        with columns[0]:
            weekdays = st.multiselect("Dia da semana do alvo", range(7), format_func=WEEKDAYS.__getitem__, placeholder="Todos os dias da semana", wrap=True)
        with columns[1]:
            days = st.multiselect("Calendário no alvo", sorted(rows["day_type"].unique()), format_func=DAY_LABELS.__getitem__, placeholder="Todas as categorias", wrap=True)
        temperatures = rows["temperature_c"].dropna()
        limits = (float(temperatures.min()), float(temperatures.max()))
        with columns[2]:
            selection = (st.slider("Temperatura no alvo (°C)", *limits, limits, format="localized",
                                   help="Média das estações disponíveis no alvo, para análise retrospectiva.")
                         if limits[0] < limits[1] else limits)
        worst = largest_errors(rows, weekday=weekdays or None, day_types=days or None,
                               temp_range=selection if selection != limits and not temperatures.empty else None, limit=30)
        if worst.empty:
            st.info("Nenhum episódio atende aos filtros.")
            return
        display = worst.assign(day_type=worst["day_type"].map(DAY_LABELS), holiday_scope=worst["holiday_scope"].map(scope_label, na_action="ignore"))
        for column in ("issued_at", "timestamp"):
            display[column] = display[column].dt.tz_convert(versions.TZ).dt.strftime("%d/%m/%Y %H:%M")
        headings = {"issued_at": "Emissão", "timestamp": "Alvo", "forecast_step": "Passo",
                    "observed_load": "Observado (MWmed)", "predicted_load": "Previsto (MWmed)",
                    "absolute_error": "Erro absoluto (MWmed)", "day_type": "Calendário",
                    "holiday_scope": "Âmbito", "temperature_c": "Temp. (°C)"}
        if "event_name" in display:
            headings["event_name"] = "Eventos"
        st.caption("Emissão e alvo no horário de São Paulo.")
        data_table(display[list(headings)].rename(columns=headings), height=390,
                   column_decimals={"Temp. (°C)": 1}, alt="Maiores erros horários e eventos")
        # O CSV de episódios conserva o código de âmbito primário do calendário.
        export = worst.assign(holiday_scope=worst["holiday_scope"].str.split("+").str[0],
                              alvo_id=versions.TARGET, unidade="MWmed", versao=version, modelo=model,
                              cenario=scenario, etapa=stage, horizonte_h=horizon, bloco_horas=block,
                              mes_emissao=month, amostra=preview)
        st.download_button("Exportar episódios", csv_bytes(export), file_name=f"maiores_erros_{version}.csv", mime="text/csv")


def render_seasonality(render_profiles):
    from components.sidebar import SidebarSettings
    from services.data_loader import DataBundle

    st.header("Sazonalidade, Clima e Calendário")
    scenario = choice("Hipótese de horário", list(versions.SCENARIOS)[:2], "v5_patterns_scenario", versions.SCENARIOS)
    station = choice("Estação", ["Média disponível", "A621", "A601"], "v5_patterns_station",
                     {"Média disponível": "Média disponível", "A621": "A621 · Vila Militar", "A601": "A601 · Seropédica"})
    try:
        value = versions.load_scenario(str(versions.root()), scenario)
    except (OSError, ValueError, KeyError) as error:
        st.warning(f"Série auditada indisponível: {error}")
        return
    settings = SidebarSettings("v5", 24, versions.REGION,
                               station=None if station == "Média disponível" else station)
    bundle = DataBundle("v5", [], value.observations, [], weather=value.weather, calendar=value.calendar)
    with st.expander("Temperatura observada e série dos modelos V5"):
        st.write(f"Em Carga × Temperatura, as medições correspondem ao horário da carga. {TEMPERATURE_CONTEXT}")
        st.write(TARGET_CONTEXT)
    render_profiles((bundle, settings))
    with st.expander("Inventário versionado e pendências"):
        st.write(CALENDAR_CONTEXT)
        st.write("Conhecido desde e Conhecido até usam o horário de São Paulo.")
        st.write("A série horária auditada V5 usa os IDs ativos na própria hora. O alcance de cada ato consta no inventário. As pendências abaixo não entram nas classificações.")
        labels = {"evento_versao_id": "ID da versão do evento", "data_local": "Data local", "nome_evento": "Evento",
                  "esfera": "Esfera", "alcance": "Alcance", "conhecido_desde": "Conhecido desde",
                  "conhecido_ate": "Conhecido até", "fonte_url": "Fonte"}
        events = pd.DataFrame(list(value.events.values()), columns=list(labels))
        pending = value.pending.copy()
        for table in (events, pending):
            table["data_local"] = pd.to_datetime(table["data_local"], format="%Y-%m-%d").dt.strftime("%d/%m/%Y")
        for column in ("conhecido_desde", "conhecido_ate"):
            for table in (events, pending):
                if column in table:
                    table[column] = pd.to_datetime(table[column], utc=True).dt.tz_convert(versions.TZ).dt.strftime("%d/%m/%Y %H:%M")
        events["esfera"] = events["esfera"].map(scope_label, na_action="ignore")
        pending["tipo_proposto"] = pending["tipo_proposto"].replace({"feriado_local_a_confirmar": "Feriado local a confirmar"})
        pending["esfera_proposta"] = pending["esfera_proposta"].replace({
            "municipal_territorios_SECO_nao_auditados": "Municipal — territórios do SE/CO a auditar",
        })
        pending["acao"] = pending["acao"].str.replace("MANTER_EXCLUIDO", "Manter excluído", regex=False)
        data_table(events, height=300, labels=labels)
        data_table(pending, height=220, labels={
            **labels, "tipo_proposto": "Tipo proposto", "esfera_proposta": "Esfera proposta",
            "ato_ou_fonte": "Ato ou fonte", "alcance_horario_pendente": "Alcance horário pendente",
            "motivo_pendencia": "Motivo da pendência", "acao": "Ação",
        })
