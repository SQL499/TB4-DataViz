"""
TB4 - Dashboard de Transicion Energetica Mundial (2000-2020)
============================================================
Streamlit + Plotly. Responde las 10 preguntas del examen TB4.

Ejecutar localmente:
    pip install -r requirements.txt
    python merge.py          # genera data/merged.csv y data/regions.csv
    streamlit run app.py

Notas de datos:
- Renovables (renewable_share_of_total_energy) e intensidad energetica
  (energy_intensity_primary_energy) provienen de Kaggle/World Bank y su
  ultimo año disponible es 2019. Para esos indicadores el dashboard usa
  2019 como año final y lo indica explicitamente.
- Intensidad de carbono, energia per capita y mix electrico provienen de
  OWID y cubren 2000-2020 completo.
"""

import os
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# --------------------------------------------------------------------------
# Configuracion general
# --------------------------------------------------------------------------
st.set_page_config(
    page_title="TB4 - Transicion Energetica Mundial",
    page_icon=":zap:",
    layout="wide",
    initial_sidebar_state="expanded",
)

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data", "merged.csv")
REGIONS = os.path.join(HERE, "data", "regions.csv")

# --------------------------------------------------------------------------
# PALETA COLORBLIND-SAFE (ColorBrewer). Ver paleta.md
# --------------------------------------------------------------------------
# Cualitativa para regiones -> ColorBrewer "Dark2"
REGION_COLORS = {
    "Africa": "#1b9e77",
    "Asia": "#d95f02",
    "Europa": "#7570b3",
    "America del Norte": "#e7298a",
    "America del Sur": "#66a61e",
    "Oceania": "#e6ab02",
}
# Divergente para cambios (ColorBrewer "RdBu")
COL_GOOD = "#2166ac"   # azul  -> mejoro / direccion deseable
COL_BAD = "#b2182b"    # rojo  -> empeoro / direccion no deseable
COL_NEUTRAL = "#999999"
COL_UP = "#2ca02c"     # verde fuerte -> subio de puesto en el ranking (P5)
# Destacado de Peru
PERU = "#d95f02"
# Fuentes del mix electrico (cualitativa Dark2 + grises)
SOURCE_COLORS = {
    "Carbon": "#666666", "Gas": "#a6761d", "Petroleo": "#1b1b1b",
    "Nuclear": "#7570b3", "Hidro": "#2166ac", "Solar": "#e6ab02",
    "Eolica": "#1b9e77", "Bioenergia": "#66a61e", "Otras renovables": "#e7298a",
}

PLOT_TMPL = "plotly_white"
END_RENEW = 2019   # ultimo año disponible para renovables / intensidad energetica


# --------------------------------------------------------------------------
# Carga de datos
# --------------------------------------------------------------------------
@st.cache_data
def load_data():
    if not os.path.exists(DATA):
        st.error("No se encuentra data/merged.csv. Ejecuta primero: python merge.py")
        st.stop()
    df = pd.read_csv(DATA)
    reg = pd.read_csv(REGIONS) if os.path.exists(REGIONS) else pd.DataFrame()
    return df, reg


df, reg_df = load_data()
REGION_ORDER = ["Africa", "Asia", "Europa", "America del Norte",
                "America del Sur", "Oceania"]

# --------------------------------------------------------------------------
# SIDEBAR - controles globales
# --------------------------------------------------------------------------
st.sidebar.title("Controles")
st.sidebar.caption("Estos controles afectan simultaneamente a varios graficos.")

sel_regions = st.sidebar.multiselect(
    "Region (afecta P2 y P3)",
    options=REGION_ORDER,
    default=REGION_ORDER,
    help="Filtra simultaneamente la trayectoria regional (P2) y el scatter "
         "riqueza vs. renovables (P3).",
)
if not sel_regions:
    sel_regions = REGION_ORDER

global_year = st.sidebar.slider(
    "Año (afecta P3 y P4)",
    min_value=2000, max_value=2019, value=2019, step=1,
    help="Actualiza simultaneamente el scatter de riqueza vs. renovables (P3) "
         "y el de pobreza energetica vs. fosiles (P4).",
)

st.sidebar.markdown("---")
st.sidebar.markdown(
    "**Fuentes**\n\n"
    "- OWID Energy (1965-2024)\n"
    "- Global Data on Sustainable Energy (Kaggle, 2000-2020)\n\n"
    "Unidos por `country` + `year`."
)
st.sidebar.info(
    "Renovables e intensidad energetica: ultimo dato de la fuente = 2019."
)


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def deltas(metric, y0=2000, y1=2020, frame=None):
    """Tabla con valor inicial, final y delta por pais."""
    d = df if frame is None else frame
    piv = d.pivot_table(index="country", columns="year", values=metric)
    piv = piv.dropna(subset=[y0, y1]).copy()
    piv["inicio"], piv["fin"] = piv[y0], piv[y1]
    piv["delta"] = piv[y1] - piv[y0]
    return piv[["inicio", "fin", "delta"]].reset_index()


