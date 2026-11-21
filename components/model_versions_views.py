"""Controles e visões do catálogo experimental V1–V5."""

from datetime import timedelta
from urllib.error import URLError

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from components.charts import WEEKDAYS, explorer_chart
from components.metrics_cards import format_number, metric_cards
from components.page_frame import DAY_LABELS, SCOPE_LABELS
from components.tables import csv_bytes, data_table
from services import model_versions as versions
from services.analysis_service import largest_errors, temperature_at_issue
from services.forecast_catalog import forecast_catalog


def choice(label, options, key, labels=None):
    return st.selectbox(label, options, key=key, format_func=(labels or {}).get if labels else str)


def month_choice(label, months, key):
    options = sorted(months, reverse=True)
    labels = {month: f"{month[5:]}/{month[:4]}" for month in options}
    return choice(label, options, key, labels)


def header(title):
    st.header(title)
    st.caption("ONS Sudeste/Centro-Oeste · ONS_SECO_piloto · MWmed")


@st.cache_resource(show_spinner=False)
def _legacy(path, sha):
    bundle = versions.legacy_bundle(path, sha)
    return bundle, forecast_catalog(bundle)


def render_explorer(legacy_render):
    header("Explorador de Previsões")
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
        horizon = st.radio("Horizonte", [24, 48], horizontal=True, key="v5_explorer_horizon")
    with columns[3]:
        history_hours = st.selectbox("Histórico anterior", [72, 48, 120, 168], format_func=lambda v: f"{v} h", key="v5_explorer_history")
    entries = {e["month"]: e for e in index if (e["scenario"], e["stage"], e["horizon"]) == (scenario, stage, horizon)}
    with st.expander("Detalhes metodológicos"):
        st.write("V2–V4 têm apenas métricas agregadas, em Avaliação de Desempenho e Erros.")
        if not legacy_available:
            st.write("As previsões horárias da V1 estão disponíveis em instalações com o ZIP legado.")
        st.write("A V5 reúne previsões retrospectivas sobre snapshots fechados.")
        if preview:
            st.write(f"Amostra V5: {len(index)} emissões reais do manifesto, uma por hipótese, etapa e horizonte. As métricas usam as amostras completas declaradas.")
        st.write("As duas hipóteses têm o mesmo estatuto. O carimbo oficial e sua borda seguem indeterminados. Emissões e alvos são armazenados em UTC e exibidos em America/Sao_Paulo. Eventos versionados refletem a informação disponível na origem segundo a hipótese do pacote.")
    if not entries:
        st.info("Nenhuma emissão no recorte selecionado.")
        return
    month = month_choice("Mês da emissão (amostra V5)" if preview else "Mês da emissão", entries, "v5_month")
    entry = entries[month]
    path = versions.partition_path(entry)
    catalog = versions.issues_for_models(path, entry["sha256"])
    models = sorted(catalog["modelo"].unique(), key=lambda name: (not catalog.loc[catalog["modelo"].eq(name), "eh_selecionado"].eq(1).any(), name))
    model = choice("Estimador", models, f"v5_model_{scenario}_{stage}_{horizon}_{month}")
    options = catalog.loc[catalog["modelo"].eq(model), "origem_t"]
    times = pd.to_datetime(options, utc=True).dt.tz_convert(versions.TZ)
    dates = sorted(times.dt.date.unique(), reverse=True)
    cols = st.columns(2)
    with cols[0]:
        day = st.selectbox("Data da emissão", dates, format_func=lambda value: value.strftime("%d/%m/%Y"), key="v5_date")
    with cols[1]:
        issue = st.selectbox("Hora / execução", sorted(options.loc[times.dt.date.eq(day)], reverse=True),
                             format_func=lambda value: pd.Timestamp(value).tz_convert(versions.TZ).strftime("%H:%M %z"), key="v5_issue")
    data = versions.forecast_detail(path, entry["sha256"], horizon, model, issue)
    observed = versions.load_scenario(str(versions.root()), scenario)
    t0 = pd.Timestamp(issue)
    _render_forecast(data, observed, t0, horizon, scenario, stage, history_hours)


