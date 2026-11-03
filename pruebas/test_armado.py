# Pruebas del arbol de armado (armado.py, escrito por Sara) con capas
# inventadas cuyo arbol se sabe de antemano.
# Correr desde cigarra-kit con el Python de Blender (ver README).
import unittest

import numpy as np

from cigarra.armado import construir_arbol, pasos_del_manual


def _bloque(j0, j1, i0, i1):
    m = np.zeros((30, 40), bool)
    m[j0:j1, i0:i1] = True
    return m


class TestArbol(unittest.TestCase):
    def setUp(self):
        # Chasis grande; capa 1 = dos piezas separadas (la grande y un "ojo");
        # capa 2 = una pieza encima de la grande.
        self.chasis = _bloque(0, 30, 0, 40)
        grande, ojo = _bloque(2, 20, 2, 25), _bloque(22, 26, 30, 34)
        self.capas = [grande | ojo, _bloque(5, 12, 5, 15)]
        self.raiz = construir_arbol(self.chasis, self.capas)

    def test_raiz_es_el_chasis(self):
        self.assertEqual((self.raiz.nombre, self.raiz.nivel), ("chasis", 0))
        self.assertIsNone(self.raiz.padre)

    def test_cada_pieza_cuelga_de_la_que_la_sostiene(self):
        hijos = [h.nombre for h in self.raiz.hijos]
        self.assertEqual(hijos, ["capa_1_a", "capa_1_b"])       # la grande primero
        grande = self.raiz.hijos[0]
        self.assertEqual([h.nombre for h in grande.hijos], ["capa_2_a"])
        self.assertEqual(grande.hijos[0].padre.nombre, "capa_1_a")
        self.assertEqual(self.raiz.hijos[1].hijos, [])         # nada sobre el ojo

    def test_hijo_dentro_de_su_padre(self):
        pila = [self.raiz]
        while pila:
            n = pila.pop()
            for h in n.hijos:
                self.assertFalse((h.mascara & ~n.mascara).any())
            pila += n.hijos

    def test_manual_capa_por_capa(self):
        self.assertEqual(pasos_del_manual(self.raiz), [
            "Paso 1: chasis (la base)",
            "Paso 2: capa_1_a sobre chasis",
            "Paso 3: capa_1_b sobre chasis",
            "Paso 4: capa_2_a sobre capa_1_a",
        ])


if __name__ == "__main__":
    unittest.main()