def section(num, title, question):
    st.subheader(f"Pregunta {num}: {title}")
    st.caption(question)


def fmt_k(v):
    """Formatea numeros grandes con sufijo K/M/B (best practice de etiquetado)."""
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "-"
    a = abs(v)
    if a >= 1e9:
        return f"{v/1e9:.1f}B"
    if a >= 1e6:
        return f"{v/1e6:.1f}M"
    if a >= 1e3:
        return f"{v/1e3:.0f}K"
    return f"{v:.0f}"


def style_fig(fig, height=460, title=None):
    """Estilo uniforme y limpio (sin chartjunk): tipografia legible, sin lineas
    de borde superfluas, grilla horizontal tenue. Best practices de la skill."""
    fig.update_layout(
        template=PLOT_TMPL,
        height=height,
        font=dict(size=13, family="Arial, sans-serif"),
        title=dict(text=title, font=dict(size=18)) if title else None,
        title_x=0.0,
        margin=dict(t=70, b=50),
        hoverlabel=dict(font_size=13),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor="rgba(0,0,0,0.06)", zeroline=False)
    return fig


# ==========================================================================
# PREGUNTA 1 - Lideres de la transicion (slope chart)
# ==========================================================================
def q1():
    section(1, "Lideres de la transicion",
            "Los cinco paises que mas aumentaron su participacion de energias "
            f"renovables entre 2000 y {END_RENEW} (puntos porcentuales ganados).")
    t = deltas("renewable_share_of_total_energy", 2000, END_RENEW)
    top = t.nlargest(5, "delta").sort_values("delta", ascending=False)
    best = top.iloc[0]

    fig = go.Figure()
    for i, (_, r) in enumerate(top.iterrows()):
        leader = (i == 0)  # resaltar uno: el lider en azul fuerte, resto atenuado
        col = COL_GOOD if leader else "#9ecae1"
        fig.add_trace(go.Scatter(
            x=[2000, END_RENEW], y=[r["inicio"], r["fin"]],
            mode="lines+markers+text",
            line=dict(color=col, width=4 if leader else 2.5),
            marker=dict(size=10 if leader else 8, color=col),
            # El lider se rotula con una anotacion destacada (debajo), no aqui.
            text=["", "" if leader else f"  {r['country']} (+{r['delta']:.1f} pp)"],
            textposition="middle right",
            textfont=dict(size=12, color="#9ecae1"),
            hovertemplate=(f"<b>{r['country']}</b><br>"
                           "Año %{x}<br>Renovables: %{y:.1f}%<br>"
                           f"Cambio total: +{r['delta']:.1f} pp<extra></extra>"),
            showlegend=False,
        ))
    # Label del lider en caja blanca con borde azul y elevado para que resalte
    # y no quede tapado por el pais vecino (que termina en un valor similar).
    fig.add_annotation(
        x=END_RENEW, y=best["fin"], xanchor="left", xshift=10, yshift=18,
        text=f"<b>{best['country']} (+{best['delta']:.1f} pp)</b>",
        showarrow=False, font=dict(size=14, color=COL_GOOD),
        bgcolor="rgba(255,255,255,0.95)", bordercolor=COL_GOOD,
        borderwidth=1.5, borderpad=4,
    )
    style_fig(fig, height=460,
              title=f"{best['country']} lidera: +{best['delta']:.1f} pp de "
                    f"renovables (2000-{END_RENEW})")
    fig.update_xaxes(title="Año", tickvals=[2000, END_RENEW], range=[1998, 2026])
    fig.update_yaxes(title="Participacion de renovables (% energia final)")
    fig.update_layout(margin=dict(r=190))
    st.plotly_chart(fig, use_container_width=True)
    st.success(f"Lider: **{best['country']}** con **+{best['delta']:.1f} pp** "
               f"({best['inicio']:.1f}% -> {best['fin']:.1f}%). El top 5 completo: "
               + ", ".join(f"{r['country']} (+{r['delta']:.1f})"
                           for _, r in top.iterrows()) + ".")


