"""Gráficos reutilizáveis; os valores nunca são interpolados ou completados."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from services.pattern_service import daily_profile, weekly_profile


NAVY = "#243B53"
TEAL = "#007F82"
MUTED = "#52657A"
GRID = "#E7EDF3"
RED = "#B6465F"
DEFAULT_TIMEZONE = "America/Sao_Paulo"
WEEKDAYS = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]


def _base_chart(title: str, *, x_title: str = "Data/hora", y_title: str = "Carga (MW)", height: int = 360) -> go.Figure:
    figure = go.Figure()
    figure.update_layout(
        title={"text": title, "font": {"size": 15, "color": NAVY}, "x": 0},
        template="plotly_white",
        font={"family": "Arial, sans-serif", "size": 13, "color": NAVY},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin={"l": 12, "r": 16, "t": 40, "b": 64},
        height=height,
        hovermode="closest",
        hoverlabel={"bgcolor": "white", "font_color": NAVY},
        legend={
            "orientation": "h", "yanchor": "bottom", "y": 0.0,
            "xanchor": "left", "x": 0.0, "yref": "container", "xref": "container",
            "font": {"size": 12},
        },
        separators=",.",
        dragmode="zoom",
    )
    figure.update_xaxes(title_text=x_title, gridcolor=GRID, zeroline=False, showline=False, automargin=True)
    figure.update_yaxes(title_text=y_title, gridcolor=GRID, zeroline=False, tickformat=",.0f", automargin=True)
    return figure


def _empty_chart(title: str, timezone: str) -> go.Figure:
    figure = _base_chart(title, x_title=f"Data/hora local · {timezone}")
    figure.add_annotation(
        text="Não há dados no período selecionado.",
        x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False,
        font={"color": MUTED, "size": 14},
    )
    figure.update_xaxes(visible=False)
    figure.update_yaxes(visible=False)
    return figure


def _local_times(timestamps: pd.Series, timezone: str) -> pd.Series:
    """A escala visual é local; o hover mantém o deslocamento UTC de cada ponto."""
    return pd.to_datetime(timestamps, utc=True).dt.tz_convert(timezone)


def _add_line(
    figure: go.Figure,
    frame: pd.DataFrame,
    column: str,
    name: str,
    color: str,
    timezone: str,
    *,
    dash: str = "solid",
    unit: str = "MW",
    yaxis: str = "y",
    frequency: str = "hourly",
) -> None:
    if frame.empty or not frame[column].notna().any():
        return
    ordered = frame.sort_values("timestamp")
    local = _local_times(ordered["timestamp"], timezone)
    utc = pd.to_datetime(ordered["timestamp"], utc=True)
    if "period_end" in ordered:
        gaps = utc.gt(pd.to_datetime(ordered["period_end"], utc=True).shift())
    elif frequency == "hourly":
        gaps = utc.diff().dt.total_seconds().gt(3600)
    else:
        interval_hours = {"daily": 24, "weekly": 168}[frequency]
        gaps = local.dt.tz_localize(None).diff().dt.total_seconds().gt(interval_hours * 3600)
    valid = ordered[column].notna().to_numpy()
    gap_values = gaps.to_numpy()
    isolated = [
        bool(valid[index])
        and not (index > 0 and valid[index - 1] and not gap_values[index])
        and not (index + 1 < len(valid) and valid[index + 1] and not gap_values[index + 1])
        for index in range(len(valid))
    ]
    labels = local.dt.strftime("%d/%m/%Y %H:%M · UTC%z").tolist()
    if "n_pairs" in ordered:
        for index, count in enumerate(ordered["n_pairs"]):
            if pd.notna(count):
                labels[index] += f"<br>Pares: {int(count)}"
                if "expected_hours" in ordered and pd.notna(ordered["expected_hours"].iloc[index]):
                    labels[index] += f" / {ordered['expected_hours'].iloc[index]:g} h possíveis"
    x_values, y_values, hover_values, marker_sizes = [], [], [], []
    for timestamp, value, label, gap, single in zip(
        local.dt.tz_localize(None), ordered[column],
        labels, gaps, isolated,
    ):
        if gap:
            # Interrompe a linha quando faltam observações horárias.
            x_values.append(None)
            y_values.append(None)
            hover_values.append("")
            marker_sizes.append(0)
        x_values.append(timestamp)
        y_values.append(value)
        hover_values.append(label)
        marker_sizes.append(3 if single else 0)
    figure.add_trace(go.Scatter(
        x=x_values,
        y=y_values,
        customdata=hover_values,
        name=name,
        mode="lines+markers" if any(isolated) else "lines",
        marker={"size": marker_sizes, "color": color},
        line={"color": color, "width": 2.6, "dash": dash},
        yaxis=yaxis,
        connectgaps=False,
        hovertemplate="%{customdata}<br>" + name + ": <b>%{y:,.2f} " + unit + "</b><extra></extra>",
    ))


def history_chart(observations: pd.DataFrame, timezone: str = DEFAULT_TIMEZONE, unit: str = "MW") -> go.Figure:
    if observations.empty:
        return _empty_chart("Carga observada no período", timezone)
    figure = _base_chart("Carga observada no período", x_title=f"Data/hora local · {timezone}", y_title=f"Carga ({unit})")
    _add_line(figure, observations, "observed_load", "Carga observada", NAVY, timezone, unit=unit)
    figure.update_xaxes(tickformat="%d/%m<br>%H:%M")
    figure.update_layout(showlegend=False, margin={"b": 48})
    return figure


def daily_pattern_chart(observations: pd.DataFrame, timezone: str = DEFAULT_TIMEZONE, unit: str = "MW") -> go.Figure:
    if observations.empty:
        return _empty_chart("Perfil médio por hora do dia", timezone)
    summary = daily_profile(observations, timezone)
    figure = _base_chart(
        "Perfil horário", x_title=f"Hora local · {timezone}", y_title=f"Carga média ({unit})",
    )
    figure.add_trace(go.Scatter(
        x=summary.index, y=summary["mean"], customdata=summary["count"],
        mode="lines+markers", name="Média das observações do período",
        line={"color": TEAL, "width": 2.6}, marker={"size": 6},
        hovertemplate="Hora: %{x:02d}h<br>Carga média: <b>%{y:,.2f} " + unit + "</b><br>%{customdata} observações<extra></extra>",
        connectgaps=False,
    ))
    figure.update_xaxes(tickmode="array", tickvals=list(range(0, 24, 3)), ticktext=[f"{hour:02d}h" for hour in range(0, 24, 3)])
    daily = summary["mean"].dropna()
    if not daily.empty and daily.min() < daily.max():
        for label, hour, offset in (("Maior média", daily.idxmax(), -30), ("Menor média", daily.idxmin(), 28)):
            figure.add_annotation(x=hour, y=daily[hour], text=f"{label} · {hour:02d} h", showarrow=True, ay=offset)
    figure.update_layout(showlegend=False, margin={"b": 48})
    return figure


def weekly_pattern_chart(observations: pd.DataFrame, timezone: str = DEFAULT_TIMEZONE, unit: str = "MW") -> go.Figure:
    if observations.empty:
        return _empty_chart("Carga média por dia da semana", timezone)
    summary = weekly_profile(observations, timezone)
    labels = [WEEKDAYS[index] for index in summary.index]
    figure = _base_chart(
        "Perfil semanal", x_title="Dia da semana", y_title=f"Carga média ({unit})",
    )
    figure.add_trace(go.Bar(
        x=labels, y=summary["mean"], customdata=summary["count"],
        name="Média das observações do período", marker_color=TEAL,
        hovertemplate="%{x}<br>Carga média: <b>%{y:,.2f} " + unit + "</b><br>%{customdata} observações<extra></extra>",
    ))
    figure.update_xaxes(categoryorder="array", categoryarray=WEEKDAYS)
    figure.update_yaxes(rangemode="tozero")
    figure.update_layout(showlegend=False, margin={"b": 48})
    return figure


def _mark_issuance(figure: go.Figure, issued_at: pd.Timestamp, timezone: str) -> None:
    origin = pd.Timestamp(issued_at)
    if origin.tzinfo is None:
        raise ValueError("A data de emissão deve conter fuso horário.")
    local = origin.tz_convert(timezone)
    x_value = local.tz_localize(None)
    figure.add_shape(
        type="line", x0=x_value, x1=x_value, y0=0, y1=1, xref="x", yref="paper",
        line={"color": "#8594A4", "dash": "dot", "width": 1},
    )
    figure.add_annotation(
        x=x_value, y=0.98, yref="paper", yanchor="top", xanchor="left", xshift=4, showarrow=False,
        text="t₀", hovertext=f"Emissão: {local.strftime('%d/%m/%Y %H:%M · UTC%z')}",
        font={"color": MUTED, "size": 11}, bgcolor="rgba(255,255,255,0.85)",
    )


def explorer_chart(
    frame: pd.DataFrame, issued_at: pd.Timestamp, unit: str = "MWmed",
    timezone: str = DEFAULT_TIMEZONE,
) -> go.Figure:
    """Mostra contexto, modelo, observados dos alvos e baseline semanal separados."""
    if frame.empty:
        return _empty_chart("Explorador de previsões", timezone)
    figure = _base_chart(
        "Histórico × Previsão", x_title=f"Data/hora local · {timezone}", y_title=f"Carga ({unit})", height=460,
    )
    phases = frame["phase"].astype(str).str.casefold()
    historical = frame.loc[phases.isin(["historico", "histórico", "history", "historical"])]
    target = frame.loc[phases.isin(["previsao", "previsão", "forecast", "prediction"])]
    _add_line(figure, historical, "observed_load", "Histórico", NAVY, timezone, unit=unit)
    _add_line(figure, target, "predicted_load", "Previsto", TEAL, timezone, dash="dash", unit=unit)
    _add_line(figure, target, "observed_load", "Real", "#7751A8", timezone, unit=unit)
    _add_line(figure, target, "seasonal_load", "Semana anterior", "#9C5700", timezone, dash="dot", unit=unit)
    _mark_issuance(figure, issued_at, timezone)
    figure.update_xaxes(tickformat="%d/%m<br>%H:%M")
    figure.update_layout(margin={"b": 70})
    return figure


def degradation_chart(by_lead: pd.DataFrame, unit: str = "MWmed", metric: str = "mae") -> go.Figure:
    if metric not in {"mae", "rmse", "mape"}:
        raise ValueError("Selecione uma métrica de erro: mae, rmse ou mape.")
    if by_lead.empty:
        return _empty_chart("Erro por passo", DEFAULT_TIMEZONE)
    if metric not in by_lead:
        raise ValueError(f"A curva de erro não contém a métrica {metric.upper()}.")
    if not by_lead[metric].notna().any():
        return _empty_chart("Erro por passo", DEFAULT_TIMEZONE)
    step_column = "forecast_step" if "forecast_step" in by_lead else "lead_hour"
    metric_unit = "%" if metric == "mape" else unit
    figure = _base_chart("Erro por passo", x_title="Passo da previsão (h)", y_title=f"{metric.upper()} ({metric_unit})")
    keys = [column for column in ("model_label", "model_name", "model_version", "horizon_hours") if column in by_lead]
    groups = list(by_lead.groupby(keys, sort=True, dropna=False, observed=True)) if keys else [("Modelo", by_lead)]
    base_labels = [str(rows.iloc[0].get("model_label", f"{rows.iloc[0].get('horizon_hours', '')} h")) for _, rows in groups]
    colors = [TEAL, NAVY, "#7751A8", "#9C5700"]
    for index, (_, rows) in enumerate(groups):
        rows = rows.sort_values(step_column)
        first = rows.iloc[0]
        label = base_labels[index]
        if base_labels.count(label) > 1 and "model_name" in rows:
            label += " · " + str(first["model_name"])
        x_values, y_values, counts = [], [], []
        previous = None
        for record in rows.to_dict("records"):
            step = record[step_column]
            if previous is not None and step - previous > 1:
                x_values.append(None)
                y_values.append(None)
                counts.append([None, None, None])
            x_values.append(step)
            y_values.append(record[metric])
            counts.append([record.get("n_pairs"), record.get("mape_valid_pairs"), record.get("mape_excluded_zeros")])
            previous = step
        sample_hover = ""
        if "n_pairs" in rows:
            sample_hover = "<br>Pares totais: %{customdata[0]:,.0f}"
        if metric == "mape" and {"mape_valid_pairs", "mape_excluded_zeros"}.issubset(rows.columns):
            sample_hover += "<br>Pares MAPE: %{customdata[1]:,.0f}<br>Zeros excluídos: %{customdata[2]:,.0f}"
        figure.add_trace(go.Scatter(
            x=x_values, y=y_values, customdata=counts, mode="lines+markers", name=label,
            line={"color": colors[index % len(colors)], "width": 2.4, "dash": "solid" if index % 2 == 0 else "dash"},
            marker={"size": 4}, connectgaps=False,
            hovertemplate="Passo: %{x:g}<br>" + metric.upper() + ": <b>%{y:,.2f} " + metric_unit + "</b>" + sample_hover + "<extra>%{fullData.name}</extra>",
        ))
    figure.update_xaxes(tickmode="array", tickvals=[1, 6, 12, 18, 24, 30, 36, 42, 48], range=[0.5, 48.5])
    # Erros podem ser inferiores a uma unidade. A precisão automática mantém
    # marcas como 0,5 e 1,5 distintas, inclusive em MAPE expresso em percentual.
    figure.update_yaxes(rangemode="tozero", tickformat=None)
    return figure


def temperature_scatter(frame: pd.DataFrame, unit: str = "MWmed", timezone: str = DEFAULT_TIMEZONE) -> go.Figure:
    if frame.empty:
        return _empty_chart("Carga e temperatura", DEFAULT_TIMEZONE)
    figure = _base_chart("Carga × Temperatura", x_title="Temperatura (°C)", y_title=f"Carga observada ({unit})")
    colors = [TEAL, NAVY, "#7751A8", "#9C5700"]
    groups = frame.groupby("station", sort=True, observed=True) if "station" in frame else [("Temperatura observada", frame)]
    for index, (station, rows) in enumerate(groups):
        time_labels = _local_times(rows["timestamp"], timezone).dt.strftime("%d/%m/%Y %H:%M · UTC%z") if "timestamp" in rows else [""] * len(rows)
        figure.add_trace(go.Scattergl(
            x=rows["temperature_c"], y=rows["observed_load"], mode="markers", name=str(station),
            customdata=time_labels,
            marker={"color": colors[index % len(colors)], "opacity": 0.55, "size": 4},
            hovertemplate="%{customdata}<br>Temperatura: %{x:.1f} °C<br>Carga: <b>%{y:,.2f} " + unit + "</b><extra>%{fullData.name}</extra>",
        ))
    figure.update_layout(showlegend=frame["station"].nunique() > 1 if "station" in frame else False)
    return figure


def load_temperature_chart(
    frame: pd.DataFrame, unit: str = "MWmed", timezone: str = DEFAULT_TIMEZONE,
    frequency: str = "hourly",
) -> go.Figure:
    if frequency not in {"hourly", "daily", "weekly"}:
        raise ValueError("Frequência visual inválida; use hourly, daily ou weekly.")
    if frame.empty:
        return _empty_chart("Carga e temperatura no tempo", timezone)
    label = {"hourly": "horária", "daily": "média diária", "weekly": "média semanal"}[frequency]
    figure = _base_chart(
        f"Carga × Temperatura · {label}", x_title=f"Início do período · {timezone}" if frequency != "hourly" else f"Data/hora local · {timezone}",
        y_title=f"Carga {'média' if frequency != 'hourly' else 'observada'} ({unit})",
    )
    _add_line(figure, frame, "observed_load", "Carga", NAVY, timezone, unit=unit, frequency=frequency)
    _add_line(figure, frame, "temperature_c", "Temperatura", "#9C5700", timezone, unit="°C", yaxis="y2", frequency=frequency)
    figure.update_layout(
        yaxis2={"title": {"text": "Temperatura média (°C)" if frequency != "hourly" else "Temperatura (°C)"}, "overlaying": "y", "side": "right", "showgrid": False, "zeroline": False},
        margin={"r": 65},
    )
    figure.update_xaxes(tickformat="%d/%m<br>%H:%M")
    return figure


def calendar_profile_chart(profile: pd.DataFrame, unit: str = "MWmed") -> go.Figure:
    if profile.empty:
        return _empty_chart("Perfil por calendário", DEFAULT_TIMEZONE)
    figure = _base_chart("Perfil por calendário", x_title="Hora local · America/Sao_Paulo", y_title=f"Carga média ({unit})", height=400)
    names = {
        "dia_util": "Dia útil", "fim_de_semana": "Fim de semana", "feriado": "Feriado",
        "ponto_facultativo": "Ponto facultativo", "nao_informado": "Não informado",
    }
    scopes = {"federal_administracao": "administração pública federal", "nacional": "nacional", "estadual": "estadual", "municipal": "municipal", "nenhum": "sem evento", "nao_informado": "escopo não informado"}
    colors = [NAVY, TEAL, "#7751A8", "#9C5700", RED, "#52657A"]
    for index, ((day_type, scope), rows) in enumerate(profile.groupby(["day_type", "holiday_scope"], sort=True)):
        rows = rows.set_index("hour").reindex(range(24))
        label = names.get(day_type, day_type)
        if day_type == "feriado":
            label += f" {scopes.get(scope, scope)}"
        elif day_type == "ponto_facultativo":
            label = "Facultativo · " + ("N/D" if scope == "nao_informado" else scopes.get(scope, scope))
        valid = rows["mean"].notna().to_numpy()
        marker_sizes = [
            3 if value and not (hour > 0 and valid[hour - 1]) and not (hour < 23 and valid[hour + 1]) else 0
            for hour, value in enumerate(valid)
        ]
        figure.add_trace(go.Scatter(
            x=rows.index, y=rows["mean"], customdata=rows["count"], mode="lines+markers" if any(marker_sizes) else "lines", name=label,
            marker={"size": marker_sizes},
            line={"color": colors[index % len(colors)], "width": 2.3, "dash": ["solid", "dash", "dot"][index % 3]},
            connectgaps=False,
            hovertemplate="Hora: %{x:02d}h<br>Carga média: <b>%{y:,.2f} " + unit + "</b><br>%{customdata} observações<extra>%{fullData.name}</extra>",
        ))
    figure.update_xaxes(dtick=3)
    figure.update_layout(margin={"b": 84})
    return figure


def monthly_chart(monthly: pd.DataFrame, unit: str = "MWmed") -> go.Figure:
    if monthly.empty:
        return _empty_chart("Evolução mensal", DEFAULT_TIMEZONE)
    rows = monthly.copy()
    rows["_month"] = pd.PeriodIndex(rows["month"], freq="M")
    if rows["_month"].duplicated().any():
        raise ValueError("A evolução mensal exige uma única média por mês e ano.")
    months = pd.period_range(rows["_month"].min(), rows["_month"].max(), freq="M")
    rows = rows.set_index("_month").reindex(months)
    rows["count"] = rows["count"].fillna(0)
    figure = _base_chart("Evolução mensal", x_title="Mês / ano · America/Sao_Paulo", y_title=f"Carga média ({unit})")
    figure.add_trace(go.Scatter(
        x=months.to_timestamp(), y=rows["mean"], customdata=rows["count"], mode="lines+markers",
        name="Média mensal observada", line={"color": TEAL, "width": 2.6}, connectgaps=False,
        hovertemplate="%{x|%m/%Y}<br>Carga média: <b>%{y:,.2f} " + unit + "</b><br>%{customdata:,.0f} observações<extra></extra>",
    ))
    figure.update_xaxes(type="date", tickformat="%m/%Y")
    figure.update_layout(showlegend=False, margin={"b": 48})
    return figure


def annual_chart(annual: pd.DataFrame, unit: str = "MWmed") -> go.Figure:
    figure = _base_chart("Média anual no período selecionado", x_title="Ano", y_title=f"Carga média ({unit})")
    figure.add_trace(go.Bar(
        x=annual["year"].astype(str).tolist(), y=annual["mean"], customdata=annual["count"],
        marker_color=TEAL,
        hovertemplate="%{x}<br>Carga média: <b>%{y:,.2f} " + unit + "</b><br>%{customdata:,.0f} horas observadas<extra></extra>",
    ))
    figure.update_xaxes(type="category")
    return figure