def _render_forecast(data, observed, t0, horizon, scenario, stage, history_hours):
    future = data.rename(columns={"instante_alvo": "timestamp", "y_real": "observed_load",
                                  "y_pred": "predicted_load", "y_baseline_semanal": "seasonal_load"})
    future = future.assign(timestamp=pd.to_datetime(future["timestamp"], utc=True), phase="previsão")
    future.loc[future["timestamp"].gt(pd.Timestamp.now(tz="UTC")), "observed_load"] = float("nan")
    previous = observed.observations
    previous = previous.loc[(previous["timestamp"] <= t0) & (previous["timestamp"] > t0 - timedelta(hours=history_hours))]
    columns = ["timestamp", "observed_load", "predicted_load", "seasonal_load", "phase"]
    frame = pd.concat([previous.assign(predicted_load=float("nan"), seasonal_load=float("nan"), phase="histórico")[columns], future[columns]], ignore_index=True)
    peak = future.loc[future["predicted_load"].idxmax()]
    temperature = temperature_at_issue(observed.weather, t0, versions.REGION)
    labels = [versions.classify(row, observed.events) for row in data.itertuples(index=False)]
    mae = (future.predicted_load - future.observed_load).abs().mean()
    metric_cards([
        {"label": "Pico previsto", "value": f"{format_number(peak.predicted_load)} MWmed"},
        {"label": "Horário do pico", "value": peak.timestamp.tz_convert(versions.TZ).strftime("%H:%M · %d/%m")},
        {"label": "Temperatura em t₀", "value": f"{format_number(temperature['temperature_c'])} °C" if temperature else "N/D"},
        {"label": "MAE da emissão", "value": f"{format_number(mae, 2)} MWmed" if pd.notna(mae) else "N/D",
         "help": f"{future.observed_load.count()} de {horizon} horas com carga observada."},
    ])
    figure = explorer_chart(frame, t0)
    figure.add_trace(go.Scatter(x=future["timestamp"].dt.tz_convert(versions.TZ), y=data["y_baseline_persistencia"],
                                name="Persistência", mode="lines", line={"dash": "dot"}))
    st.plotly_chart(figure, width="stretch", config={"displaylogo": False})
    with st.expander("Valores horários e calendário"):
        counts = pd.Series([DAY_LABELS[x[0]] for x in labels]).value_counts(sort=False)
        st.write(" · ".join(f"{kind}: {count} h" for kind, count in counts.items()))
        role = "Selecionado" if data["eh_selecionado"].iloc[0] else (
            "Piloto" if data["modelo"].iloc[0] == "piloto_so_carga" else "Alternativa"
        )
        st.write(f"Grupo do estimador · {role}")
        exported = data.assign(versao="v5", alvo_id=versions.TARGET, horizonte_h=horizon, cenario=scenario,
                               etapa=stage, unidade="MWmed", y_real=future["observed_load"])
        display = exported.assign(calendario=[DAY_LABELS[x[0]] for x in labels],
                                  ambito=[SCOPE_LABELS[x[1]] for x in labels],
                                  eventos=[x[2] for x in labels])
        display["instante_local"] = future["timestamp"].dt.tz_convert(versions.TZ).dt.strftime("%d/%m/%Y %H:%M %z")
        headings = {"passo_h": "Passo", "instante_local": "Alvo local", "y_real": "Observado (MWmed)",
                    "y_pred": "Previsto (MWmed)", "y_baseline_semanal": "Semanal (MWmed)",
                    "y_baseline_persistencia": "Persistência (MWmed)", "calendario": "Calendário",
                    "ambito": "Âmbito", "eventos": "Eventos", "evento_versao_ids": "IDs de evento"}
        data_table(display[list(headings)].rename(columns=headings))
        st.download_button("Exportar emissão V5", csv_bytes(display), file_name=f"v5_{horizon}h.csv", mime="text/csv")