# ==========================================================================
# PREGUNTA 2 - Trayectoria regional (lineas multiples)
# ==========================================================================
def q2():
    section(2, "Trayectoria regional",
            "Evolucion de la intensidad de carbono de la electricidad por region "
            "del mundo, 2000-2020 (gCO2/kWh). Menor es mejor.")
    if reg_df.empty:
        st.warning("Falta data/regions.csv (ejecuta merge.py).")
        return
    # Quien redujo mas / empeoro (para el titulo-insight)
    piv = reg_df.pivot_table(index="region", columns="year",
                             values="carbon_intensity_elec").dropna(subset=[2000, 2020])
    piv["delta"] = piv[2020] - piv[2000]
    mejor, peor = piv["delta"].idxmin(), piv["delta"].idxmax()

    # Resaltar uno, atenuar el resto: la region que MAS redujo (azul) y la que
    # MAS empeoro (roja) responden la pregunta; las demas quedan en gris tenue.
    d = reg_df[reg_df["region"].isin(sel_regions)]
    fig = go.Figure()
    for r in REGION_ORDER:
        if r not in sel_regions:
            continue
        sub = d[d["region"] == r].sort_values("year")
        if sub.empty:
            continue
        if r == mejor:
            col, w, op, bold = COL_GOOD, 4, 1.0, True
        elif r == peor:
            col, w, op, bold = COL_BAD, 4, 1.0, True
        else:
            col, w, op, bold = COL_NEUTRAL, 1.8, 0.55, False
        fig.add_trace(go.Scatter(
            x=sub["year"], y=sub["carbon_intensity_elec"],
            mode="lines+markers", name=r, opacity=op,
            line=dict(color=col, width=w), marker=dict(size=5, color=col),
            hovertemplate=(f"<b>{r}</b><br>Año %{{x}}<br>"
                           "Intensidad: %{y:.0f} gCO2/kWh<extra></extra>"),
        ))
        last = sub.iloc[-1]
        fig.add_annotation(
            x=last["year"], y=last["carbon_intensity_elec"], text=r,
            showarrow=False, xanchor="left", xshift=6, opacity=op,
            font=dict(size=12 if bold else 11, color=col,
                      family="Arial Black" if bold else "Arial"))
    style_fig(fig, height=470,
              title=f"{mejor} descarbonizo mas su electricidad; {peor} empeoro "
                    f"(2000-2020)")
    fig.update_xaxes(title="Año")
    fig.update_yaxes(title="Intensidad de carbono (gCO2/kWh)")
    fig.update_layout(showlegend=False, margin=dict(r=150))
    st.plotly_chart(fig, use_container_width=True)
    c1, c2 = st.columns(2)
    c1.success(f"Mayor reduccion: **{mejor}** ({piv.loc[mejor, 'delta']:+.0f} gCO2/kWh)")
    c2.error(f"Empeoro mas: **{peor}** ({piv.loc[peor, 'delta']:+.0f} gCO2/kWh)")


# ==========================================================================
# PREGUNTA 3 - Riqueza vs. renovables (scatter)
# ==========================================================================
def q3():
    section(3, "Riqueza vs. renovables",
            f"Relacion entre PIB per capita y participacion de renovables en "
            f"el año {global_year}. Cada punto es un pais (tamaño = poblacion).")
    d = df[(df["year"] == global_year) & (df["region"].isin(sel_regions))].copy()
    d = d.dropna(subset=["gdp_per_capita", "renewable_share_of_total_energy",
                         "population"])
    fig = px.scatter(
        d, x="gdp_per_capita", y="renewable_share_of_total_energy",
        color="region", size="population", size_max=45,
        color_discrete_map=REGION_COLORS, log_x=True,
        category_orders={"region": REGION_ORDER},
        hover_name="country",
        hover_data={"gdp_per_capita": ":,.0f", "renewable_share_of_total_energy": ":.1f",
                    "co2_emissions_kt": ":,.0f", "population": ":,.0f", "region": False},
        labels={"gdp_per_capita": "PIB per capita (US$, escala log)",
                "renewable_share_of_total_energy": "Renovables (% energia final)",
                "co2_emissions_kt": "CO2 (kt)", "population": "Poblacion"},
    )
    style_fig(fig, height=520,
              title=f"Ser mas rico no implica ser mas renovable ({global_year})")
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Lectura: no hay una relacion lineal clara. Hay paises ricos muy "
               "poco renovables (Golfo Persico) y paises de ingreso medio muy "
               "renovables (Noruega, Uruguay, varios africanos por biomasa).")


