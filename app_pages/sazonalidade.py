"""Sazonalidade, clima em janela controlada e calendário municipal."""

from datetime import timedelta

import pandas as pd
import streamlit as st

from components.charts import PLOTLY_CONFIG, annual_chart, calendar_profile_chart, daily_pattern_chart, history_chart, load_temperature_chart, monthly_chart, temperature_scatter, weekly_pattern_chart
from components.metrics_cards import format_number
from components.page_frame import CALENDAR_CONTEXT, DAY_LABELS, page_header, scope_label
from components.tables import data_table
from services.history_service import filter_history, region_history
from services.pattern_service import aggregate_load_temperature, annual_profile, calendar_profile, join_weather, monthly_profile


def render() -> None:
    if st.session_state.get("version_catalog_mode"):
        from components.model_versions_views import render_seasonality

        render_seasonality(_render_profiles)
    else:
        _render_profiles()


def _date_range(label, default_start, first, last, key):
    previous = st.session_state.get(key, ())
    if len(previous) == 2:
        overlap = (max(previous[0], first), min(previous[1], last))
        if overlap[0] <= overlap[1] and overlap != previous:
            st.session_state[key] = overlap
    return st.date_input(label, value=(default_start, last), min_value=first, max_value=last, format="DD/MM/YYYY", key=key)


