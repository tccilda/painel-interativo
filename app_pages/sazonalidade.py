"""Sazonalidade, clima em janela controlada e calendário municipal."""

from datetime import timedelta

import pandas as pd
import streamlit as st

from components.charts import PLOTLY_CONFIG, annual_chart, calendar_profile_chart, daily_pattern_chart, history_chart, load_temperature_chart, monthly_chart, temperature_scatter, weekly_pattern_chart
from components.metrics_cards import format_number
from components.page_frame import DAY_LABELS, page_header, scope_label
from components.tables import data_table
from services.history_service import filter_history, region_history
from services.pattern_service import aggregate_load_temperature, annual_profile, calendar_coverage, calendar_hourly_profile, calendar_observations, join_weather, monthly_profile


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
    hours = calendar_observations(history, bundle.calendar, settings.region, settings.timezone)
    if bundle.calendar.empty or hours.empty or hours["day_type"].eq("nao_informado").all():
        st.info("Calendário não informado para o período.")
    else:
        coverage = calendar_coverage(hours)
        categories = coverage.index.tolist()
        selected = st.multiselect(
            "Categorias de calendário", categories, default=categories,
            format_func=lambda pair: DAY_LABELS[pair[0]] if pair[1] == "nenhum" else f"{DAY_LABELS[pair[0]]} · {scope_label(pair[1])}",
            key=f"calendar_categories_{history_key}", placeholder="Selecione as categorias", wrap=True,
        )
        shown = coverage.loc[coverage.index.isin(selected)]
        eligible = shown.loc[shown["civil_dates"].ge(5) & (shown.index.get_level_values("day_type") != "nao_informado")]
        hour_keys = pd.MultiIndex.from_frame(hours[["day_type", "holiday_scope"]])
        selected_hours = hours.loc[hour_keys.isin(shown.index)]
        profile = calendar_hourly_profile(hours.loc[hour_keys.isin(eligible.index)])
        if profile.empty:
            st.info("Nenhuma categoria selecionada atende ao critério de cinco datas civis observadas.")
        else:
            st.plotly_chart(calendar_profile_chart(profile, unit=settings.unit), width="stretch", config=PLOTLY_CONFIG)

        total = int(coverage["observed_hours"].sum())
        if not shown.empty:
            counts = shown.reset_index()
            counts["day_type"] = counts["day_type"].map(DAY_LABELS)
            counts["holiday_scope"] = counts["holiday_scope"].map(scope_label)
            counts["% das horas observadas"] = counts["observed_hours"] / total * 100
            counts["Tamanho da amostra"] = counts["civil_dates"].map(
                lambda dates: "Rara · menos de 5 datas" if dates < 5 else "5 datas ou mais"
            )
            data_table(counts.rename(columns={"day_type": "Calendário", "holiday_scope": "Âmbito",
                                             "observed_hours": "Horas", "civil_dates": "Datas civis distintas"}),
                       alt="Horas observadas, datas civis e cobertura por categoria do calendário")
        with st.expander("Amostra do calendário"):
            expected = pd.date_range(pd.Timestamp(period[0]).tz_localize(settings.timezone),
                                     pd.Timestamp(period[1] + timedelta(days=1)).tz_localize(settings.timezone),
                                     inclusive="left", freq="h")
            expected_hours = int(expected.year.isin(selected_years).sum())
            ratio = f"{format_number(100 * total / expected_hours, 2)}%" if expected_hours else "N/D"
            st.write(f"{format_number(total, 0)} de {format_number(expected_hours, 0)} h esperadas no período "
                     f"e nos anos selecionados ({ratio}).")
            st.write("O perfil exige cinco datas civis distintas com observações por categoria. "
                     "O limiar é exploratório e não garante significância estatística.")
            counts_by_hour = selected_hours.groupby(["hour", "day_type", "holiday_scope"]).size().rename("Observações").reset_index()
            counts_by_hour["hour"] = counts_by_hour["hour"].map(lambda hour: f"{hour:02d}:00")
            counts_by_hour["day_type"] = counts_by_hour["day_type"].map(DAY_LABELS)
            counts_by_hour["holiday_scope"] = counts_by_hour["holiday_scope"].map(scope_label)
            data_table(counts_by_hour.rename(columns={"hour": "Hora", "day_type": "Calendário", "holiday_scope": "Âmbito"}),
                       alt="Número de observações por hora e categoria")
            rare = shown.loc[shown["civil_dates"].lt(5)]
            rare_hours = hours.loc[hour_keys.isin(rare.index), ["timestamp", "day_type", "holiday_scope", "observed_load"]].copy()
            if not rare_hours.empty:
                st.markdown("**Registros horários de categorias raras**")
                rare_hours["timestamp"] = rare_hours["timestamp"].dt.tz_convert(settings.timezone).dt.strftime("%d/%m/%Y %H:%M %z")
                rare_hours["day_type"] = rare_hours["day_type"].map(DAY_LABELS)
                rare_hours["holiday_scope"] = rare_hours["holiday_scope"].map(scope_label)
                data_table(rare_hours, height=260, labels={"timestamp": "Data e hora local", "day_type": "Calendário",
                           "holiday_scope": "Âmbito", "observed_load": f"Carga observada ({settings.unit})"},
                           alt="Registros horários das categorias raras")
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
            st.write("A621 fica na Vila Militar (Rio de Janeiro) e A601 em Seropédica. As medições meteorológicas e os eventos do Rio contextualizam a série de carga regional. Sua cobertura é local.")
        if bundle.mode == "demo":
            st.write("O calendário e todas as demais variáveis são sintéticos; não são fontes oficiais.")
    with st.expander("Histórico horário"):
        st.plotly_chart(history_chart(history, settings.timezone, unit=settings.unit), width="stretch", config=PLOTLY_CONFIG)