# ==========================================================================
# PREGUNTA 4 - Pobreza energetica y fosiles (scatter)
# ==========================================================================
def q4():
    section(4, "Pobreza energetica y fosiles",
            f"En {global_year}: paises con menos del 50% de acceso a electricidad "
            "y su dependencia de combustibles fosiles en la generacion.")
    d = df[df["year"] == global_year].copy()
    d = d.dropna(subset=["access_to_electricity", "fossil_share_elec"])
    d["Critico"] = np.where(d["access_to_electricity"] < 50,
                            "Acceso < 50%", "Acceso >= 50%")
    fig = px.scatter(
        d, x="access_to_electricity", y="fossil_share_elec",
        color="Critico", size="population", size_max=45,
        color_discrete_map={"Acceso < 50%": COL_BAD, "Acceso >= 50%": COL_NEUTRAL},
        hover_name="country",
        hover_data={"access_to_electricity": ":.1f", "fossil_share_elec": ":.1f",
                    "energy_per_capita": ":,.0f", "population": ":,.0f", "Critico": False},
        labels={"access_to_electricity": "Acceso a electricidad (% poblacion)",
                "fossil_share_elec": "Generacion fosil (% electricidad)",
                "energy_per_capita": "Energia per capita (kWh)", "population": "Poblacion"},
    )
    fig.add_vline(x=50, line_dash="dash", line_color=COL_BAD,
                  annotation_text="Umbral 50% acceso", annotation_position="top")
    n_crit = int((d["access_to_electricity"] < 50).sum())
    style_fig(fig, height=520,
              title=f"{n_crit} paises con acceso < 50% a electricidad en {global_year}")
    st.plotly_chart(fig, use_container_width=True)
    crit = d[d["access_to_electricity"] < 50].sort_values("access_to_electricity")
    st.caption(f"Paises a la izquierda de la linea (acceso < 50%): "
               f"{', '.join(crit['country'].head(12))}" if len(crit)
               else "Ningun pais con acceso < 50% en este año.")


# ==========================================================================
# PREGUNTA 5 - Ranking de consumo (bump chart)
# ==========================================================================
def q5():
    section(5, "Ranking de consumo",
            "Movimiento en el ranking de los 12 mayores consumidores de energia "
            "per capita entre 2000 y 2020 (kWh/persona).")
    d = df.dropna(subset=["energy_per_capita"]).copy()
    top_ends = set(d[d.year == 2000].nlargest(12, "energy_per_capita").country) | \
               set(d[d.year == 2020].nlargest(12, "energy_per_capita").country)
    d = d[d.country.isin(top_ends) & d.year.isin(range(2000, 2021))]
    d["rank"] = d.groupby("year")["energy_per_capita"].rank(ascending=False, method="first")
    d = d[d["rank"] <= 12]

    # Resaltar uno, atenuar el resto: en vez de 12 colores, codificamos la
    # DIRECCION del movimiento (azul = subio puestos, rojo = bajo, gris = estable),
    # que es justo lo que pregunta el enunciado.
    fig = go.Figure()
    risers, fallers = [], []
    for c, g in d.groupby("country"):
        g = g.sort_values("year")
        mov = g.iloc[0]["rank"] - g.iloc[-1]["rank"]  # >0 = subio puestos
        if mov >= 1:
            col, w, op = COL_UP, 3, 1.0; risers.append((c, mov))
        elif mov <= -1:
            col, w, op = COL_BAD, 3, 1.0; fallers.append((c, -mov))
        else:
            col, w, op = COL_NEUTRAL, 1.6, 0.5
        mover = col != COL_NEUTRAL
        fig.add_trace(go.Scatter(
            x=g.year, y=g["rank"], mode="lines+markers", name=c, opacity=op,
            line=dict(color=col, width=w), marker=dict(size=5, color=col),
            customdata=g["energy_per_capita"],
            hovertemplate=(f"<b>{c}</b><br>Año %{{x}}<br>Puesto %{{y:.0f}}<br>"
                           "Energia: %{customdata:,.0f} kWh/persona<extra></extra>"),
        ))
        last = g.iloc[-1]
        fig.add_annotation(
            x=last["year"], y=last["rank"], text=c, showarrow=False,
            xanchor="left", xshift=6, opacity=1.0 if mover else 0.6,
            font=dict(size=11, color=col,
                      family="Arial Black" if mover else "Arial"))

    top_riser = max(risers, key=lambda x: x[1])[0] if risers else None
    top_faller = max(fallers, key=lambda x: x[1])[0] if fallers else None
    if top_riser and top_faller:
        title = (f"{top_riser} es quien mas subio y {top_faller} quien mas bajo "
                 f"en el ranking (2000-2020)")
    else:
        title = "Movimiento en el ranking de consumo per capita (2000-2020)"
    fig.update_layout(
        showlegend=False,
        xaxis=dict(title="Año", showgrid=False, range=[2000, 2022]),
        yaxis=dict(title="Puesto en el ranking", autorange="reversed",
                   tickmode="array", tickvals=list(range(1, 13)),
                   showgrid=True, gridcolor="rgba(0,0,0,0.06)"),
        margin=dict(r=160),
    )
    style_fig(fig, height=560, title=title)
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Verde = el pais subio puestos (consume relativamente mas); "
               "rojo = bajo puestos; gris = se mantuvo. El eje esta invertido: "
               "puesto 1 (arriba) = mayor consumo per capita.")


