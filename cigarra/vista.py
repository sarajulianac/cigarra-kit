# =============================================================================
# vista.py  -  Vista ortografica desde arriba: mapa de alturas y silueta
#
# Como una camara Orthographic de Blender puesta encima de la cigarra que, en
# vez de colores, guarda A QUE ALTURA estaba lo primero que toco cada rayo.
# Eso es un z-buffer (cap. 9) visto en proyeccion ortografica (cap. 8).
#
# Paso 2 del pipeline (retroalimentacion del 20 oct): la silueta de esa vista,
# en un solo color, es la PRIMERA PIEZA: el chasis.
# =============================================================================
from dataclasses import dataclass

import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

from . import config


@dataclass
class Rejilla:
    """Hoja cuadriculada sobre el plano XY: donde empieza y cuanto mide cada pixel."""
    x0: float     # esquina de la hoja (unidades de Blender)
    y0: float
    celda: float  # lado de un pixel (unidades de Blender)
    ancho: int    # columnas (i)
    alto: int     # filas (j)

    @classmethod
    def alrededor(cls, malla, pixel_mm=config.PIXEL_MM, margen_mm=2.0):
        """La rejilla mas pequena que cubre la malla, mas un margen."""
        celda = config.a_blender(pixel_mm)
        margen = config.a_blender(margen_mm)
        (xmin, ymin), (xmax, ymax) = malla.vertices[:, :2].min(0), malla.vertices[:, :2].max(0)
        x0, y0 = xmin - margen, ymin - margen
        ancho = int(np.ceil((xmax + margen - x0) / celda))
        alto = int(np.ceil((ymax + margen - y0) / celda))
        return cls(x0, y0, celda, ancho, alto)

    def centro(self, i, j):
        """Centro del pixel (i, j) en el plano XY."""
        return self.x0 + (i + 0.5) * self.celda, self.y0 + (j + 0.5) * self.celda


def mapa_de_alturas(malla, rejilla):
    """Lanza un rayo vertical hacia abajo por cada pixel.

    Devuelve dos arreglos 2D de (alto, ancho):
      altura[j, i]  z del primer punto que toca el rayo (NaN si no toca nada)
      parte[j, i]   que pieza toco (indice en malla.nombres; -1 si nada)
    """
    # BVH: arbol de cajas envolventes. Cada rayo descarta ramas enteras del
    # arbol en vez de probar los miles de triangulos uno por uno.
    bvh = BVHTree.FromPolygons(malla.vertices.tolist(), malla.triangulos.tolist())
    z_arriba = float(malla.vertices[:, 2].max()) + 1.0   # por encima de todo
    abajo = Vector((0.0, 0.0, -1.0))

    altura = np.full((rejilla.alto, rejilla.ancho), np.nan, np.float32)
    parte = np.full((rejilla.alto, rejilla.ancho), -1, np.int16)
    for j in range(rejilla.alto):
        for i in range(rejilla.ancho):
            x, y = rejilla.centro(i, j)
            punto, _normal, indice, _dist = bvh.ray_cast(Vector((x, y, z_arriba)), abajo)
            if punto is not None:
                altura[j, i] = punto.z
                parte[j, i] = malla.parte_de_triangulo[indice]
    return altura, parte


def silueta(altura):
    """Mascara del chasis: True donde algun rayo toco la cigarra."""
    return np.isfinite(altura)
