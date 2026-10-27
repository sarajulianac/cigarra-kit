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