# ==========================================================================
# PREGUNTA 6 - Mix electrico por pais (barras 100%)
# ==========================================================================
SRC_COLS = {
    "coal_electricity": "Carbon", "gas_electricity": "Gas",
    "oil_electricity": "Petroleo", "nuclear_electricity": "Nuclear",
    "hydro_electricity": "Hidro", "solar_electricity": "Solar",
    "wind_electricity": "Eolica", "biofuel_electricity": "Bioenergia",
    "other_renewable_electricity": "Otras renovables",
}


def q6():
    section(6, "Mix electrico por pais",
            "Mix de generacion electrica por fuente, en el año de mayor "
            "produccion renovable del pais seleccionado.")
    countries = sorted(df.loc[df["renewables_electricity"].notna(), "country"].unique())
    default_ix = countries.index("Peru") if "Peru" in countries else 0
    country = st.selectbox("Pais", countries, index=default_ix, key="q6c")

    g = df[(df.country == country) & df["renewables_electricity"].notna()]
    if g.empty:
        st.warning("Sin datos de mix para este pais.")
        return
    year_max = int(g.loc[g["renewables_electricity"].idxmax(), "year"])
    row = df[(df.country == country) & (df.year == year_max)].iloc[0]

    data = [(lbl, row[col]) for col, lbl in SRC_COLS.items()
            if pd.notna(row[col]) and row[col] > 0]
    if not data:
        st.warning("Sin desglose de fuentes para este pais/año.")
        return
    mix = pd.DataFrame(data, columns=["Fuente", "TWh"])
    total = mix["TWh"].sum()
    mix["pct"] = mix["TWh"] / total * 100

    fig = go.Figure()
    for _, r in mix.sort_values("TWh", ascending=False).iterrows():
        fig.add_trace(go.Bar(
            x=[r["pct"]], y=[f"{country} ({year_max})"], orientation="h",
            name=r["Fuente"], marker_color=SOURCE_COLORS.get(r["Fuente"], "#888"),
            customdata=[[r["Fuente"], r["TWh"]]],
            hovertemplate=("%{customdata[0]}<br>%{x:.1f}% del mix<br>"
                           "%{customdata[1]:.2f} TWh<extra></extra>"),
        ))
    ren = mix[mix.Fuente.isin(["Hidro", "Solar", "Eolica", "Bioenergia",
                               "Otras renovables"])]["pct"].sum()
    dominant = mix.sort_values("TWh", ascending=False).iloc[0]
    fig.update_layout(
        barmode="stack",
        xaxis=dict(title="Participacion en la generacion (%)", range=[0, 100],
                   showgrid=False),
        yaxis=dict(title="", showgrid=False),
        legend=dict(orientation="h", bgcolor="rgba(0,0,0,0)"),
    )
    style_fig(fig, height=300,
              title=f"{country} ({year_max}): {dominant['Fuente'].lower()} domina "
                    f"con {dominant['pct']:.0f}% del mix")
    st.plotly_chart(fig, use_container_width=True)
    st.success(f"En {year_max} (año de mayor produccion renovable), **{ren:.0f}%** "
               f"de la electricidad de {country} fue renovable. "
               f"Generacion total: {total:,.1f} TWh.")


# ==========================================================================
# PREGUNTA 7 - America Latina: quienes mejoraron (barras divergentes)
# ==========================================================================
def q7():
    section(7, "America Latina: quienes mejoraron",
            "Cambio en la intensidad de carbono de la electricidad en America "
            "Latina, 2000-2020. Azul = mejoro (bajo); rojo = empeoro (subio).")
    la = df[df["is_latam"]]
    t = deltas("carbon_intensity_elec", 2000, 2020, frame=la).sort_values("delta")
    t["color"] = np.where(t["delta"] < 0, COL_GOOD, COL_BAD)
    mejor = t.iloc[0]   # menor delta = mas mejoro
    peor = t.iloc[-1]   # mayor delta = mas empeoro
    n_mejor = int((t["delta"] < 0).sum())
    fig = go.Figure(go.Bar(
        x=t["delta"], y=t["country"], orientation="h",
        marker_color=t["color"],
        text=[f"{v:+.0f}" for v in t["delta"]], textposition="outside",
        textfont=dict(size=11),
        customdata=np.stack([t["inicio"], t["fin"]], axis=-1),
        hovertemplate=("<b>%{y}</b><br>2000: %{customdata[0]:.0f} gCO2/kWh<br>"
                       "2020: %{customdata[1]:.0f} gCO2/kWh<br>"
                       "Cambio: %{x:+.0f} gCO2/kWh<extra></extra>"),
    ))
    fig.add_vline(x=0, line_color="#444")
    style_fig(fig, height=620,
              title=f"{n_mejor} de {len(t)} paises de America Latina "
                    f"descarbonizaron su electricidad (2000-2020)")
    fig.update_xaxes(title="Cambio en intensidad de carbono (gCO2/kWh)  "
                           "<-- mejoro | empeoro -->", showgrid=False)
    fig.update_yaxes(title="")
    st.plotly_chart(fig, use_container_width=True)
    c1, c2 = st.columns(2)
    c1.success(f"Mejor: **{mejor['country']}** ({mejor['delta']:+.0f} gCO2/kWh)")
    c2.error(f"Peor: **{peor['country']}** ({peor['delta']:+.0f} gCO2/kWh)")
    st.caption("Barras azules hacia la izquierda = mas descarbonizaron; rojas "
               "hacia la derecha = ensuciaron mas su electricidad.")