def _render_profiles(context=None) -> None:
    bundle, settings = context or page_header("Sazonalidade, Clima e Calendário")
    observations = region_history(bundle.observations, settings.region, unit=settings.unit)
    if observations.empty:
        st.info("Nenhuma carga observada disponível.")
        return
    local = observations["timestamp"].dt.tz_convert(settings.timezone)
    observations = observations.loc[local.dt.year.between(2024, 2026)]
    if observations.empty:
        st.info("Nenhuma observação disponível entre 2024 e 2026.")
        return
    dates = observations["timestamp"].dt.tz_convert(settings.timezone).dt.date
    controls = st.columns([1.3, 1])
    with controls[0]:
        first, last = dates.min(), dates.max()
        period = _date_range("Período da análise", first, first, last,
                             f"patterns_period_{settings.mode}_{settings.region}_{settings.unit}")
    if len(period) != 2:
        st.info("Selecione o início e o fim do período.")
        return
    history = filter_history(observations, period[0], period[1], settings.timezone)
    years = sorted(history["timestamp"].dt.tz_convert(settings.timezone).dt.year.unique().tolist())
    period_key = settings.mode if settings.mode == "v5" else f"{settings.mode}_{period[0]}_{period[1]}"
    with controls[1]:
        selected_years = st.multiselect("Anos", years, default=years, placeholder="Selecione os anos", key=f"patterns_years_{period_key}", wrap=True)
    history = history.loc[history["timestamp"].dt.tz_convert(settings.timezone).dt.year.isin(selected_years)]
    if history.empty:
        st.info("Nenhuma observação no período selecionado.")
        return
    st.subheader("Sazonalidade")
    left, right = st.columns(2)
    with left:
        st.plotly_chart(daily_pattern_chart(history, settings.timezone, unit=settings.unit), width="stretch", config=PLOTLY_CONFIG)
    with right:
        st.plotly_chart(weekly_pattern_chart(history, settings.timezone, unit=settings.unit), width="stretch", config=PLOTLY_CONFIG)
    month_column, year_column = st.columns(2)
    with month_column:
        st.plotly_chart(monthly_chart(monthly_profile(history, settings.timezone), unit=settings.unit), width="stretch", config=PLOTLY_CONFIG)
    with year_column:
        st.plotly_chart(annual_chart(annual_profile(history, settings.timezone), unit=settings.unit), width="stretch", config=PLOTLY_CONFIG)
    st.subheader("Carga × Temperatura")
    climate_dates = history["timestamp"].dt.tz_convert(settings.timezone).dt.date
    first, last = climate_dates.min(), climate_dates.max()
    climate_controls = st.columns([1.3, 1])
    history_key = period_key if settings.mode == "v5" else f"{period_key}_{selected_years}"
    with climate_controls[0]:
        climate_period = _date_range("Intervalo climático", max(first, last - timedelta(days=29)),
                                     first, last, f"climate_period_{history_key}")
    with climate_controls[1]:
        frequency = st.radio(
            "Resolução temporal", ["daily", "weekly", "hourly"], horizontal=True,
            help="A série horária mostra até as últimas 168 h do intervalo. A dispersão usa todos os pares selecionados.",
            format_func=lambda value: {"daily": "Diária", "weekly": "Semanal", "hourly": "Horária"}[value],
            key=f"climate_resolution_{settings.mode}",
        )
    if len(climate_period) == 2:
        climate_history = filter_history(history, climate_period[0], climate_period[1], settings.timezone)
        matched = join_weather(climate_history, bundle.weather, settings.region, station=settings.station, timezone=settings.timezone)
        if matched.empty:
            st.info("Sem temperatura observada correspondente ao intervalo.")
        else:
            scatter = temperature_scatter(matched, unit=settings.unit, timezone=settings.timezone)
            scatter.update_layout(title_text=None, margin={"t": 20})
            st.plotly_chart(scatter, width="stretch", config=PLOTLY_CONFIG)
            temporal = matched
            if frequency == "hourly" and (matched["timestamp"].max().value - matched["timestamp"].min().value) > 168 * 3_600_000_000_000:
                boundary = pd.Timestamp(matched["timestamp"].max().value - 168 * 3_600_000_000_000, tz="UTC")
                temporal = matched.loc[matched["timestamp"] > boundary]
            aggregated = aggregate_load_temperature(temporal, frequency=frequency, timezone=settings.timezone)
            st.plotly_chart(load_temperature_chart(aggregated, unit=settings.unit, timezone=settings.timezone, frequency=frequency), width="stretch", config=PLOTLY_CONFIG)
    else:
        st.info("Selecione as duas datas do intervalo climático.")
    st.subheader("Carga por tipo de dia")
    profile = calendar_profile(history, bundle.calendar, settings.region, settings.timezone)
    if bundle.calendar.empty or profile.empty or profile["day_type"].eq("nao_informado").all():
        st.info("Calendário não informado para o período.")
    else:
        if bundle.mode == "v5":
            st.caption(CALENDAR_CONTEXT)
        sample = profile.groupby(["day_type", "holiday_scope"])["count"].sum()
        categories = sample.index.tolist()
        selected = st.multiselect(
            "Categorias de calendário", categories, default=categories,
            format_func=lambda pair: DAY_LABELS[pair[0]] if pair[1] == "nenhum" else f"{DAY_LABELS[pair[0]]} · {scope_label(pair[1])}",
            key=f"calendar_categories_{history_key}", placeholder="Selecione as categorias", wrap=True,
        )
        profile = profile.loc[pd.MultiIndex.from_frame(profile[["day_type", "holiday_scope"]]).isin(selected)]
        if profile.empty:
            st.info("Selecione uma categoria para exibir o perfil.")
        else:
            st.plotly_chart(calendar_profile_chart(profile, unit=settings.unit), width="stretch", config=PLOTLY_CONFIG)
        shown = sample.loc[sample.index.isin(selected)]
        st.caption(
            f"{format_number(shown.sum(), 0)} h únicas nas categorias exibidas · "
            f"{format_number(sample.sum(), 0)} h no recorte. Grupos de até 120 h (5 dias equivalentes) "
            "aparecem com traço pontilhado."
        )
        counts = shown.rename("Horas").reset_index()
        counts["Dias equivalentes"] = counts["Horas"].div(24).map(lambda days: format_number(days, 1))
        counts["Tamanho da amostra"] = counts["Horas"].map(
            lambda hours: "Apenas 1 dia equivalente" if hours == 24 else "Grupo pequeno" if hours <= 120 else "Mais de 5 dias"
        )
        if not counts.empty:
            counts["day_type"] = counts["day_type"].map(DAY_LABELS)
            counts["holiday_scope"] = counts["holiday_scope"].map(scope_label)
            data_table(counts, labels={"day_type": "Calendário", "holiday_scope": "Âmbito"},
                       alt="Horas e dias equivalentes por categoria do calendário")
        with st.expander("Amostra do calendário"):
            display = profile.copy()
            display["hour"] = display["hour"].map(lambda hour: f"{hour:02d}:00")
            display["day_type"] = display["day_type"].map(DAY_LABELS).fillna("Não informado")
            display["holiday_scope"] = display["holiday_scope"].map(scope_label)
            data_table(display.rename(columns={"hour": "Hora", "day_type": "Calendário", "holiday_scope": "Âmbito", "mean": f"Média ({settings.unit})", "count": "Observações"}))
    with st.expander("Detalhes metodológicos"):
        st.write("Perfis são médias das cargas horárias disponíveis, sem extrapolar períodos incompletos. Contagens estão no hover. As análises usam somente 2024–2026 e observações já ocorridas.")
        st.write("A dispersão mantém todos os pares exatos do intervalo climático, com transparência e renderização WebGL. Não há interpolação, imputação ou conclusão causal.")
        st.write("A série climática usa médias somente dos pares disponíveis: dia local ou semana iniciada na segunda-feira. Períodos sem pares permanecem como lacunas. Dois eixos preservam as unidades de carga e temperatura; agregações são apenas visuais e não alteram modelos ou métricas.")
        st.write(f"Estação: {settings.station or 'média das estações disponíveis em cada instante'}. O número de estações pode variar.")
        st.write("Sazonalidade e calendário usam o período da análise; clima usa seu intervalo próprio. Na resolução horária, a série temporal é limitada a 168 h para manter a leitura.")
        if bundle.mode == "v5":
            st.write("A classificação horária vem dos IDs de evento conhecidos naquele instante. Quando atos coexistem, o perfil reúne os âmbitos na mesma categoria e conta a hora uma vez.")
        st.write("Prioridade do calendário: feriado > ponto facultativo > fim de semana > dia útil. O ponto facultativo aplica-se ao âmbito administrativo indicado, sem implicar paralisação de toda a economia. Datas sem classificação permanecem não informadas.")
        if bundle.mode == "v5":
            st.write("A621 fica na Vila Militar (Rio de Janeiro) e A601 em Seropédica. Os dados locais contextualizam uma série de carga regional.")
        if bundle.mode == "demo":
            st.write("O calendário e todas as demais variáveis são sintéticos; não são fontes oficiais.")
    with st.expander("Histórico horário"):
        st.plotly_chart(history_chart(history, settings.timezone, unit=settings.unit), width="stretch", config=PLOTLY_CONFIG)