def _filter(frame, horizon, stage, scenario):
    return frame.loc[frame["horizonte_h"].eq(horizon) & frame["etapa"].eq(stage) & frame["cenario"].eq(scenario)]


def render_evolution():
    header("Avaliação de Desempenho e Erros")
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
        horizon = st.radio("Horizonte", [24, 48], horizontal=True, key="evolution_horizon")
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
    roles = ["Selecionado", "Alternativa", "Piloto", "Referência"]
    left, right = st.columns(2)
    with left:
        role = choice("Grupo de estimadores", roles, "evolution_role")
    with right:
        metric = choice("Indicador dos gráficos", list(versions.METRICS), "evolution_metric", versions.METRICS)
    population = _filter(tables["globais"], horizon, stage, scenario)
    population = population.loc[population["bloco_horas"].eq(block) & population["papel"].eq(role)]
    model = None
    if role != "Selecionado":
        choices = population if version == "Todas" else population.loc[population["versao"].eq(version)]
        models = sorted(choices["modelo"].unique())
        if models:
            model = choice("Estimador", models, "evolution_model")
            population = population.loc[population["modelo"].eq(model)]
    if population["versao"].duplicated().any():
        st.warning("Há mais de uma linha para a mesma versão no recorte. Selecione um estimador único.")
        return
    order = list(versions.VERSIONS) if version == "Todas" else [version]
    if version == "Todas" and role == "Piloto" and scenario == "sem_cenario_bruto":
        order.insert(0, "piloto")
    display = population.set_index("versao").reindex(order).reset_index()
    display["versao"] = display["versao"].str.upper()
    if display[metric].notna().any():
        fig = px.scatter(display, x="versao", y=metric, hover_data=["modelo", "n_pares"],
                         labels={"versao": "Versão", "modelo": "Estimador", "n_pares": "Pares",
                                 metric: versions.METRICS[metric]})
        fig.update_traces(marker_size=10)
        fig.update_layout(height=300, margin={"t": 15}, separators=",.")
        fig.update_xaxes(categoryorder="array", categoryarray=[v.upper() for v in order])
        st.plotly_chart(fig, width="stretch", config={"displaylogo": False})
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
            data_table(display_civil, height=320, labels={
                "versao": "Versão", "modelo": "Estimador", civil_key: "Hora local" if granularity == "por_hora" else "Mês",
                "n_pares": "Pares", **versions.METRICS,
            })
    with st.expander("Disponibilidade e detalhes metodológicos"):
        st.write("A comparação V4 × V5 usa os pares comuns fornecidos. Os deltas são V5 − V4 e a variação do MAPE é expressa em pontos percentuais.")
        st.write("V1 tem carimbo bruto sem fuso documentado e fica em recorte próprio. V2–V4 incluem agregados; V1 e V5 têm detalhe quando a fonte correspondente está configurada. As duas hipóteses de V2–V5 seguem abertas.")
        st.write("N/D representa ausência no recorte. MAE e RMSE em MWmed; MAPE em %. Os blocos 1–24 e 25–48 pertencem ao modelo de 48 h. Validação, teste e retrospectiva de 2026 são exibidos separadamente.")
        st.write("Validação: primeiro semestre de 2025. Teste: segundo semestre de 2025. Retrospectiva: período de 2026 coberto pelos snapshots.")
        st.write("V1: carimbo bruto. V2: hipóteses de horário. V3: ajuste OLS estabilizado. V4: reexecução retrospectiva. V5: calendário versionado e comparação com pares comuns.")
        availability = tables["disponibilidade"]
        subset = _filter(availability, horizon, stage, scenario)
        if not subset.empty:
            data_table(subset[["versao", "modelo", "tabela", "campo", "status", "motivo"]], height=320, labels={
                "versao": "Versão", "modelo": "Estimador", "tabela": "Tabela", "campo": "Campo",
                "status": "Situação", "motivo": "Motivo",
            })