# ==========================================================================
# PREGUNTA 8 - Peru en la region (radar multidimensional)
# ==========================================================================
def q8():
    section(8, "Peru en la region",
            f"Posicion de Peru frente al promedio de America Latina en tres "
            f"dimensiones ({END_RENEW}). Mas hacia afuera = mejor.")
    la = df[(df["is_latam"]) & (df["year"] == END_RENEW)].copy()
    dims = {
        "renewable_share_of_total_energy": ("Renovables (%)", False),
        "access_to_electricity": ("Acceso electricidad (%)", False),
        "energy_intensity_primary_energy": ("Intensidad energetica", True),  # menor mejor
    }
    axes, peru_norm, la_norm, peru_raw, la_raw = [], [], [], [], []
    for col, (label, lower_better) in dims.items():
        s = la[col].dropna()
        lo, hi = s.min(), s.max()
        pe = la.loc[la.country == "Peru", col].values[0]
        avg = s.mean()

        def norm(v):
            if hi == lo:
                return 0.5
            z = (v - lo) / (hi - lo)
            return 1 - z if lower_better else z
        axes.append(label)
        peru_norm.append(norm(pe) * 100)
        la_norm.append(norm(avg) * 100)
        peru_raw.append(pe)
        la_raw.append(avg)

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=la_norm + [la_norm[0]], theta=axes + [axes[0]],
        name="Promedio America Latina", line_color=COL_NEUTRAL,
        fill="toself", fillcolor="rgba(153,153,153,0.25)",
        customdata=[[v] for v in la_raw + [la_raw[0]]],
        hovertemplate="%{theta}<br>Valor real: %{customdata[0]:.1f}<extra>LA prom.</extra>",
    ))
    fig.add_trace(go.Scatterpolar(
        r=peru_norm + [peru_norm[0]], theta=axes + [axes[0]],
        name="Peru", line_color=PERU, line_width=3,
        fill="toself", fillcolor="rgba(217,95,2,0.25)",
        customdata=[[v] for v in peru_raw + [peru_raw[0]]],
        hovertemplate="%{theta}<br>Valor real: %{customdata[0]:.1f}<extra>Peru</extra>",
    ))
    fuerte = "intensidad energetica" if peru_raw[2] < la_raw[2] else "acceso"
    debil = "renovables" if peru_raw[0] < la_raw[0] else "acceso"
    fig.update_layout(
        template=PLOT_TMPL, height=540,
        font=dict(size=13, family="Arial, sans-serif"),
        title=dict(text=f"Peru aventaja a LA en {fuerte}, pero va por detras en "
                        f"{debil} ({END_RENEW})", font=dict(size=18)),
        title_x=0.0, margin=dict(t=70, l=90, r=90, b=70),
        # Disco transparente: hereda el fondo del tema (claro u oscuro) para que
        # los textos de los ejes siempre contrasten y se lean.
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(range=[0, 100], angle=90, tickangle=90,
                            gridcolor="rgba(128,128,128,0.35)",
                            tickfont=dict(size=11)),
            angularaxis=dict(gridcolor="rgba(128,128,128,0.35)",
                             tickfont=dict(size=13)),
        ),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )
    st.plotly_chart(fig, use_container_width=True)
    c1, c2, c3 = st.columns(3)
    c1.metric("Renovables", f"{peru_raw[0]:.1f}%", f"{peru_raw[0]-la_raw[0]:+.1f} vs LA")
    c2.metric("Acceso electricidad", f"{peru_raw[1]:.1f}%", f"{peru_raw[1]-la_raw[1]:+.1f} vs LA")
    c3.metric("Intensidad energetica", f"{peru_raw[2]:.2f}",
              f"{peru_raw[2]-la_raw[2]:+.2f} vs LA", delta_color="inverse")
    st.caption("Escala normalizada 0-100 respecto al rango de America Latina "
               "(0 = peor de la region, 100 = mejor). La intensidad energetica "
               "se invierte porque menor es mejor. El tooltip muestra el valor real.")


