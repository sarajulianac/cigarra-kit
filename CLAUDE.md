# Cigarra para armar — Proyecto final CVI

Proyecto final de Sara Cuadrado para **Computación Visual Interactiva** (Uniandes, prof. Pablo Figueroa).
Pipeline que convierte un modelo 3D de una **cigarra** en un **kit para armar sin pegante**, en formato
**relieve para colgar en la pared**, más su **manual de ensamble**.

## Cómo trabajar conmigo (Sara)

- Todo en **español**, registro conversacional. Comentarios del código también en español.
- **Analogía antes que fórmula**: anclar cada concepto en algo cotidiano o en Blender antes de la notación.
- Sara debe poder **explicar y defender** el código ante el profesor. No basta con que funcione.
- **Modo de trabajo acordado (opción 2, mixta):**
  - Claude construye la estructura y la parte técnica pesada (extraer contornos, exportar SVG a escala,
    utilidades de Blender), y la explica módulo por módulo.
  - **Sara escribe ella misma, con guía línea por línea**, las partes conceptuales:
    el **árbol de armado** (`armado.py`) y la **regla de ramificación de las venas** (`alas.py`).
    En esas partes Claude explica y propone el siguiente paso; **no escribe el código por ella**.
- **Consultar antes de construir algo grande.** Proponer el plan, esperar su visto bueno.
- Commits pequeños con mensajes descriptivos en español: el profesor revisa el avance en GitHub.

## Estado actual

- Modelos y scripts heredados en `legado/` (vienen de Blender, ver abajo). Todavía no están
  organizados como módulos.
- La entrega del **martes 27 de octubre de 2026** es "código avanzado del proyecto".
- Retroalimentación del profesor (20 oct): `docs/retroalimentacion_2026-10-20.md`.
- Plan de construcción: `docs/plan_construccion.md`.

## Blender

- Archivo: `../Primerprototipo.blend` (en la carpeta padre `Proyecto Final/`). No se versiona.
- Blender 5.2 LTS, controlado por el **MCP de Blender** (ejecutar código, mirar la escena).
- Los scripts de `legado/` también existen como bloques de texto dentro del `.blend`.
- Objetos clave en la escena:
  - `Cigarra` (vacío raíz, prefijo `C_`): modelo base paramétrico, de `cigarra_base.py`.
  - `Cigarra_H` (vacío raíz, prefijo `H_`, colección `Cigarra_Hibrida`): modelo híbrido de 30 piezas,
    de `cigarra_hibrida.py`. Cada pieza tiene propiedades `tecnica`, `union`, `apoyo`, `material`, `orden`.
  - `Trazado_Ala_Ant`: marco de calco del ala anterior con la foto de referencia de fondo
    (`Cigarra/Referencias/1792337711629_image.png`). El calco quedó a medias: ahora las alas van procedurales.

## Escala y reglas de fabricación

- Insecto de **15 cm** en su lado mayor = 1,178 unidades de Blender → `MM = 1.178 / 150` unidades por mm.
- Anchos mínimos: bisturí 2 mm · **láser 0,8 mm** · impreso 0,3 mm.
- Cartón 1,5 mm · cartulina 0,4 mm · **holgura** de ranuras 0,3 mm.
- **Sin pegante.** Uniones permitidas: ranura + pestaña, atrapada entre capas, remache (perla), engaste.
- Venas de corte del ala: deben formar **un solo componente conectado** (si no, se caen al cortar).

## Estructuras de datos (lo que Sara expuso el 20 oct)

- Malla: lista indexada (cómo guarda Blender) / half-edge (BMesh, para preguntar por vecinos).
- BVH (`mathutils.bvhtree`) para lanzar rayos y obtener el mapa de alturas ortográfico.
- Arreglo 2D (mapa de alturas = z-buffer visto desde arriba), cortes por **cuantiles** = curvas de nivel.
- BFS para contar islas y verificar conectividad; apertura morfológica para zonas frágiles.
- Orden del pintor = orden de armado (vista fija de frente, no hace falta BSP).
- El profesor pidió reemplazar el "grafo de escena" por un **árbol de armado** propio.
