# =============================================================================
# armado.py  -  Arbol de armado del kit 
#
# Cada nodo es una pieza del kit.
# El padre de un nodo es la pieza sobre la que va el nodo.
# La raiz es el chasis porque es la base, la primera pieza para armar.
#
# Es un arbol y no un grafo porque cada pieza se apoya sobre una sola pieza:
# cada pieza es una isla conectada, y las piezas de la capa de abajo no se tocan,
# entonces no puede quedar sobre dos a la vez.
# ===================================================================
import numpy as np
from . import curvas_nivel

class Nodo:
    def __init__(self, nombre, nivel, mascara):
        self.nombre = nombre
        self.nivel = nivel
        self.mascara = mascara
        self.padre = None
        self.hijos = []

    def agregar_hijo(self, hijo):
        self.hijos.append(hijo)
        hijo.padre = self 

def construir_arbol(chasis, capas):
    raiz = Nodo("chasis", 0, chasis)
    abajo = [raiz]
    for k, capa in enumerate(capas, start=1):
        este_nivel = []
        for n, isla in enumerate(curvas_nivel.islas(capa)):
            letra = "abcdefgh"[n]
            pieza = Nodo(f"capa_{k}_{letra}", k, isla)
            j, i = np.argwhere(isla)[0]
            for candidato in abajo:
                if candidato.mascara[j, i]:
                    candidato.agregar_hijo(pieza)
            este_nivel.append(pieza)
        abajo = este_nivel
    return raiz


def pasos_del_manual(raiz):
    pasos = []
    cola = [raiz]
    while cola:
        nodo = cola.pop(0)
        numero = len(pasos) + 1
        if nodo.padre is None:
            texto = f"Paso {numero}: {nodo.nombre} (la base)"
            pasos.append(texto)
        else:
            texto = f"Paso {numero}: {nodo.nombre} sobre {nodo.padre.nombre}"
            pasos.append(texto)
        for hijo in nodo.hijos:
            cola.append(hijo)
    return pasos
        