# ==========================================================================
# PREGUNTA 9 - Peru vs. vecinos (lineas multiples)
# ==========================================================================
def q9():
    section(9, "Peru vs. vecinos",
            "Trayectoria de energia per capita de Peru, Chile, Colombia y Brasil "
            "entre 2000 y 2020 (kWh/persona).")
    grp = ["Peru", "Chile", "Colombia", "Brazil"]
    d = df[df.country.isin(grp) & df.year.between(2000, 2020)]

    # Resaltar uno, atenuar el resto: Peru (foco de la pregunta) en naranja
    # fuerte; los vecinos en gris como "el grupo", identificables por su etiqueta.
    fig = go.Figure()
    for c in ["Chile", "Colombia", "Brazil", "Peru"]:  # Peru ultimo = encima
        sub = d[d.country == c].sort_values("year")
        if sub.empty:
            continue
        peru = (c == "Peru")
        col = PERU if peru else COL_NEUTRAL
        fig.add_trace(go.Scatter(
            x=sub["year"], y=sub["energy_per_capita"], mode="lines+markers",
            name=c, opacity=1.0 if peru else 0.55,
            line=dict(color=col, width=4 if peru else 2),
            marker=dict(size=6 if peru else 4, color=col),
            hovertemplate=(f"<b>{c}</b><br>Año %{{x}}<br>"
                           "Energia: %{y:,.0f} kWh/persona<extra></extra>"),
        ))
        last = sub.iloc[-1]
        fig.add_annotation(
            x=last["year"], y=last["energy_per_capita"],
            text=f"{c} ({fmt_k(last['energy_per_capita'])})",
            showarrow=False, xanchor="left", xshift=6,
            opacity=1.0 if peru else 0.7,
            font=dict(size=12, color=col,
                      family="Arial Black" if peru else "Arial"))
    style_fig(fig, height=480,
              title="Peru: el menor consumo per capita entre sus vecinos (2000-2020)")
    fig.update_xaxes(title="Año")
    fig.update_yaxes(title="Energia per capita (kWh/persona)")
    fig.update_layout(showlegend=False, margin=dict(r=150))
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Chile es el mayor consumidor del grupo y Peru el menor. La brecha "
               "Peru-Colombia se mantiene casi constante; ambos crecen en paralelo.")


# ==========================================================================
# PREGUNTA 10 - Guia de defensa de diseno
# ==========================================================================
DEFENSE = [
    ("P1 - Slope chart",
     "Conecta dos puntos en el tiempo con una linea; la pendiente codifica la "
     "magnitud y direccion del cambio (posicion vertical + pendiente). Ideal para "
     "comparar el cambio de pocos paises entre dos años.",
     "Solo muestra inicio y fin: oculta la trayectoria intermedia (un pais pudo "
     "subir y bajar). Se satura con muchas series."),
    ("P2 - Lineas multiples (resaltado por hallazgo)",
     "Tiempo en X, valor en Y. En vez de un color por region (que satura), solo "
     "coloreamos la region que MAS redujo (azul) y la que MAS empeoro (rojo); el "
     "resto queda en gris. El color codifica la respuesta a la pregunta, no la "
     "identidad. Cada linea se rotula directamente.",
     "Atenuar regiones a gris sacrifica la comparacion fina entre las no "
     "destacadas; si la pregunta cambiara a 'comparar todas por igual', habria "
     "que reactivar el color cualitativo."),
    ("P3 / P4 - Scatter",
     "Cruza dos variables continuas (posicion X e Y), con color (categoria) y "
     "tamaño (poblacion) como tercer y cuarto encoding. Revela correlaciones y "
     "outliers.",
     "El tamaño (area) se sobre/subestima perceptualmente; puede haber "
     "solapamiento (overplotting) de puntos. La escala log en X comprime los "
     "extremos."),
    ("P5 - Bump chart (color por direccion)",
     "Codifica la POSICION en un ranking (no el valor absoluto) en el tiempo. "
     "Para no usar 12 colores distintos, el color codifica la DIRECCION del "
     "movimiento: azul = subio puestos, rojo = bajo, gris = estable. Asi el "
     "grafico responde directamente '¿quien subio y quien bajo?'.",
     "Oculta la magnitud absoluta: dos puestos contiguos pueden estar muy lejos "
     "en kWh; por eso el tooltip muestra el valor real. Paises del mismo color no "
     "se distinguen por tono, solo por su etiqueta y posicion."),
    ("P6 - Barras apiladas al 100%",
     "Cada segmento es la participacion de una fuente sobre el total (parte-todo). "
     "Suma 100% y permite comparar composicion.",
     "Solo el primer y ultimo segmento tienen una base comun; los del medio son "
     "dificiles de comparar entre paises. No usamos torta justamente por esto."),
    ("P7 - Barras divergentes",
     "Barras desde un cero comun; la direccion (izq/der) y el color divergente "
     "(azul/rojo) codifican mejora vs. empeoramiento; el largo, la magnitud.",
     "El color rojo/verde seria inaccesible; por eso usamos azul/rojo (RdBu, "
     "colorblind safe). El orden de paises influye en la lectura."),
    ("P8 - Radar",
     "Pone 3 dimensiones de unidades distintas en ejes radiales normalizados, "
     "destacando a Peru sobre el promedio regional en una sola figura.",
     "El area encerrada no tiene significado y depende del orden de los ejes. "
     "La normalizacion puede exagerar diferencias pequenas; mostramos el valor "
     "real en el tooltip."),
    ("P9 - Lineas multiples (Peru destacado)",
     "Series temporales a nivel pais. Peru va en naranja fuerte y grueso (foco de "
     "la pregunta) y los tres vecinos en gris, leidos como 'el grupo'; cada uno "
     "se identifica por su etiqueta directa. Asi se ve de un vistazo cuando Peru "
     "se acerca o se aleja del grupo.",
     "Atenuar a los vecinos dificulta compararlos ENTRE si; la decision asume que "
     "la pregunta es 'Peru vs. el grupo', no 'Chile vs. Brasil'."),
]


