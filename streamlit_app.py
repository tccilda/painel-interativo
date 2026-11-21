"""Entrada do painel de previsão de carga elétrica, local ou hospedado."""

import os

import streamlit as st

from services import model_versions

from app_pages import desempenho, explorador, sazonalidade
from components.sidebar import render_sidebar, select_data_mode
from services.app_data import has_model_files, imported_config_path, load_app_context


APP_NAME = "Monitor de Previsão"
APP_SUBTITLE = "Painel Interativo de Previsão de Demanda Energética"


def main() -> None:
    st.set_page_config(
        page_title=APP_NAME,
        page_icon=":material/electric_bolt:",
        layout="wide",
        initial_sidebar_state="auto",
    )
    st.markdown(
        """<style>
        .block-container { max-width: 1560px; padding: 3.3rem 1.8rem 1.8rem; }
        h1 { letter-spacing: -.025em; font-size: 1.9rem !important; line-height: 1.2 !important; }
        h3 { font-size: 1.25rem !important; }
        [data-testid="stMainBlockContainer"] [data-testid="stVerticalBlock"] { gap: .65rem; }
        [data-testid="stMetricValue"] { font-variant-numeric: tabular-nums; font-size: clamp(1.1rem, 1.4vw, 1.4rem); }
        [data-testid="stMetricLabel"] p { white-space: normal !important; overflow: visible !important; text-overflow: clip !important; }
        [data-testid="stMetricValue"] > div { white-space: normal !important; overflow: visible !important; text-overflow: clip !important; }
        [data-testid="stSidebar"] { border-right: 1px solid #d9e2ef; }
        [data-testid="stSidebar"] .block-container { padding: .6rem 1rem; }
        button:focus-visible, a:focus-visible { outline: 3px solid #087f8c; }
        </style>""",
        unsafe_allow_html=True,
    )
    # A versão pública usa somente fontes reais. A demonstração é uma opção
    # explícita de desenvolvimento/teste, nunca um fallback de dados ausentes.
    mode = select_data_mode(
        has_imported=imported_config_path().is_file(),
        has_versions=model_versions.enabled(),
        has_model_files=has_model_files(),
        allow_demo=os.environ.get("ENERGY_FORECAST_ALLOW_DEMO", "").strip().lower() == "true",
    )
    st.session_state["version_catalog_mode"] = mode == "versions"
    if mode != "versions":
        with st.spinner("Carregando os dados locais…"):
            bundle, catalog = load_app_context(mode)
        settings = render_sidebar(bundle, catalog)
        st.session_state["data_bundle"] = bundle
        st.session_state["app_settings"] = settings
        st.session_state["forecast_catalog"] = catalog

    navigation = st.navigation(
        [
            st.Page(explorador.render, title="Explorador de Previsões", icon=":material/show_chart:", url_path="explorador", default=True),
            st.Page(desempenho.render, title="Avaliação de Desempenho e Erros", icon=":material/analytics:", url_path="desempenho"),
            st.Page(sazonalidade.render, title="Sazonalidade, Clima e Calendário", icon=":material/calendar_month:", url_path="sazonalidade"),
        ],
        position="top",
    )
    st.title(APP_NAME, anchor=False)
    st.markdown(f"*{APP_SUBTITLE}*")
    navigation.run()


if __name__ == "__main__":
    main()
