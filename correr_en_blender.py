# =============================================================================
# correr_en_blender.py  -  Corre el pipeline dentro de Blender
#
# Uso: abrir este archivo en el Text Editor de Blender y pulsar "Run Script"
# (o ejecutarlo por el MCP). El .blend vive en la carpeta padre del repo
# (Proyecto Final/), asi que el repo se busca al lado del .blend.
# =============================================================================
import importlib
import os
import sys
import time

import bpy
import numpy as np
from mathutils import Vector

try:
    REPO = os.path.dirname(os.path.abspath(__file__))
    if not os.path.isdir(os.path.join(REPO, "cigarra")):
        raise NameError
except NameError:  # desde el Text Editor __file__ apunta dentro del .blend
    REPO = os.path.join(os.path.dirname(bpy.data.filepath), "cigarra-kit")
if REPO not in sys.path:
    sys.path.insert(0, REPO)

# Recargar: sin esto Blender sigue usando la version vieja de los modulos
# aunque se hayan editado los archivos.
import cigarra.config, cigarra.entrada, cigarra.vista, cigarra.curvas_nivel, cigarra.exportar, cigarra.maqueta  # noqa: E401,E501
for modulo in (cigarra.config, cigarra.entrada, cigarra.vista, cigarra.curvas_nivel, cigarra.exportar,
               cigarra.maqueta):
    importlib.reload(modulo)
from cigarra import config, curvas_nivel, entrada, exportar, maqueta, vista  # noqa: E402

# La maqueta se arma al lado de la Cigarra (en +x), en su propia coleccion, fuera
# de lo que ya hay en la escena (la ShadowBox_Cigarra vieja ocupa x = 1,2 a 2,1).
SEPARACION_MAQUETA = 2.8


def guardar_png(arreglo_rgb, nombre, carpeta):
    """Arreglo (alto, ancho, 3) entre 0 y 1 -> PNG. La fila 0 de Blender es la de abajo,
    igual que y creciente en la rejilla: la imagen sale como se ve desde arriba."""
    alto, ancho, _ = arreglo_rgb.shape
    rgba = np.concatenate([arreglo_rgb, np.ones((alto, ancho, 1))], axis=2).astype(np.float32)
    im = bpy.data.images.get(nombre) or bpy.data.images.new(nombre, ancho, alto)
    if tuple(im.size) != (ancho, alto):
        im.scale(ancho, alto)
    im.pixels.foreach_set(rgba.ravel())
    im.filepath_raw = os.path.join(carpeta, nombre + ".png")
    im.file_format = 'PNG'
    im.save()
    return im.filepath_raw


def guardar_svg(piezas_mm, nombre, carpeta, referencia):
    """Piezas (listas de contornos en mm) -> SVG con la cabeza arriba, con el
    encuadre de `referencia` (el chasis) para que todas las hojas se superpongan."""
    todos = [c for p in piezas_mm for c in p]
    hoja, ancho, alto = exportar.cabeza_arriba(todos, referencia=referencia)
    lienzo = exportar.Lienzo(ancho, alto)
    for c in sorted(hoja, key=lambda c: abs(curvas_nivel.area_con_signo(c))):
        lienzo.polilinea(c)          # huecos (mas pequenos) antes que los bordes exteriores
    return lienzo.guardar(os.path.join(carpeta, nombre + ".svg"))


def piezas_mm(mascara):
    """Una lista de contornos en mm por cada isla (pieza fisica) de la mascara."""
    return [curvas_nivel.contornos_mm(isla, config.PIXEL_MM, config.TOLERANCIA_MM)[0]
            for isla in curvas_nivel.islas(mascara)]


