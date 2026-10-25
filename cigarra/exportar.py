# =============================================================================
# exportar.py  -  Archivos SVG a escala real para el laser
#
# Un Lienzo es una hoja en MILIMETROS: el SVG declara width="..mm" y un
# viewBox con las mismas medidas, asi 1 unidad del dibujo = 1 mm real y el
# programa del laser lo importa al tamano correcto.
#
# Cada trazo va a una capa segun lo que el laser debe hacer con el:
#   "corte"   -> atraviesa el material (COLOR_CORTE)
#   "grabado" -> solo marca la superficie (COLOR_GRABADO)
#
# Escrito a mano, sin librerias: Blender no trae svgwrite y un SVG es solo texto.
# =============================================================================
import os

from . import config

CAPAS = {"corte": config.COLOR_CORTE, "grabado": config.COLOR_GRABADO}


def _num(x):
    # 3 decimales (micras) son de sobra para un laser; se quitan ceros de mas.
    return f"{x:.3f}".rstrip("0").rstrip(".")


def cabeza_arriba(polilineas_mm, margen_mm=5.0, referencia=None):
    """Lleva contornos de la vista cenital (cabeza hacia +x, y hacia arriba) a la
    hoja del SVG, con la cabeza hacia ARRIBA como queda colgada en la pared.

    Es un giro de 90 grados antihorario, (x, y) -> (-y, x), seguido del cambio
    a coordenadas de SVG (y crece hacia abajo). Un giro no refleja: el lado
    izquierdo de la cigarra sigue a la izquierda de quien la mira de frente.

    La hoja se encuadra con `referencia` (por defecto, los mismos contornos).
    Si todas las capas usan el chasis como referencia, todos los SVG comparten
    el mismo encuadre y se pueden superponer.
    Devuelve las polilineas en la hoja y el tamano de hoja (ancho, alto).
    """
    girar = lambda ps: [[(-y, x) for x, y in p] for p in ps]
    marco = [q for p in girar(referencia or polilineas_mm) for q in p]
    xmin, xmax = min(x for x, _ in marco), max(x for x, _ in marco)
    ymin, ymax = min(y for _, y in marco), max(y for _, y in marco)
    hoja = [[(x - xmin + margen_mm, ymax - y + margen_mm) for x, y in p]
            for p in girar(polilineas_mm)]
    return hoja, xmax - xmin + 2 * margen_mm, ymax - ymin + 2 * margen_mm


class Lienzo:
    def __init__(self, ancho_mm, alto_mm):
        self.ancho = ancho_mm
        self.alto = alto_mm
        self.elementos = {capa: [] for capa in CAPAS}

    def polilinea(self, puntos, cerrada=True, capa="corte"):
        """Lista de (x, y) en mm. Cerrada = el laser vuelve al punto inicial."""
        coords = " ".join(f"{_num(x)},{_num(y)}" for x, y in puntos)
        etiqueta = "polygon" if cerrada else "polyline"
        self.elementos[capa].append(f'<{etiqueta} points="{coords}"/>')

    def texto(self, x, y, contenido, alto_mm=3.0, capa="grabado"):
        """Texto centrado en x; y es la linea base. Va relleno, no como trazo."""
        self.elementos[capa].append(
            f'<text x="{_num(x)}" y="{_num(y)}" font-size="{_num(alto_mm)}" '
            f'text-anchor="middle" font-family="Arial, Helvetica, sans-serif" '
            f'fill="{CAPAS[capa]}" stroke="none">{contenido}</text>')

    def a_svg(self):
        lineas = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{_num(self.ancho)}mm" height="{_num(self.alto)}mm" '
            f'viewBox="0 0 {_num(self.ancho)} {_num(self.alto)}">',
        ]
        for capa, color in CAPAS.items():
            if not self.elementos[capa]:
                continue
            lineas.append(f'<g id="{capa}" fill="none" stroke="{color}" '
                          f'stroke-width="{_num(config.TRAZO_MM)}">')
            lineas += ["  " + e for e in self.elementos[capa]]
            lineas.append("</g>")
        lineas.append("</svg>")
        return "\n".join(lineas) + "\n"

    def guardar(self, ruta):
        os.makedirs(os.path.dirname(ruta) or ".", exist_ok=True)
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(self.a_svg())
        return ruta
