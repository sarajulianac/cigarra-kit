# Plan de construcción del código

Objetivo para el martes 27 de octubre: un **corte vertical** del pipeline funcionando de punta a punta
con pocas piezas (el profesor pidió empezar simple, armarlo y ver cómo se ve antes de agregar complejidad).

**Demo del martes:** cargar la cigarra → correr el pipeline → salen el chasis y 3–4 curvas de nivel como
SVG listos para el láser, el árbol de armado impreso como pasos del manual, y un ala generada por
algoritmo junto a la foto de referencia.

## Módulos (paquete `cigarra/`)

| Módulo | Qué hace | Estructura / algoritmo | Quién | Estado |
|---|---|---|---|---|
| `entrada` | Carga la cigarra, quita las alas, la lleva a su marco local | Malla (lista indexada) | Claude | Existe en `legado/shadowbox_pipeline.py` (`malla_local`) |
| `vista` | Vista ortográfica cenital → mapa de alturas | BVH + arreglo 2D | Claude | Existe (`mapa_de_alturas`) |
| `curvas_nivel` | Cortes por cuantiles → contornos vectoriales por capa | Marching squares + simplificación | Claude | Nuevo |
| `piezas` | Clase `Pieza`: nombre, contorno, técnica, altura | Lista indexada | Claude | Nuevo |
| `armado` | Árbol de armado: cada pieza sabe sobre cuál va; el recorrido da los pasos del manual | Árbol | **Sara** | Nuevo |
| `uniones` | Un tipo de unión: ranura en la pieza padre + pestaña en la hija | Booleanas 2D | Claude | Nuevo, simple |
| `exportar` | SVG a escala real (mm) para el láser + JSON del manual | — | Claude | Nuevo |
| `alas` | Venas procedurales: ramificación fractal (venas principales, corte) + Voronoi de pocos centros (celdas, impresas) | Grafo + Voronoi | **Sara** (regla de ramificación) + Claude | Prototipo 2D |
| `textura` | Textura proyectada en perspectiva desde el ojo del observador | Mapeo proyectivo | — | Después del martes |

## Orden de trabajo

1. `entrada` + `vista`: pasar el código existente a módulos limpios.
2. `curvas_nivel` + `exportar`: convertir las capas en archivos de corte reales.
3. `piezas` + `armado`: el árbol que pidió el profesor.
4. `alas`: prototipo procedural.
5. `uniones`: solo si queda tiempo.

## Referencias para las alas

- Runions et al. 2005, *Modeling and visualization of leaf venation patterns* (colonización del espacio):
  https://algorithmicbotany.org/papers/venation.sig2005.html
- Hoffmann et al. 2018, *A simple developmental model recapitulates complex insect wing venation patterns*
  (PNAS; celdas por Voronoi): https://pmc.ncbi.nlm.nih.gov/articles/PMC6176563