def q10():
    st.subheader("Pregunta 10: Defensa de diseno (guia del equipo)")
    st.caption("Esta pregunta se responde verbalmente. Aqui esta el porque de "
               "cada grafico, su encoding y su limitacion.")
    for titulo, porque, limite in DEFENSE:
        with st.expander(titulo):
            st.markdown(f"**Por que este grafico / encoding:** {porque}")
            st.markdown(f"**Limitacion:** {limite}")
    st.markdown("---")
    st.markdown(
        "**Mejores practicas de visualizacion aplicadas**\n"
        "- **El titulo es el hallazgo, no el tipo de grafico**: cada titulo se "
        "calcula del dato (p. ej. 'Dinamarca lidera: +26.8 pp') en vez de "
        "'Grafico de renovables'.\n"
        "- **Resaltar uno, atenuar el resto**: el lider (P1), Peru (P5, P8, P9) y "
        "los paises criticos <50% acceso (P4) llevan color; el resto queda gris.\n"
        "- **Etiquetado directo en lugar de leyenda**: las lineas (P2, P9) se "
        "rotulan al final, evitando que el ojo salte a una leyenda.\n"
        "- **Ordenar por valor**: las barras (P7) van ordenadas por magnitud, no "
        "alfabeticamente.\n"
        "- **Formato legible**: numeros grandes con sufijo K/M, fuentes >=13px, "
        "sin chartjunk (grilla minima, sin bordes superfluos).\n"
        "- **Anotaciones que guian la lectura**: linea de referencia del 50% de "
        "acceso (P4), eje con direccion 'mejoro/empeoro' (P7).\n\n"
        "**Decisiones transversales**\n"
        "- Sin tortas, donas ni 3D (restriccion del enunciado y mala precision "
        "perceptual de los angulos/areas).\n"
        "- Paleta ColorBrewer colorblind-safe: cualitativa *Dark2* para regiones, "
        "divergente *RdBu* (azul/rojo, no rojo/verde) para cambios. Ver `paleta.md`.\n"
        "- Renovables e intensidad energetica: la fuente (World Bank) llega a 2019; "
        "ese es el año final que usamos para esos indicadores.\n"
        "- Datos unidos por `country` + `year` (OWID + Kaggle)."
    )


# --------------------------------------------------------------------------
# LAYOUT PRINCIPAL
# --------------------------------------------------------------------------
st.title("Transicion Energetica Mundial 2000-2020")
st.markdown("Dashboard TB4 - Data Visualization. Responde las 10 preguntas del "
            "examen navegando las pestanas. Usa los controles de la barra lateral.")

tabA, tabB, tabC, tabD = st.tabs([
    "Bloque A - Panorama global",
    "Bloque B - Patrones y comparaciones",
    "Bloque C - Posicion de Peru",
    "Bloque D - Defensa (P10)",
])

with tabA:
    q1(); st.divider(); q2(); st.divider(); q3()
with tabB:
    q4(); st.divider(); q5(); st.divider(); q6(); st.divider(); q7()
with tabC:
    q8(); st.divider(); q9()
with tabD:
    q10()
