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

- **Fuente única: `cigarra/config.py`.** Ningún módulo nuevo repite estos números; los scripts de
  `legado/` todavía tienen la escala vieja (15 cm) y no se tocan.
- Envergadura de **30 cm** (escala doble, decidido el 25 oct 2026) = 1,178 unidades de Blender
  → `MM = 1.178 / 300` unidades por mm.
  - Ojo: la envergadura medida de los modelos es ~1,23 unidades; Sara decidió conservar 1,178,
    así que el kit real sale de ~31,4 cm.
- Anchos mínimos: bisturí 2 mm · **láser 0,8 mm** · impreso 0,3 mm.
- Cartón 1,5 mm · cartulina 0,4 mm.
- **Holgura TOTAL** (no por lado): ranura = grosor + holgura. Una por material
  (`HOLGURA_CARTON_MM`, `HOLGURA_CARTULINA_MM`), ambas 0,3 mm provisionales hasta cortar la peineta
  (`python3 -m cigarra.peineta` → `salida/peineta_prueba.svg`). Ojo: `legado/cigarra_hibrida.py` usaba
  grosor + 2·holgura; los módulos nuevos no.
- Corte láser previsto en **Comercial Papelera**. Colores del SVG: rojo = corte, azul = grabado
  (convención común, falta confirmarla con ellos; se cambia en `config.py`).
- Pruebas (sin abrir Blender, pero con su Python, que trae numpy; el `python3` del sistema no lo
  trae), desde `cigarra-kit/`:
  `/Applications/Blender.app/Contents/Resources/5.2/python/bin/python3.13 -m unittest -v`
- Pipeline en Blender: `correr_en_blender.py` (Text Editor → Run Script, o por el MCP).
- Contornos: tolerancia de simplificación 0,1 mm (`TOLERANCIA_MM`). **Solo se simplifican bordes
  trazados** (chasis, capas); ranuras y pestañas nunca, se agregan después y exactas.
- Capas: **chasis = nivel 0** y `N_CAPAS = 3` encima, con cortes por cuantiles (25/50/75 % del área).
  Se limpian de abajo hacia arriba (apertura con el ancho del láser + islas < 25 mm² fuera) y siguen
  una dentro de otra. Cada isla es una pieza física. Relieve comprimido ~10× en altura (bajo relieve).
- Maqueta 3D: colección `Maqueta_Capas` en x = 2,8 (fuera de lo que ya hay en la escena). Se rehace
  en cada corrida; no tocar los modelos de Sara.
- Chasis = silueta del cuerpo + 1,5 mm de margen (`MARGEN_CHASIS_MM`). En los SVG la cigarra va
  **con la cabeza hacia arriba**, como cuelga en la pared (giro de 90°, sin reflejar).
- **Sin pegante.** Uniones permitidas: ranura + pestaña, atrapada entre capas, remache (perla), engaste.
- Venas de corte del ala: deben formar **un solo componente conectado** (si no, se caen al cortar).

## Estructuras de datos (lo que Sara expuso el 20 oct)

- Malla: lista indexada (cómo guarda Blender) / half-edge (BMesh, para preguntar por vecinos).
- BVH (`mathutils.bvhtree`) para lanzar rayos y obtener el mapa de alturas ortográfico.
- Arreglo 2D (mapa de alturas = z-buffer visto desde arriba), cortes por **cuantiles** = curvas de nivel.
- BFS para contar islas y verificar conectividad; apertura morfológica para zonas frágiles.
- Orden del pintor = orden de armado (vista fija de frente, no hace falta BSP).
- El profesor pidió reemplazar el "grafo de escena" por un **árbol de armado** propio.