def _step_chart(frame, horizon, stage, scenario, block, role, model, metric):
    st.markdown("#### Erro por passo")
    lo, hi = (25, 48) if block == "25–48 h" else (1, 48) if block == "1–48 h" else (1, 24)
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
        fig.add_trace(go.Scatter(x=grid.index, y=grid[metric], name=f"{v.upper()} · {name}", mode="lines+markers",
                                 connectgaps=False, customdata=grid["n_pares"],
                                 hovertemplate="%{x} h · %{y:.4f}<br>Pares: %{customdata}<extra>%{fullData.name}</extra>"))
    fig.update_layout(xaxis_title="Passo (h)", yaxis_title=versions.METRICS[metric], height=340, margin={"t": 15}, separators=",.")
    if lo == 1 and hi == 48:
        fig.add_vline(x=24.5, line_dash="dot", line_color="#52657A")
    st.plotly_chart(fig, width="stretch", config={"displaylogo": False})


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
    data_table(pairs[list(labels)], decimals=4, labels=labels)
    st.download_button("Exportar pares comuns", csv_bytes(pairs), file_name="metricas_v4_v5_pares_comuns.csv", mime="text/csv")


def _horizon_summary(frame, stage, scenario, version):
    if version == "Todas":
        version = "v1" if scenario == "sem_cenario_bruto" else "v5"
    rows = frame.loc[frame["etapa"].eq(stage) & frame["cenario"].eq(scenario)
                     & frame["versao"].eq(version) & frame["papel"].isin(["Selecionado", "Referência"])]
    with st.expander(f"24 h × 48 h e referências · {version.upper()}"):
        st.write("Resultados descritivos por horizonte e bloco. Cada linha conserva os seus próprios pares.")
        if rows.empty:
            st.write("N/D")
            return
        headings = {"horizonte_h": "Horizonte (h)", "bloco_horas": "Bloco", "papel": "Grupo",
                    "modelo": "Estimador", "n_pares": "Pares", "n_mape_validos": "Pares MAPE", **versions.METRICS}
        data_table(rows.sort_values(["horizonte_h", "bloco_horas", "papel"])[list(headings)].rename(columns=headings),
                   decimals=4, integer_columns=("Pares", "Pares MAPE"))
        st.download_button("Exportar os dois horizontes", csv_bytes(rows), file_name="metricas_por_horizonte.csv", mime="text/csv")


