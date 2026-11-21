"""Contexto municipal, avisos necessários e seletores de emissão."""

import pandas as pd
import streamlit as st

from components.sidebar import SidebarSettings
from components.metrics_cards import format_number
from contracts.forecast_schema import Forecast
from services.data_loader import DataBundle
from services.forecast_catalog import forecast_catalog, materialize_forecast
from services.geography_service import TARGET_REGION, geographic_status, municipal_bundle
from services.history_service import future_observation_count

SPLIT_LABELS = {
    "validation_2025": "Validação 2025", "test_2025": "Teste 2025",
    "forecast_2026": "Forecast 2026", "unspecified": "Não classificado",
}
DAY_LABELS = {
    "dia_util": "Dia útil", "fim_de_semana": "Fim de semana", "feriado": "Feriado",
    "ponto_facultativo": "Ponto facultativo", "nao_informado": "Não informado",
}
SCOPE_LABELS = {
    "nacional": "Nacional", "estadual": "Estadual", "municipal": "Municipal",
    "federal_administracao": "Administração pública federal",
    "nenhum": "Sem evento", "nao_informado": "Não informado",
}


def get_context() -> tuple[DataBundle, SidebarSettings]:
    # Também protege páginas chamadas diretamente, fora do ponto de entrada.
    bundle = municipal_bundle(st.session_state["data_bundle"])
    return bundle, st.session_state["app_settings"]


def get_catalog(bundle: DataBundle, settings: SidebarSettings) -> pd.DataFrame:
    catalog = st.session_state.get("forecast_catalog")
    if catalog is None:
        catalog = forecast_catalog(bundle)
    return catalog.loc[(catalog["region"] == settings.region) & (catalog["unit"] == settings.unit)].copy()


def format_timestamp(value: pd.Timestamp, timezone: str = "America/Sao_Paulo") -> str:
    return pd.Timestamp(value).tz_convert(timezone).strftime("%d/%m/%Y %H:%M %z")


def page_header(title: str) -> tuple[DataBundle, SidebarSettings]:
    bundle, settings = get_context()
    st.header(title)
    st.caption(f"{TARGET_REGION}, RJ · {settings.unit} · America/Sao_Paulo")
    audit = bundle.provenance.get("geographic_audit") or geographic_status(bundle)
    if audit["status"] == "incompatible":
        st.error("Base incompatível com o recorte municipal. " + audit["reason"])
        with st.expander("Evidência geográfica", expanded=True):
            evidence = audit.get("evidence", {})
            if evidence:
                st.write(f"{format_number(evidence['matched_hours'], 0)} horas de 2024 coincidem com o ONS, com diferença máxima de {evidence['max_absolute_difference_mwmed']:.2g} MWmed.")
            if audit.get("evidence_url"):
                st.markdown(f"[Fonte oficial da comparação]({audit['evidence_url']})")
            st.write("O alvo continua sendo o município do Rio de Janeiro. Os arquivos originais foram preservados; é necessária uma série municipal para habilitar estas análises.")
            outside = audit.get("outside_municipality_weather_stations", [])
            if outside:
                st.write("Estações fora do município: " + ", ".join(outside) + ". A601 pertence a Seropédica.")
        st.stop()
    if bundle.mode == "demo":
        st.warning("Modo demonstração — dados sintéticos", icon=":material/science:")
    future_count = future_observation_count(bundle.observations, settings.region, unit=settings.unit)
    if future_count:
        st.warning(f"{future_count} registros futuros foram excluídos das análises.")
    if bundle.issues:
        with st.expander(f"Avisos dos dados ({len(bundle.issues)})"):
            for issue in bundle.issues:
                st.warning(str(issue))
    return bundle, settings


def forecast_picker(
    bundle: DataBundle, settings: SidebarSettings, key: str,
    candidates: pd.DataFrame | None = None,
) -> Forecast | None:
    catalog = get_catalog(bundle, settings) if candidates is None else candidates
    catalog = catalog.loc[catalog["horizon_hours"] == settings.horizon_hours].sort_values("issued_at", ascending=False).reset_index(drop=True)
    if catalog.empty:
        st.info("Nenhuma previsão disponível para esta seleção.")
        return None
    dates = catalog["issued_at"].dt.tz_convert(settings.timezone).dt.date
    date_options = sorted(dates.unique(), reverse=True)
    left, right = st.columns([1, 1.6])
    with left:
        selected_date = st.selectbox(
            "Data da emissão", date_options, format_func=lambda value: value.strftime("%d/%m/%Y"),
            key=f"{key}_date_{settings.mode}_{settings.horizon_hours}_{settings.region}_{settings.unit}",
        )
    catalog = catalog.loc[dates == selected_date].reset_index(drop=True)
    with right:
        index = st.selectbox(
            "Hora / execução", list(range(len(catalog))),
            format_func=lambda index: f"{pd.Timestamp(catalog.iloc[index]['issued_at']).tz_convert(settings.timezone).strftime('%H:%M')} · {catalog.iloc[index]['model_name']}",
            key=f"{key}_{settings.mode}_{settings.horizon_hours}_{settings.region}_{settings.unit}",
        )
    return materialize_forecast(bundle, str(catalog.iloc[index]["forecast_id"]))


def forecast_details(forecast: Forecast, settings: SidebarSettings) -> None:
    st.write(f"Modelo: {forecast.model_name} · Versão: {forecast.model_version}")
    st.write(f"Região declarada: {forecast.region} · Unidade: {forecast.unit}")
    stage = "Retrospectiva 2026" if settings.mode == "v1" and forecast.dataset_split == "forecast_2026" else SPLIT_LABELS.get(forecast.dataset_split, forecast.dataset_split)
    st.write(f"Conjunto: {stage}")
    st.write(f"Emissão: {format_timestamp(forecast.issued_at, settings.timezone)}")
    if forecast.source_path:
        st.write(f"Arquivo: {forecast.source_path.name}")
