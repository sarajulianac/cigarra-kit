# Pruebas de la peineta: leen el SVG ya escrito (lo que recibe el laser) y
# miden las ranuras. Correr desde cigarra-kit:  python3 -m unittest -v
import re
import unittest
import xml.etree.ElementTree as ET

from cigarra import config, peineta

NS = "{http://www.w3.org/2000/svg}"


def _puntos(poligono):
    return [tuple(map(float, p.split(","))) for p in poligono.get("points").split()]


class TestPeineta(unittest.TestCase):
    def setUp(self):
        self.svg = ET.fromstring(peineta.peineta_svg().a_svg())
        self.cortes = self.svg.find(f"{NS}g[@id='corte']").findall(f"{NS}polygon")

    def test_hoja_en_milimetros(self):
        # width="..mm" y viewBox con los mismos numeros: 1 unidad = 1 mm.
        ancho = self.svg.get("width")
        self.assertTrue(ancho.endswith("mm"))
        self.assertEqual(float(ancho[:-2]), float(self.svg.get("viewBox").split()[2]))

    def test_ranuras_abiertas_carton(self):
        # El peine es el poligono que empieza en (MARGEN, MARGEN). Cada ranura
        # son los dos puntos del fondo (y = MARGEN + PROFUNDIDAD).
        peine = next(p for p in self.cortes if _puntos(p)[0] == (peineta.MARGEN, peineta.MARGEN))
        fondo = [x for x, y in _puntos(peine) if y == peineta.MARGEN + peineta.PROFUNDIDAD]
        anchos = [round(b - a, 3) for a, b in zip(fondo[::2], fondo[1::2])]
        self.assertEqual(anchos, [1.3, 1.4, 1.5, 1.6, 1.7, 1.8])

    def test_ranuras_cerradas_cartulina(self):
        huecos = [_puntos(p) for p in self.cortes if len(_puntos(p)) == 4][:6]
        anchos = [round(h[1][0] - h[0][0], 3) for h in huecos]
        largos = [round(h[2][1] - h[1][1], 3) for h in huecos]
        self.assertEqual(anchos, [0.2, 0.3, 0.4, 0.5, 0.6, 0.7])
        self.assertEqual(largos, [peineta.PROFUNDIDAD] * 6)

    def test_huecos_antes_que_bordes(self):
        # Los 6 huecos deben ir primero en el archivo (el laser corta en orden).
        self.assertEqual([len(_puntos(p)) for p in self.cortes[:6]], [4] * 6)

    def test_etiquetas_con_coma(self):
        textos = [t.text for t in self.svg.iter(f"{NS}text")]
        self.assertIn("1,5", textos)
        self.assertIn("0,4", textos)
        self.assertFalse(any(re.fullmatch(r"\d\.\d", t) for t in textos))

    def test_dientes_mas_anchos_que_el_laser(self):
        self.assertGreater(peineta.DIENTE, config.ANCHO_MIN_LASER_MM)


if __name__ == "__main__":
    unittest.main()
