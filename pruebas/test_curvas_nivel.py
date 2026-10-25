# Pruebas de curvas_nivel con mascaras inventadas, cuyo resultado se sabe de
# antemano. Correr desde cigarra-kit:  python3 -m unittest -v
import unittest

import numpy as np

from cigarra import config, curvas_nivel as cn
from cigarra.exportar import cabeza_arriba


def _bloque(alto, ancho, j0, j1, i0, i1):
    m = np.zeros((alto, ancho), bool)
    m[j0:j1, i0:i1] = True
    return m


class TestContornos(unittest.TestCase):
    def test_cuadrado(self):
        # 10 x 10 pixeles: el borde pasa a medio pixel de los centros, con las
        # 4 esquinas cortadas a 45 grados -> area 100 - 4 * 1/8 = 99,5.
        c = cn.contornos(_bloque(20, 20, 5, 15, 5, 15))
        self.assertEqual(len(c), 1)
        self.assertAlmostEqual(cn.area_con_signo(c[0]), 99.5)

    def test_anillo_con_hueco(self):
        m = _bloque(20, 20, 3, 13, 3, 13)
        m[6:10, 6:10] = False
        areas = sorted(cn.area_con_signo(c) for c in cn.contornos(m))
        # Exterior antihorario (+), hueco horario (-).
        self.assertEqual(len(areas), 2)
        self.assertAlmostEqual(areas[0], -15.5)
        self.assertGreater(areas[1], 0)

    def test_dos_manchas(self):
        m = _bloque(20, 30, 2, 8, 2, 8) | _bloque(20, 30, 10, 18, 15, 25)
        self.assertEqual(len(cn.contornos(m)), 2)
        self.assertEqual(len(cn.contar_islas(m)), 2)

    def test_silla_de_montar(self):
        # Dos pixeles que solo se tocan en diagonal: dos islas y dos contornos
        # (contornos y BFS deben estar de acuerdo).
        m = np.zeros((6, 6), bool)
        m[2, 2] = m[3, 3] = True
        self.assertEqual(len(cn.contar_islas(m)), 2)
        self.assertEqual(len(cn.contornos(m)), 2)

    def test_borde_de_la_hoja(self):
        # Una mancha que toca el borde igual da un contorno cerrado.
        c = cn.contornos(_bloque(5, 5, 0, 5, 0, 5))
        self.assertEqual(len(c), 1)
        self.assertAlmostEqual(cn.area_con_signo(c[0]), 24.5)


class TestSimplificar(unittest.TestCase):
    def test_cuadrado_queda_en_8_puntos(self):
        # Lados rectos: sobran los puntos intermedios; quedan las 4 esquinas
        # cortadas (2 puntos cada una).
        c = cn.contornos(_bloque(20, 20, 5, 15, 5, 15))[0]
        self.assertEqual(len(cn.simplificar(c, 0.1)), 8)

    def test_circulo_respeta_la_tolerancia(self):
        y, x = np.mgrid[0:80, 0:80]
        c = cn.contornos((x - 40) ** 2 + (y - 40) ** 2 <= 30 ** 2)[0]
        s = np.array(cn.simplificar(c, 0.4) + [cn.simplificar(c, 0.4)[0]])
        self.assertLess(len(s), len(c))
        # Ningun punto original queda a mas de la tolerancia de la linea limpia.
        for p in np.asarray(c, float):
            d = min(cn._distancia_a_recta(p[None], s[k], s[k + 1])[0] for k in range(len(s) - 1))
            self.assertLessEqual(d, 0.4 + 1e-9)


class TestMorfologia(unittest.TestCase):
    def test_dilatar_un_pixel_da_un_disco(self):
        m = np.zeros((9, 9), bool)
        m[4, 4] = True
        self.assertEqual(cn.dilatar(m, 2).sum(), 13)   # dx^2 + dy^2 <= 4

    def test_zonas_delgadas(self):
        # Mancha gruesa con una "pata" de 1 pixel de ancho: solo la pata es fragil.
        m = _bloque(30, 40, 5, 25, 5, 20)
        m[15, 20:35] = True
        fragil = cn.zonas_delgadas(m, 2)
        self.assertTrue(fragil[15, 25:35].all())
        self.assertFalse(fragil[15, 12])


class TestReglas(unittest.TestCase):
    def test_tolerancia_no_borra_la_calibracion(self):
        desfases = sorted(config.PEINETA_DESFASES_MM)
        paso = min(round(b - a, 3) for a, b in zip(desfases, desfases[1:]))
        self.assertLessEqual(config.TOLERANCIA_MM, paso)
        self.assertLess(config.TOLERANCIA_MM, config.ANCHO_MIN_LASER_MM / 2)

    def test_cabeza_arriba_no_refleja(self):
        # Cabeza en +x, lado izquierdo de la cigarra en +y (vista cenital).
        hoja, _, _ = cabeza_arriba([[(10.0, 0.0), (0.0, 5.0), (0.0, -5.0)]], margen_mm=0)
        cabeza, izquierda, derecha = hoja[0]
        self.assertLess(cabeza[1], izquierda[1])         # cabeza arriba (y del SVG menor)
        self.assertLess(izquierda[0], cabeza[0])         # izquierda de la cigarra...
        self.assertLess(cabeza[0], derecha[0])           # ...a la izquierda de quien mira


if __name__ == "__main__":
    unittest.main()
