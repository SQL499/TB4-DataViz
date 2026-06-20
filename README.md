URL del dashboard en produccion: https://tb4-dataviz-mhsusj3qnnnjayue3cbxrx.streamlit.app/

# TB4 - Dashboard de Transicion Energetica Mundial (2000-2020)

Dashboard interactivo (Streamlit + Plotly) que responde las 10 preguntas del
examen TB4 de Data Visualization, integrando dos fuentes de datos de energia.

## Reproducir en un solo comando

```bash
pip install -r requirements.txt && python merge.py && streamlit run app.py
```

`merge.py` descarga OWID, lo une con el dataset de Kaggle por `country` + `year`
y genera `data/merged.csv` y `data/regions.csv`. Luego `app.py` levanta el
dashboard.

## Datos

| Fuente | Cobertura | Uso |
|--------|-----------|-----|
| **OWID Energy** (descargado por `merge.py`) | ~200 paises, 1965-2024, ~130 variables | intensidad de carbono, energia per capita, mix electrico, regiones |
| **Global Data on Sustainable Energy** (Kaggle, local) | 176 paises, 2000-2020 | acceso a electricidad, % renovables, intensidad energetica, PIB per capita, CO2 |

Se unen por `country` + `year` (los nombres de pais coinciden 100%). Se anade la
columna `region` (continente, via `pycountry-convert`) y la bandera `is_latam`.

**Nota de cobertura:** las variables `renewable_share_of_total_energy` y
`energy_intensity_primary_energy` (fuente World Bank) tienen como ultimo ano
disponible **2019**; para esos indicadores el dashboard usa 2019 como ano final
y lo indica en pantalla. El resto (OWID) cubre 2000-2020 completo.

## Las 10 preguntas y su visualizacion

| # | Pregunta | Grafico | Pestana |
|---|----------|---------|---------|
| 1 | Lideres de la transicion (renovables) | Slope chart | A |
| 2 | Trayectoria regional (intensidad de carbono) | Lineas multiples | A |
| 3 | Riqueza vs. renovables | Scatter (4 encodings) | A |
| 4 | Pobreza energetica y fosiles | Scatter | B |
| 5 | Ranking de consumo per capita | Bump chart | B |
| 6 | Mix electrico por pais | Barras apiladas 100% | B |
| 7 | America Latina: quienes mejoraron | Barras divergentes | B |
| 8 | Peru en la region (3 dimensiones) | Radar | C |
| 9 | Peru vs. vecinos | Lineas multiples | C |
| 10 | Defensa de diseno | Guia verbal (pestana D) | D |

## Controles interactivos

- **Multiselect de region** (barra lateral): filtra simultaneamente P2 y P3.
- **Slider de ano** (barra lateral): actualiza simultaneamente P3 y P4.
- **Selector de pais** (P6): cualquier pais del dataset.
- **Tooltips** en todos los graficos con >=2 metricas adicionales.

## Diseno y mejores practicas aplicadas

- **Titulo = hallazgo, no tipo de grafico**: cada titulo se calcula del dato
  (p. ej. "Denmark lidera: +26.8 pp de renovables").
- **Resaltar uno, atenuar el resto**: lider/Peru/paises criticos en color, el
  resto en gris.
- **Etiquetado directo** al final de las lineas (P2, P9) en vez de leyenda.
- **Barras ordenadas por valor** (P7), numeros con sufijo K/M, sin chartjunk.
- **Anotaciones que guian**: linea de referencia 50% acceso (P4), eje
  "mejoro/empeoro" (P7).
- Paleta ColorBrewer **colorblind safe** (RdBu divergente, Dark2 cualitativa).
  Ver [paleta.md](paleta.md).
- Sin tortas, donas ni 3D (restriccion del enunciado).

## Estructura

```
.
├── README.md          (este archivo; 1a linea = URL del dashboard)
├── requirements.txt   (dependencias con version exacta)
├── app.py             (dashboard Streamlit)
├── paleta.md          (validacion de accesibilidad de color)
├── merge.py           (descarga y une los dos datasets)
└── data/
    ├── merged.csv     (generado por merge.py)
    └── regions.csv    (agregados regionales OWID, P2)
```
