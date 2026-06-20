"""
merge.py - TB4 Data Visualization
=================================
Descarga el dataset OWID Energy y lo une con el dataset Global Data on
Sustainable Energy (Kaggle) por country + year. Anade una columna de
continente (region) y una bandera de America Latina, y exporta el
resultado a data/merged.csv.

Uso:
    python merge.py

Salida:
    data/merged.csv   (dataset unificado listo para el dashboard)

Reproducibilidad:
    - OWID se descarga de su URL publica oficial. Si no hay internet,
      se usa la copia local owid-energy-data.csv si existe.
    - El dataset de Kaggle requiere autenticacion para descargarse via API,
      por lo que se lee del CSV local global-data-on-sustainable-energy.csv
      (descargado al inicio del examen segun indica el enunciado).
"""

import io
import os
import sys
import urllib.request
import pandas as pd
import pycountry_convert as pcc

# --------------------------------------------------------------------------
# Rutas y constantes
# --------------------------------------------------------------------------
HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")

OWID_URL = "https://owid-public.owid.io/data/energy/owid-energy-data.csv"
OWID_LOCAL = os.path.join(HERE, "owid-energy-data.csv")
KAGGLE_LOCAL = os.path.join(HERE, "global-data-on-sustainable-energy.csv")
OUTPUT = os.path.join(DATA_DIR, "merged.csv")
OUTPUT_REGIONS = os.path.join(DATA_DIR, "regions.csv")

# Agregados regionales OFICIALES de OWID (definicion propia de OWID, sin sufijo).
# Se usan para la Pregunta 2 (trayectoria regional de intensidad de carbono).
OWID_REGIONS = [
    "Africa", "Asia", "Europe", "North America", "South America", "Oceania",
]

# Periodo de analisis pedido por el enunciado (todas las preguntas usan 2000-2020).
YEAR_MIN, YEAR_MAX = 2000, 2020

# Columnas de OWID que el dashboard necesita (subset para mantener el CSV liviano).
OWID_COLS = [
    "country", "year", "iso_code", "population", "gdp",
    # Trayectorias / rankings
    "energy_per_capita",
    "carbon_intensity_elec",
    # Renovables y fosiles (share)
    "renewables_share_energy", "fossil_share_elec", "fossil_share_energy",
    "renewables_electricity",  # para hallar el ano de mayor produccion renovable (P6)
    # Mix electrico por fuente (TWh) - Pregunta 6
    "coal_electricity", "gas_electricity", "oil_electricity",
    "nuclear_electricity", "solar_electricity", "wind_electricity",
    "hydro_electricity", "biofuel_electricity", "other_renewable_electricity",
]

# Mapeo de columnas de Kaggle -> nombres limpios usados en el dashboard.
KAGGLE_RENAME = {
    "Entity": "country",
    "Year": "year",
    "Access to electricity (% of population)": "access_to_electricity",
    "Renewable energy share in the total final energy consumption (%)": "renewable_share_of_total_energy",
    "Energy intensity level of primary energy (MJ/$2017 PPP GDP)": "energy_intensity_primary_energy",
    "gdp_per_capita": "gdp_per_capita",
    "Value_co2_emissions_kt_by_country": "co2_emissions_kt",
    "Electricity from fossil fuels (TWh)": "elec_from_fossil_twh",
    "Electricity from renewables (TWh)": "elec_from_renewables_twh",
    "Electricity from nuclear (TWh)": "elec_from_nuclear_twh",
    "Low-carbon electricity (% electricity)": "low_carbon_elec_pct",
}

# Continentes en espanol.
_CONT_ES = {
    "AF": "Africa", "AS": "Asia", "EU": "Europa",
    "NA": "America del Norte", "SA": "America del Sur",
    "OC": "Oceania", "AN": "Antartida",
}

# Paises que consideramos America Latina (Pregunta 7 y 8).
# Mainland Latinoamerica + principales del Caribe hispano.
LATAM = {
    "Argentina", "Bolivia", "Brazil", "Chile", "Colombia", "Costa Rica",
    "Cuba", "Dominican Republic", "Ecuador", "El Salvador", "Guatemala",
    "Haiti", "Honduras", "Mexico", "Nicaragua", "Panama", "Paraguay",
    "Peru", "Uruguay", "Venezuela",
}


