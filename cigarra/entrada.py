# =============================================================================
# entrada.py  -  De la cigarra en Blender a una malla en lista indexada
#
# Paso 1 del pipeline (retroalimentacion del 20 oct): tomar el modelo y
# QUITARLE LAS ALAS. Las alas se generan aparte, por algoritmo (alas.py).
#
# Lista indexada = como guarda Blender la malla:
#   vertices   tabla de puntos (x, y, z), cada uno UNA sola vez
#   triangulos cada triangulo son 3 numeros de fila de esa tabla
# Basta para lo que viene (lanzar rayos): nadie le pregunta a la malla
# "quien es mi vecino", solo "donde esta este triangulo".
# =============================================================================
from dataclasses import dataclass

import bpy
import numpy as np

# Piezas que NO van en el cuerpo: se comparan con las palabras del nombre
# (C_Ala_Ant_L -> ["C", "Ala", "Ant", "L"]), no con pedazos de texto sueltos.
EXCLUIR = ("Ala", "Vena")


@dataclass
class Malla:
    vertices: np.ndarray            # (N, 3) float: x, y, z en el marco de la cigarra
    triangulos: np.ndarray          # (M, 3) int: filas de `vertices`
    parte_de_triangulo: np.ndarray  # (M,) int: a que pieza pertenece cada triangulo
    nombres: list                   # nombres[k] = nombre de la pieza k


def partes_del_cuerpo(raiz, excluir=EXCLUIR):
    """Hijos de malla de la raiz (a cualquier profundidad), sin las piezas excluidas."""
    partes = [o for o in raiz.children_recursive
              if o.type == 'MESH' and not set(o.name.split("_")) & set(excluir)]
    return sorted(partes, key=lambda o: o.name)


def cargar_cuerpo(nombre_raiz="Cigarra", excluir=EXCLUIR):
    """Junta todas las piezas del cuerpo en una sola Malla, en el marco propio de la cigarra."""
    raiz = bpy.data.objects[nombre_raiz]
    # Marco propio: se deshace la posicion/rotacion de la raiz en la escena, asi
    # la cigarra queda centrada y alineada aunque la hayan movido.
    inversa_raiz = np.array(raiz.matrix_world.inverted())
    dg = bpy.context.evaluated_depsgraph_get()

    todos_v, todos_t, todas_p, nombres = [], [], [], []
    n_vertices = 0
    for k, obj in enumerate(partes_del_cuerpo(raiz, excluir)):
        evaluado = obj.evaluated_get(dg)        # con modificadores aplicados
        me = evaluado.to_mesh()
        me.calc_loop_triangles()                 # Blender parte cada cara en triangulos

        co = np.empty(len(me.vertices) * 3, np.float64)
        me.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3)
        tri = np.empty(len(me.loop_triangles) * 3, np.int64)
        me.loop_triangles.foreach_get("vertices", tri)
        tri = tri.reshape(-1, 3)
        evaluado.to_mesh_clear()

        # Matriz 4x4 de la pieza al marco de la cigarra. Coordenadas homogeneas:
        # se agrega un 1 a cada punto para que la traslacion entre en el producto.
        M = inversa_raiz @ np.array(obj.matrix_world)
        co = (np.c_[co, np.ones(len(co))] @ M.T)[:, :3]

        todos_v.append(co)
        todos_t.append(tri + n_vertices)         # los indices se corren: la tabla crece
        todas_p.append(np.full(len(tri), k))
        nombres.append(obj.name)
        n_vertices += len(co)

    return Malla(np.vstack(todos_v), np.vstack(todos_t), np.concatenate(todas_p), nombres)