def chasis_y_capas(cuerpo, altura, carpeta):
    """Nivel 0 = chasis (silueta + margen); niveles 1..N_CAPAS = curvas de nivel."""
    px = config.PIXEL_MM
    mm2 = px * px
    radio = curvas_nivel.radio_para_ancho(config.ANCHO_MIN_LASER_MM, px)

    # --- Chasis: dilatar con un pincel redondo de MARGEN_CHASIS_MM de radio.
    chasis = curvas_nivel.dilatar(cuerpo, round(config.MARGEN_CHASIS_MM / px))
    delgado = curvas_nivel.zonas_delgadas(chasis, radio)
    p_chasis = piezas_mm(chasis)
    print(f"Chasis: {len(p_chasis)} pieza(s) | {chasis.sum() * mm2 / 100:.1f} cm2 "
          f"| mas angosto que {config.ANCHO_MIN_LASER_MM} mm: {delgado.sum()} px")
    referencia = p_chasis[0]
    print("  SVG:", os.path.basename(guardar_svg(p_chasis, "chasis", carpeta, referencia)))

    # --- Capas por cuantiles, limpiadas de abajo hacia arriba.
    cortes = curvas_nivel.cortes_por_cuantiles(altura, config.N_CAPAS)
    crudas = curvas_nivel.capas_apiladas(altura, cortes)
    limpias = curvas_nivel.capas_limpias(crudas, cuerpo, radio, config.AREA_MIN_PIEZA_MM2 / mm2)
    niveles = [("chasis", p_chasis)]
    for k, (cruda, limpia) in enumerate(zip(crudas, limpias), start=1):
        piezas = piezas_mm(limpia)
        perdido = (cruda & ~limpia).sum() * mm2
        print(f"Capa {k}: corte z = {cortes[k - 1]:.3f} | {len(piezas)} pieza(s) "
              f"| {limpia.sum() * mm2 / 100:.1f} cm2 | descartado {perdido:.0f} mm2 "
              f"({len(curvas_nivel.islas(cruda))} islas antes de limpiar)")
        print("  SVG:", os.path.basename(guardar_svg(piezas, f"capa_{k}", carpeta, referencia)))
        niveles.append((f"capa_{k}", piezas))
    return chasis, limpias, niveles


def main():
    t = time.time()
    malla = entrada.cargar_cuerpo("Cigarra")
    rejilla = vista.Rejilla.alrededor(malla)
    altura, parte = vista.mapa_de_alturas(malla, rejilla)
    cuerpo = vista.silueta(altura)
    segundos = time.time() - t

    px_mm = config.PIXEL_MM
    filas, columnas = np.nonzero(cuerpo)
    print("=" * 64)
    print(f"Piezas del cuerpo ({len(malla.nombres)}): {', '.join(malla.nombres)}")
    print(f"Malla: {len(malla.vertices)} vertices, {len(malla.triangulos)} triangulos")
    print(f"Rejilla {rejilla.ancho} x {rejilla.alto} = {rejilla.ancho * rejilla.alto} rayos "
          f"| pixel {px_mm} mm | {segundos:.1f} s")
    print(f"Silueta del cuerpo: {(np.ptp(columnas) + 1) * px_mm:.1f} x {(np.ptp(filas) + 1) * px_mm:.1f} mm "
          f"| area {cuerpo.sum() * px_mm ** 2 / 100:.1f} cm2")
    ocultas = [n for k, n in enumerate(malla.nombres) if not (parte == k).any()]
    print("Piezas que no se ven desde arriba:", ", ".join(ocultas) or "ninguna")
    carpeta = os.path.join(REPO, "salida")
    os.makedirs(carpeta, exist_ok=True)
    chasis, capas, niveles = chasis_y_capas(cuerpo, altura, carpeta)
    raiz = bpy.data.objects["Cigarra"]
    ubicacion = raiz.matrix_world.translation + Vector((SEPARACION_MAQUETA, 0, 0))
    maqueta.construir(niveles, rejilla, ubicacion)
    print(f"Maqueta: coleccion {maqueta.COLECCION}, en {tuple(round(v, 2) for v in ubicacion)}")
    print("=" * 64)
    # Silueta: negro sobre blanco. Alturas: mas claro = mas alto.
    print("PNG:", guardar_png(np.repeat(~cuerpo[..., None], 3, axis=2).astype(float),
                              "chasis_silueta", carpeta))
    z = np.nan_to_num((altura - np.nanmin(altura)) / np.nanmax(altura - np.nanmin(altura)), nan=0.0)
    print("PNG:", guardar_png(np.repeat(z[..., None], 3, axis=2), "mapa_alturas", carpeta))
    return malla, rejilla, altura, parte, cuerpo, chasis, capas


if __name__ == "__main__":
    main()
