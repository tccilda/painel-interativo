"""Explorador compacto: uma emissão, quatro indicadores e quatro curvas."""

from dataclasses import replace

import pandas as pd
import streamlit as st

from components.charts import explorer_chart
from components.metrics_cards import format_number, metric_cards
from components.page_frame import DAY_LABELS, SCOPE_LABELS, SPLIT_LABELS, forecast_details, forecast_picker, format_timestamp, get_catalog, page_header
from components.tables import data_table
from services.analysis_service import calendar_for_targets, explorer_frame, temperature_at_issue
from services.forecast_service import export_forecast_csv, forecast_summary, prepare_evaluation
from services.metrics_service import calculate_metrics


def render() -> None:
    if st.session_state.get("version_catalog_mode"):
        from components.model_versions_views import render_explorer

        render_explorer(_render_legacy)
    else:
        _render_legacy()


def _render_legacy(context=None, catalog=None) -> None:
    bundle, settings = context or page_header("Explorador de Previsões")
    candidates = get_catalog(bundle, settings) if catalog is None else catalog
    controls = st.columns([1.15, 1, 1])
    available_splits = set(candidates["dataset_split"])
    splits = [value for value in ("forecast_2026", "test_2025", "validation_2025", "unspecified") if value in available_splits]
    with controls[0]:
        split = st.selectbox(
            "Conjunto", splits or ["unspecified"], format_func=lambda value: "Retrospectiva 2026" if settings.mode == "v1" and value == "forecast_2026" else SPLIT_LABELS[value],
            disabled=not splits, key=f"explorer_split_{settings.mode}",
        )
    subset = candidates.loc[candidates["dataset_split"] == split]
    available_horizons = [value for value in (24, 48) if value in set(subset["horizon_hours"])]
    with controls[1]:
        horizon = st.radio(
            "Horizonte" if settings.mode == "v1" else "Modelo", available_horizons or [24, 48], horizontal=True,
            format_func=lambda value: f"{value} h", key="selected_horizon", disabled=not available_horizons,
        )
    settings = replace(settings, horizon_hours=horizon)
    with controls[2]:
        history_hours = st.selectbox("Histórico anterior", [48, 72, 120, 168], index=1, format_func=lambda value: f"{value} h")
    available = subset.loc[subset["horizon_hours"] == horizon]
    models = sorted(set(zip(available["model_name"], available["model_version"])))
    if len(models) > 1:
        model = st.selectbox("Modelo / versão", models, format_func=lambda value: f"{value[0]} · {value[1]}")
        available = available.loc[(available["model_name"] == model[0]) & (available["model_version"] == model[1])]
    forecast = forecast_picker(bundle, settings, "explorer_run", candidates=available)
    if forecast is None:
        return
    summary = forecast_summary(forecast)
    aligned = prepare_evaluation(forecast, bundle.observations)
    try:
        metrics = calculate_metrics(aligned)
    except ValueError as exc:
        st.error(f"Erro indisponível: {exc}")
        metrics = {"mae": None, "n_pairs": 0}
    temperature = temperature_at_issue(bundle.weather, forecast.issued_at, forecast.region, station=settings.station)
    calendar = calendar_for_targets(forecast, bundle.calendar)
    peak = summary["peak_timestamp"].tz_convert(settings.timezone)
    first, last = forecast.predictions["timestamp"].iloc[[0, -1]]
    retrospective = last <= pd.Timestamp.now(tz="UTC")
    kind = "Previsão retrospectiva" if retrospective else "Previsão com alvos futuros"
    metric_cards([
        {"label": "Pico previsto", "value": f"{format_number(summary['peak_load'])} {forecast.unit}", "help": "Maior carga prevista da emissão. Em caso de empate, exibe-se o primeiro pico."},
        {"label": "Horário do pico", "value": peak.strftime("%H:%M · %d/%m"), "help": format_timestamp(peak)},
        {"label": "Temperatura em t₀", "value": f"{format_number(temperature['temperature_c'])} °C" if temperature else "N/D", "help": "Última medição de cada estação até t₀, com no máximo 1 h de defasagem. Nenhuma leitura posterior à emissão é utilizada."},
        {"label": "MAE da emissão", "value": f"{format_number(metrics['mae'], 2)} {forecast.unit}" if metrics["mae"] is not None else "N/D", "help": f"Erro absoluto médio nos {metrics['n_pairs']} pares disponíveis, de {horizon} alvos."},
    ])
    counts = calendar["day_type"].value_counts()
    distribution = [f"{DAY_LABELS[kind]} {int(counts.get(kind, 0))} h" for kind in ("dia_util", "fim_de_semana", "feriado", "ponto_facultativo")]
    if counts.get("nao_informado", 0):
        distribution.append(f"Não informado {int(counts['nao_informado'])} h")
    st.caption("Calendário · " + " · ".join(distribution))
    st.subheader("Histórico × Previsão")
    frame = explorer_frame(forecast, bundle.observations, history_hours=history_hours)
    figure = explorer_chart(frame, forecast.issued_at, unit=forecast.unit, timezone=settings.timezone)
    figure.update_layout(title_text=None, margin={"t": 20})
    st.plotly_chart(figure, width="stretch", config={"displaylogo": False})
    if 0 < metrics["n_pairs"] < horizon:
        st.warning(f"MAE parcial: {metrics['n_pairs']} de {horizon} pares disponíveis.")
    with st.expander("Detalhes metodológicos"):
        forecast_details(forecast, settings)
        st.write(f"{kind} · {first.tz_convert(settings.timezone):%d/%m %H:%M} → {last.tz_convert(settings.timezone):%d/%m %H:%M}")
        st.write("Comparações em UTC; exibição em America/Sao_Paulo. A semana anterior usa o alvo menos 168 h, disponível até t₀. Lacunas não são preenchidas.")
        st.write(f"Amostra do MAE: {metrics['n_pairs']} de {horizon} pares. Sem observado correspondente, o erro fica N/D.")
        if temperature:
            st.write(f"Temperatura: {temperature['station_count']} estação(ões), de {format_timestamp(temperature['oldest_timestamp'])} a {format_timestamp(temperature['timestamp'])}. Seleção: {settings.station or 'média disponível'}.")
        else:
            st.write("Sem temperatura observada válida no instante de emissão.")
        st.write("Calendário: feriado > ponto facultativo > fim de semana > dia útil quando os indicadores se sobrepõem. Ponto facultativo administrativo não significa paralisação geral da economia. Datas sem classificação permanecem não informadas.")
        if bundle.mode == "demo":
            st.write("Carga, temperatura, calendário e previsões são artificiais; não representam precisão de modelos treinados ou calendário oficial.")
        else:
            st.write("O recorte municipal foi declarado na fonte; a declaração não substitui a comprovação da origem. A separação de treino/validação/teste deve ser documentada pelos responsáveis.")
    with st.expander("Valores horários e calendário"):
        hourly = frame.loc[frame["phase"].eq("previsão"), ["timestamp", "predicted_load", "observed_load", "seasonal_load"]]
        table = hourly.merge(calendar.drop(columns="date"), on="timestamp", validate="one_to_one")
        table["timestamp"] = table["timestamp"].dt.tz_convert(settings.timezone).dt.strftime("%d/%m/%Y %H:%M %z")
        table["day_type"] = table["day_type"].map(DAY_LABELS).fillna("Não informado")
        table["holiday_scope"] = table["holiday_scope"].map(SCOPE_LABELS).fillna("Não informado")
        data_table(table.rename(columns={
            "timestamp": "Hora prevista", "predicted_load": f"Previsto ({forecast.unit})",
            "observed_load": f"Observado ({forecast.unit})", "seasonal_load": f"Semanal ({forecast.unit})",
            "day_type": "Calendário", "holiday_scope": "Âmbito", "event_name": "Evento",
        }))
        st.download_button(
            "Exportar previsão", data=export_forecast_csv(forecast),
            file_name=f"{'sintetico' if bundle.mode == 'demo' else 'previsao'}_{horizon}h_{forecast.issued_at.strftime('%Y%m%dT%H%M%SZ')}.csv",
            mime="text/csv", icon=":material/download:",
        )