def load_owid() -> pd.DataFrame:
    """Descarga OWID de la URL oficial; usa la copia local como respaldo."""
    try:
        print(f"Descargando OWID desde {OWID_URL} ...")
        # Se necesita User-Agent: el servidor responde 403 a peticiones sin el.
        req = urllib.request.Request(OWID_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read()
        df = pd.read_csv(io.BytesIO(raw), usecols=lambda c: c in OWID_COLS)
        print(f"  OK (descargado): {df.shape[0]} filas")
    except Exception as exc:  # sin internet / URL caida
        print(f"  No se pudo descargar ({exc}).")
        if not os.path.exists(OWID_LOCAL):
            sys.exit("ERROR: no hay internet ni copia local de OWID.")
        print(f"  Usando copia local: {OWID_LOCAL}")
        df = pd.read_csv(OWID_LOCAL, usecols=lambda c: c in OWID_COLS)
    return df


def load_kaggle() -> pd.DataFrame:
    """Lee el dataset de Kaggle desde el CSV local y renombra columnas."""
    if not os.path.exists(KAGGLE_LOCAL):
        sys.exit(f"ERROR: falta {KAGGLE_LOCAL} (descargar desde Kaggle).")
    print(f"Leyendo Kaggle desde {KAGGLE_LOCAL} ...")
    df = pd.read_csv(KAGGLE_LOCAL)
    keep = [c for c in KAGGLE_RENAME if c in df.columns]
    df = df[keep].rename(columns=KAGGLE_RENAME)
    print(f"  OK: {df.shape[0]} filas")
    return df


def continent_of(iso3):
    """Devuelve el continente (en espanol) a partir del codigo ISO alpha-3."""
    if not isinstance(iso3, str) or len(iso3) != 3:
        return None
    try:
        a2 = pcc.country_alpha3_to_country_alpha2(iso3)
        return _CONT_ES[pcc.country_alpha2_to_continent_code(a2)]
    except Exception:
        return None


def main() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)

    owid = load_owid()
    kaggle = load_kaggle()

    # --- Agregados regionales OWID para la Pregunta 2 (antes de filtrar paises) ---
    region_es = {
        "Africa": "Africa", "Asia": "Asia", "Europe": "Europa",
        "North America": "America del Norte", "South America": "America del Sur",
        "Oceania": "Oceania",
    }
    reg = owid[(owid["country"].isin(OWID_REGIONS)) &
               (owid["year"].between(YEAR_MIN, YEAR_MAX))][
        ["country", "year", "carbon_intensity_elec"]].copy()
    reg["region"] = reg["country"].map(region_es)
    reg = reg.dropna(subset=["carbon_intensity_elec"]).sort_values(["region", "year"])
    reg.to_csv(OUTPUT_REGIONS, index=False, encoding="utf-8")
    print(f"Guardado: {OUTPUT_REGIONS}  ({reg.shape[0]} filas, "
          f"{reg['region'].nunique()} regiones)")

    # Filtrar al periodo de analisis.
    owid = owid[owid["year"].between(YEAR_MIN, YEAR_MAX)]
    kaggle = kaggle[kaggle["year"].between(YEAR_MIN, YEAR_MAX)]

    # --- MERGE por country + year (tarea 1 del examen) ---
    # outer para no perder filas; OWID aporta el iso_code que da la region.
    print("Uniendo por country + year (outer)...")
    merged = pd.merge(owid, kaggle, on=["country", "year"], how="outer")

    # Completar iso_code faltante (filas que solo venian de Kaggle).
    iso_map = (owid.dropna(subset=["iso_code"])
                    .drop_duplicates("country")
                    .set_index("country")["iso_code"].to_dict())
    merged["iso_code"] = merged["iso_code"].fillna(merged["country"].map(iso_map))

    # --- Region (continente) y bandera LATAM ---
    merged["region"] = merged["iso_code"].map(continent_of)
    merged["is_latam"] = merged["country"].isin(LATAM)

    # gdp_per_capita de respaldo desde OWID (gdp/population) si Kaggle no lo trae.
    if "gdp" in merged.columns:
        gpc_owid = merged["gdp"] / merged["population"]
        merged["gdp_per_capita"] = merged["gdp_per_capita"].fillna(gpc_owid)

    # Quedarnos solo con paises reales (con iso_code); fuera agregados.
    merged = merged[merged["iso_code"].notna()].copy()

    # Orden y export.
    merged = merged.sort_values(["country", "year"]).reset_index(drop=True)
    merged.to_csv(OUTPUT, index=False, encoding="utf-8")

    print("-" * 60)
    print(f"Guardado: {OUTPUT}")
    print(f"  Filas: {merged.shape[0]} | Columnas: {merged.shape[1]}")
    print(f"  Paises: {merged['country'].nunique()} | "
          f"Anios: {int(merged['year'].min())}-{int(merged['year'].max())}")
    print(f"  Regiones: {sorted(merged['region'].dropna().unique())}")
    print(f"  Paises LATAM: {merged.loc[merged.is_latam, 'country'].nunique()}")


if __name__ == "__main__":
    main()
