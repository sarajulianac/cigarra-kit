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
import cigarra.config, cigarra.entrada, cigarra.vista, cigarra.curvas_nivel, cigarra.exportar  # noqa: E401
for modulo in (cigarra.config, cigarra.entrada, cigarra.vista, cigarra.curvas_nivel, cigarra.exportar):
    importlib.reload(modulo)
from cigarra import config, curvas_nivel, entrada, exportar, vista  # noqa: E402


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


def chasis_svg(cuerpo, carpeta):
    """Silueta del cuerpo -> chasis con margen -> contorno limpio -> SVG con la cabeza arriba."""
    px = config.PIXEL_MM
    # Margen: dilatar con un pincel redondo de MARGEN_CHASIS_MM de radio.
    chasis = curvas_nivel.dilatar(cuerpo, round(config.MARGEN_CHASIS_MM / px))

    # Fabricabilidad: una sola isla y nada mas angosto que el minimo del laser.
    islas = curvas_nivel.contar_islas(chasis)
    delgado = curvas_nivel.zonas_delgadas(chasis, round(config.ANCHO_MIN_LASER_MM / 2 / px))
    print(f"Chasis: {len(islas)} isla(s) | zonas mas angostas que "
          f"{config.ANCHO_MIN_LASER_MM} mm: {delgado.sum()} px")

    limpios, n_crudos = curvas_nivel.contornos_mm(chasis, px, config.TOLERANCIA_MM)
    huecos = sum(curvas_nivel.area_con_signo(c) < 0 for c in limpios)
    print(f"Contornos: {len(limpios)} ({huecos} huecos) | puntos {n_crudos} -> "
          f"{sum(len(c) for c in limpios)} con tolerancia {config.TOLERANCIA_MM} mm")

    hoja, ancho, alto = exportar.cabeza_arriba(limpios)
    lienzo = exportar.Lienzo(ancho, alto)
    for c in sorted(hoja, key=lambda c: abs(curvas_nivel.area_con_signo(c))):
        lienzo.polilinea(c)          # huecos (mas pequenos) antes que el borde exterior
    print(f"SVG: hoja {ancho:.1f} x {alto:.1f} mm ->",
          lienzo.guardar(os.path.join(carpeta, "chasis.svg")))
    return chasis


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
    chasis = chasis_svg(cuerpo, carpeta)
    print("=" * 64)
    # Silueta: negro sobre blanco. Alturas: mas claro = mas alto.
    print("PNG:", guardar_png(np.repeat(~cuerpo[..., None], 3, axis=2).astype(float),
                              "chasis_silueta", carpeta))
    z = np.nan_to_num((altura - np.nanmin(altura)) / np.nanmax(altura - np.nanmin(altura)), nan=0.0)
    print("PNG:", guardar_png(np.repeat(z[..., None], 3, axis=2), "mapa_alturas", carpeta))
    return malla, rejilla, altura, parte, cuerpo, chasis


if __name__ == "__main__":
    main()