def _episode_section(scenario, stage, horizon, block, model):
    is_legacy = scenario == "sem_cenario_bruto"
    version = "v1" if is_legacy else "v5"
    with st.expander(f"Maiores erros por emissão · {version.upper()}"):
        if not st.toggle("Consultar episódios", key=f"{version}_query_episodes"):
            return
        lo, hi = (25, 48) if block == "25–48 h" else (1, 48 if block == "1–48 h" else 24)
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
                month = month_choice("Mês da emissão", subset["month_issued"].unique(), "v1_episode_month")
                rows = versions.legacy_episode_rows(bundle, subset, month, lo, hi)
                preview = False
            else:
                entries = {e["month"]: e for e in versions.detail_index()
                           if (e["scenario"], e["stage"], e["horizon"]) == (scenario, stage, horizon)}
                if not entries:
                    st.info("Nenhuma emissão disponível neste recorte.")
                    return
                preview = next(iter(entries.values()))["preview"]
                month = month_choice("Mês da emissão (amostra V5)" if preview else "Mês da emissão",
                                     entries, "v5_episode_month")
                entry = entries[month]
                rows = versions.episode_rows(versions.partition_path(entry), entry["sha256"], model, lo, hi, scenario)
        except (OSError, ValueError, KeyError, URLError) as error:
            st.warning(f"Episódios indisponíveis: {error}")
            return
        if rows.empty:
            st.info("Nenhum par com carga observada disponível para este estimador.")
            return
        columns = st.columns(3)
        with columns[0]:
            weekdays = st.multiselect("Dia da semana do alvo", range(7), format_func=WEEKDAYS.__getitem__)
        with columns[1]:
            days = st.multiselect("Calendário no alvo", sorted(rows["day_type"].unique()), format_func=DAY_LABELS.__getitem__)
        temperatures = rows["temperature_c"].dropna()
        limits = (float(temperatures.min()), float(temperatures.max()))
        with columns[2]:
            selection = (st.slider("Temperatura no alvo (°C)", *limits, limits,
                                   help="Média das estações disponíveis no alvo, para análise retrospectiva.")
                         if limits[0] < limits[1] else limits)
        worst = largest_errors(rows, weekday=weekdays or None, day_types=days or None,
                               temp_range=selection if selection != limits and not temperatures.empty else None, limit=30)
        if worst.empty:
            st.info("Nenhum episódio atende aos filtros.")
            return
        display = worst.assign(day_type=worst["day_type"].map(DAY_LABELS), holiday_scope=worst["holiday_scope"].map(SCOPE_LABELS))
        for column in ("issued_at", "timestamp"):
            display[column] = display[column].dt.tz_convert(versions.TZ).dt.strftime("%d/%m/%Y %H:%M %z")
        headings = {"issued_at": "Emissão", "timestamp": "Alvo", "forecast_step": "Passo",
                    "observed_load": "Observado (MWmed)", "predicted_load": "Previsto (MWmed)",
                    "absolute_error": "Erro absoluto (MWmed)", "day_type": "Calendário",
                    "holiday_scope": "Âmbito", "temperature_c": "Temp. (°C)"}
        data_table(display[list(headings)].rename(columns=headings), height=390)
        export = worst.assign(alvo_id=versions.TARGET, unidade="MWmed", versao=version, modelo=model,
                              cenario=scenario, etapa=stage, horizonte_h=horizon, bloco_horas=block,
                              mes_emissao=month, amostra=preview)
        st.download_button("Exportar episódios", csv_bytes(export), file_name=f"maiores_erros_{version}.csv", mime="text/csv")


def render_seasonality(render_profiles):
    from components.sidebar import SidebarSettings
    from services.data_loader import DataBundle

    header("Sazonalidade, Clima e Calendário")
    scenario = choice("Hipótese de horário", list(versions.SCENARIOS)[:2], "v5_patterns_scenario", versions.SCENARIOS)
    station = choice("Estação", ["Média disponível", "A621", "A601"], "v5_patterns_station",
                     {"Média disponível": "Média disponível", "A621": "A621 · Vila Militar", "A601": "A601 · Seropédica"})
    try:
        value = versions.load_scenario(str(versions.root()), scenario)
    except (OSError, ValueError, KeyError) as error:
        st.warning(f"Série auditada indisponível: {error}")
        return
    settings = SidebarSettings(scenario, 24, versions.REGION,
                               station=None if station == "Média disponível" else station)
    bundle = DataBundle("v5", [], value.observations, [], weather=value.weather, calendar=value.calendar)
    render_profiles((bundle, settings))
    with st.expander("Inventário versionado e pendências"):
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
                    table[column] = pd.to_datetime(table[column], utc=True).dt.tz_convert(versions.TZ).dt.strftime("%d/%m/%Y %H:%M %z")
        data_table(events, height=300, labels=labels)
        data_table(pending, height=220, labels={
            **labels, "tipo_proposto": "Tipo proposto", "esfera_proposta": "Esfera proposta",
            "ato_ou_fonte": "Ato ou fonte", "alcance_horario_pendente": "Alcance horário pendente",
            "motivo_pendencia": "Motivo da pendência", "acao": "Ação",
        })
