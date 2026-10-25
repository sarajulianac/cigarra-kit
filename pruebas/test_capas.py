# Pruebas de las capas por cuantiles con terrenos inventados.
# Correr desde cigarra-kit con el Python de Blender (ver CLAUDE.md).
import unittest

import numpy as np

from cigarra import curvas_nivel as cn
from cigarra.exportar import cabeza_arriba


def piramide(n=81):
    """Altura = distancia al borde de un cuadrado (pico en el centro)."""
    y, x = np.mgrid[0:n, 0:n]
    c = (n - 1) / 2
    return (c - np.maximum(abs(x - c), abs(y - c))).astype(float)


def dos_picos():
    y, x = np.mgrid[0:60, 0:100]
    h = np.maximum(20 - np.hypot(x - 25, y - 30), 20 - np.hypot(x - 75, y - 30))
    return np.where(h > 0, h, np.nan)


class TestCuantiles(unittest.TestCase):
    def test_areas_parejas(self):
        # 3 capas sobre el chasis: cada nivel con ~1/4 del area total.
        # Cono (alturas continuas): en la piramide hay anillos enteros con la
        # MISMA altura entera y el corte no puede partir un empate.
        y, x = np.mgrid[0:101, 0:101]
        h = 50 - np.hypot(x - 50, y - 50)
        h[h < 0] = np.nan
        capas = cn.capas_apiladas(h, cn.cortes_por_cuantiles(h, 3))
        total = np.isfinite(h).sum()
        for k, capa in enumerate(capas, start=1):
            self.assertAlmostEqual(capa.sum() / total, 1 - k / 4, delta=0.03)

    def test_una_dentro_de_otra(self):
        h = piramide()
        capas = cn.capas_apiladas(h, cn.cortes_por_cuantiles(h, 3))
        for abajo, arriba in zip(capas, capas[1:]):
            self.assertFalse((arriba & ~abajo).any())

    def test_dos_picos_se_separan_arriba(self):
        h = dos_picos()
        capas = cn.capas_apiladas(h, cn.cortes_por_cuantiles(h, 3))
        self.assertEqual(len(cn.islas(capas[-1])), 2)


class TestLimpieza(unittest.TestCase):
    def test_quita_isla_pequena_y_astilla(self):
        m = np.zeros((40, 40), bool)
        m[5:30, 5:30] = True        # pieza buena
        m[34:37, 34:37] = True      # isla de 3 x 3 = 9 px
        m[15, 30:38] = True         # astilla de 1 px de ancho
        limpia = cn.limpiar(m, radio_px=1, area_min_px=25)
        self.assertEqual(len(cn.islas(limpia)), 1)
        self.assertFalse(limpia[35, 35])
        self.assertFalse(limpia[15, 35])
        self.assertTrue(limpia[15, 15])

    def test_si_se_va_la_de_abajo_se_va_la_de_arriba(self):
        # Un pico chiquito: su capa 1 (5 x 5 px) no pasa el filtro y se
        # descarta; lo que estaba encima (capa 2) se va con ella.
        h = piramide(41)
        base = np.isfinite(h)
        limpias = cn.capas_limpias([h >= 18, h >= 19], base, radio_px=0, area_min_px=30)
        self.assertFalse(limpias[0].any())
        self.assertFalse(limpias[1].any())

    def test_limpias_siguen_una_dentro_de_otra(self):
        h = dos_picos()
        capas = cn.capas_apiladas(h, cn.cortes_por_cuantiles(h, 3))
        limpias = cn.capas_limpias(capas, np.isfinite(h), radio_px=2, area_min_px=40)
        for abajo, arriba in zip(limpias, limpias[1:]):
            self.assertFalse((arriba & ~abajo).any())
        self.assertTrue(limpias[-1].any())

    def test_radio_para_ancho(self):
        # Pincel de 2 * 2 + 1 = 5 px = 1,25 mm >= 0,8 mm con pixel de 0,25.
        self.assertEqual(cn.radio_para_ancho(0.8, 0.25), 2)
        self.assertEqual(cn.radio_para_ancho(0.25, 0.25), 0)


class TestEncuadre(unittest.TestCase):
    def test_capas_comparten_encuadre_con_el_chasis(self):
        chasis = [[(0, 0), (10, 0), (10, 4), (0, 4)]]
        capa = [[(2, 1), (4, 1), (4, 2), (2, 2)]]
        _, ancho_c, alto_c = cabeza_arriba(chasis, margen_mm=1)
        hoja, ancho, alto = cabeza_arriba(capa, margen_mm=1, referencia=chasis)
        self.assertEqual((ancho, alto), (ancho_c, alto_c))
        # (2, 1) girado -> (-1, 2); en la hoja: x = -1 - (-4) + 1, y = 10 - 2 + 1.
        self.assertEqual(hoja[0][0], (4, 9))


if __name__ == "__main__":
    unittest.main()
