# Paleta de color -- TB4

El dashboard usa dos paletas de ColorBrewer, ambas validadas como
**colorblind safe**. Se eligio una paleta por tipo de dato, segun el Anexo A.

---

## 1. Paleta divergente (cambios: mejoro / empeoro)

**Tipo:** Divergente
**Fuente:** ColorBrewer -- RdBu
**Validacion:** colorblind safe confirmado (filtro "colorblind safe" activo en colorbrewer2.org)

Codifica los cambios con punto medio cero (Preguntas 1 y 7):

Colores adoptados:
```
#2166ac  azul  -> cambio en la direccion deseable (mejoro): renovables que suben,
                  intensidad de carbono que baja
#b2182b  rojo  -> cambio en la direccion no deseable (empeoro): intensidad de
                  carbono que sube; tambien marca paises con acceso < 50% (P4)
#999999  gris  -> categoria neutra / sin cambio relevante
```

**Simulacion deuteranopia:** el azul y el rojo se mantienen perfectamente
distinguibles (el azul se percibe azul, el rojo se percibe como marron/ocre
oscuro). No se confunden entre si ni con el gris neutro. Es la razon por la que
NO se uso la convencion rojo/verde, inaccesible para deuteranopia.

---

## 2. Paleta cualitativa (regiones y fuentes de energia)

**Tipo:** Cualitativo
**Fuente:** ColorBrewer -- Dark2
**Validacion:** colorblind safe confirmado (Dark2 es la paleta cualitativa
recomendada por ColorBrewer para accesibilidad; verificada en Viz Palette).

Codifica categorias sin jerarquia: las 6 regiones del mundo (P2, P3) y las
fuentes del mix electrico (P6).

Colores adoptados (regiones):
```
#1b9e77  Africa
#d95f02  Asia   (y destacado de Peru en P5/P8/P9)
#7570b3  Europa
#e7298a  America del Norte
#66a61e  America del Sur
#e6ab02  Oceania
```

**Simulacion deuteranopia:** en projects.susielu.com/viz-palette los seis tonos
de Dark2 permanecen separables; el par mas cercano (verde #1b9e77 vs.
verde-oliva #66a61e) sigue siendo distinguible por diferencia de luminosidad.
Para reforzar la lectura, los graficos no dependen solo del color: usan tambien
posicion, etiquetas directas y tooltips.

---

## Procedimiento seguido (Anexo A)

1. **ColorBrewer:** se selecciono RdBu (divergente, 3+ clases) y Dark2
   (cualitativo) con el filtro "colorblind safe" activado.
2. **Viz Palette:** se pegaron los hex y se verifico la simulacion de
   deuteranopia, protanopia y tritanopia; todos los colores resultaron
   distinguibles entre si.
3. Restricciones del enunciado cumplidas: **sin** rojo/verde como unica
   distincion, **sin** tortas/donas, **sin** 3D.
