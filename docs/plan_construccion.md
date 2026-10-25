# Plan de construcción del código

Objetivo para el martes 27 de octubre: un **corte vertical** del pipeline funcionando de punta a punta
con pocas piezas (el profesor pidió empezar simple, armarlo y ver cómo se ve antes de agregar complejidad).

**Demo del martes:** cargar la cigarra → correr el pipeline → salen el chasis y 3–4 curvas de nivel como
SVG listos para el láser, el árbol de armado impreso como pasos del manual, y un ala generada por
algoritmo junto a la foto de referencia.

## Módulos (paquete `cigarra/`)

| Módulo | Qué hace | Estructura / algoritmo | Quién | Estado |
|---|---|---|---|---|
| `config` | Escala (30 cm de envergadura) y reglas de fabricación en un solo lugar | Constantes | Claude | Hecho |
| `entrada` | Carga la cigarra, quita las alas, la lleva a su marco local | Malla (lista indexada) | Claude | Hecho (sin BMesh; quita Ala y Vena) |
| `vista` | Vista ortográfica cenital → mapa de alturas | BVH + arreglo 2D | Claude | Hecho: mapa de alturas + silueta del chasis (píxel 0,25 mm) |
| `curvas_nivel` | Cortes por cuantiles → contornos vectoriales por capa | Marching squares + Douglas–Peucker | Claude | Hecho para el chasis (`salida/chasis.svg`); faltan las capas por cuantiles |
| `piezas` | Clase `Pieza`: nombre, contorno, técnica, altura | Lista indexada | Claude | Nuevo |
| `armado` | Árbol de armado: cada pieza sabe sobre cuál va; el recorrido da los pasos del manual | Árbol | **Sara** | Nuevo |
| `uniones` | Un tipo de unión: ranura en la pieza padre + pestaña en la hija | Booleanas 2D | Claude | Nuevo, simple |
| `exportar` | SVG a escala real (mm) para el láser + JSON del manual | — | Claude | SVG hecho (capas corte/grabado); falta JSON |
| `alas` | Venas procedurales: ramificación fractal (venas principales, corte) + Voronoi de pocos centros (celdas, impresas) | Grafo + Voronoi | **Sara** (regla de ramificación) + Claude | Prototipo 2D |
| `textura` | Textura proyectada en perspectiva desde el ojo del observador | Mapeo proyectivo | — | Después del martes |

## Orden de trabajo

0. **Peineta de prueba** (primer SVG del pipeline, **hecho**: `cigarra/peineta.py`,
   `salida/peineta_prueba.svg`). Dos piezas cortadas en cartón, con desfases de −0,2 a +0,3 mm en
   pasos de 0,1 sobre el grosor, cada ranura rotulada con su medida:
   - peine con ranuras **abiertas** para cartón (1,3 · 1,4 · 1,5 · 1,6 · 1,7 · 1,8 mm);
   - tira con ranuras **cerradas** para cartulina (0,2 … 0,7 mm), como las del chasis donde entran
     las pestañas de las bandas del abdomen y del pronoto.

   Se corta en el láser real (Comercial Papelera) y se prueba qué ranura sostiene la pestaña firme sin
   forzarla; ese ancho menos el grosor pasa a `HOLGURA_CARTON_MM` / `HOLGURA_CARTULINA_MM`.
   La holgura es **total**, no por lado. Así se calibra antes de cortar piezas de verdad (el láser
   quema ~0,1–0,2 mm de material y eso varía con cada máquina y cada cartón).
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
