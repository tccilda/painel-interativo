"""Fonte e contexto global; filtros da análise ficam na respectiva página."""

from dataclasses import dataclass

import pandas as pd
import streamlit as st

from services.data_loader import DataBundle


@dataclass(frozen=True)
class SidebarSettings:
    mode: str
    horizon_hours: int
    region: str | None
    timezone: str = "America/Sao_Paulo"
    unit: str = "MWmed"
    station: str | None = None


def select_data_mode(
    has_imported: bool = False, allow_demo: bool = False, has_versions: bool = False,
    has_model_files: bool = False,
) -> str:
    """Demonstração exige habilitação explícita, sem fallback de fontes reais."""
    if has_versions:
        options = ["Catálogo V1–V5"]
        if has_model_files:
            options.append("Arquivos dos modelos")
    else:
        options = ["Arquivos dos modelos"]
        if has_imported:
            options.insert(0, "Base do grupo (CSV)")
    if allow_demo:
        options.append("Demonstração")
    if "source_mode" in st.session_state and st.session_state["source_mode"] not in options:
        st.session_state["source_mode"] = options[0]
    labels = {"Catálogo V1–V5": "versions", "Demonstração": "demo",
              "Arquivos dos modelos": "real", "Base do grupo (CSV)": "provided"}
    if len(options) == 1:
        return labels[options[0]]
    label = st.sidebar.selectbox(
        "Fonte", options, key="source_mode",
        help="As fontes são isoladas. Dados ausentes ou incompatíveis não são substituídos por simulação.",
    )
    return labels[label]


def render_sidebar(bundle: DataBundle, catalog: pd.DataFrame) -> SidebarSettings:
    regions = set(catalog["region"].unique()) if not catalog.empty else set()
    if not bundle.observations.empty:
        regions.update(bundle.observations["region"].unique())
    options = sorted(regions)
    region = options[0] if options else None
    # Séries distintas podem ter metadados próprios, mas não mudam o alvo territorial.
    if len(options) > 1:
        region = st.sidebar.selectbox("Série municipal", options, key=f"region_{bundle.mode}")
    units = set(catalog.loc[catalog["region"] == region, "unit"].unique()) if not catalog.empty else set()
    if region is not None and not bundle.observations.empty:
        units.update(bundle.observations.loc[bundle.observations["region"] == region, "unit"].unique())
    unit_options = sorted(units, key=lambda value: (value != "MWmed", value))
    unit = unit_options[0] if unit_options else "MWmed"
    if len(unit_options) > 1:
        unit = st.sidebar.selectbox(
            "Série / unidade", unit_options, key=f"unit_{bundle.mode}",
            format_func=lambda value: f"Série em {value}",
            help="Seleciona séries físicas distintas. Não converte MW em MWmed nem altera rótulos.",
        )
    stations = []
    if region is not None and not bundle.weather.empty:
        stations = sorted(bundle.weather.loc[bundle.weather["region"] == region, "station"].unique())
    station = None
    if stations:
        selected = st.sidebar.selectbox(
            "Estação", ["Média disponível"] + stations, key=f"station_{bundle.mode}_{region}",
            help="Média das estações disponíveis em cada instante. Estações externas ou sem localização verificada não entram na visão municipal.",
        )
        station = None if selected == "Média disponível" else selected
    return SidebarSettings(bundle.mode, 24, region, unit=unit, station=station)
