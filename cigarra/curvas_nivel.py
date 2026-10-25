# =============================================================================
# curvas_nivel.py  -  De una mascara de pixeles a contornos cerrados (lineas)
#
# El laser no corta pixeles, corta LINEAS. Aqui se traza el borde de una
# mascara (True = hay material) como se calca la orilla de un lago en papel
# cuadriculado, y despues se pasa en limpio.
#
# Sirve igual para el chasis (mascara = "donde hay cigarra") y para cada curva
# de nivel (mascara = "donde la altura >= corte k"): solo cambia la mascara.
#
# Todo es numpy puro: se prueba fuera de Blender (pruebas/test_curvas_nivel.py).
#
# Coordenadas: x = columna i, y = fila j, en PIXELES, con el centro del pixel
# (i, j) en (i, j). El eje y crece hacia arriba, como en la rejilla de vista.py.
# =============================================================================
from collections import deque

import numpy as np


# ---------------------- MORFOLOGIA (dilatar, erosionar) ----------------------
def _disco(radio_px):
    """Desplazamientos (dj, di) dentro de un circulo: el 'pincel' redondo."""
    r = int(radio_px)
    return [(dj, di) for dj in range(-r, r + 1) for di in range(-r, r + 1)
            if dj * dj + di * di <= radio_px * radio_px]


def _barrer(mascara, radio_px, juntar):
    """Pasa el pincel redondo por la mascara. juntar = OR (dilatar) o AND (erosionar)."""
    r = int(radio_px)
    if r == 0:
        return mascara.copy()
    # Borde de relleno: afuera de la hoja no hay material.
    grande = np.pad(mascara, r, constant_values=False)
    alto, ancho = mascara.shape
    resultado = None
    for dj, di in _disco(radio_px):
        corrida = grande[r + dj:r + dj + alto, r + di:r + di + ancho]
        resultado = corrida.copy() if resultado is None else juntar(resultado, corrida)
    return resultado


def dilatar(mascara, radio_px):
    """Engorda la mancha radio_px en todas direcciones (offset hacia afuera).
    Con un pincel REDONDO el margen mide lo mismo en diagonal que de frente."""
    return _barrer(mascara, radio_px, np.logical_or)


def erosionar(mascara, radio_px):
    """Adelgaza la mancha radio_px: sobrevive lo que tiene el pincel entero adentro."""
    return _barrer(mascara, radio_px, np.logical_and)


def zonas_delgadas(mascara, radio_px):
    """Apertura morfologica: lo que desaparece al erosionar y volver a dilatar
    es mas angosto que el pincel (2 * radio + 1 pixeles)."""
    return mascara & ~dilatar(erosionar(mascara, radio_px), radio_px)


# ---------------------- ISLAS (BFS) ------------------------------------------
def contar_islas(mascara):
    """Busqueda en anchura sobre la rejilla. Cada isla es una pieza fisica
    separada: si el chasis tiene mas de una, algo se cae al cortarlo.
    Vecinos = arriba, abajo, izquierda, derecha (los de esquina no cuentan,
    igual que en los contornos)."""
    alto, ancho = mascara.shape
    visto = np.zeros(mascara.shape, bool)
    tamanos = []
    for j0, i0 in zip(*np.nonzero(mascara)):
        if visto[j0, i0]:
            continue
        visto[j0, i0] = True
        cola, n = deque([(j0, i0)]), 0
        while cola:
            j, i = cola.popleft()
            n += 1
            for a, b in ((j + 1, i), (j - 1, i), (j, i + 1), (j, i - 1)):
                if 0 <= a < alto and 0 <= b < ancho and mascara[a, b] and not visto[a, b]:
                    visto[a, b] = True
                    cola.append((a, b))
        tamanos.append(n)
    return tamanos


# ---------------------- MARCHING SQUARES -------------------------------------
def _cruza(p, q, c):
    """Producto cruz (q - p) x (c - p): positivo si c queda a la IZQUIERDA de p->q."""
    return (q[0] - p[0]) * (c[1] - p[1]) - (q[1] - p[1]) * (c[0] - p[0])


def contornos(mascara):
    """Borde de la mascara como lista de polilineas cerradas [(x, y), ...].

    Se mira cada ventanita de 2x2 centros de pixel. Cada esquina esta dentro
    o fuera: 16 combinaciones, y cada una dice por donde cruza la orilla (por
    el punto medio de los lados que unen una esquina de adentro con una de
    afuera). Los pedacitos se orientan con el material a la IZQUIERDA, asi el
    borde exterior gira antihorario (area > 0) y los huecos horario (area < 0).
    """
    m = np.pad(mascara.astype(bool), 1, constant_values=False)
    # Solo interesan las ventanas mixtas (ni todo dentro ni todo fuera).
    suma = (m[:-1, :-1].astype(int) + m[:-1, 1:] + m[1:, :-1] + m[1:, 1:])
    siguiente = {}   # punto de inicio -> punto final de cada pedacito
    for j, i in zip(*np.nonzero((suma > 0) & (suma < 4))):
        # Esquinas en orden antihorario: abajo-izq, abajo-der, arriba-der, arriba-izq.
        esq = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
        den = [m[j, i], m[j, i + 1], m[j + 1, i + 1], m[j + 1, i]]
        # Punto medio del lado k (entre la esquina k y la k+1).
        medio = [((esq[k][0] + esq[(k + 1) % 4][0]) / 2, (esq[k][1] + esq[(k + 1) % 4][1]) / 2)
                 for k in range(4)]
        if den == [True, False, True, False] or den == [False, True, False, True]:
            # Silla de montar: dos esquinas opuestas adentro. Se separan (como
            # en contar_islas): cada esquina de adentro se lleva su pedacito.
            pedazos = [(medio[(k - 1) % 4], medio[k], esq[k]) for k in range(4) if den[k]]
        else:
            lados = [k for k in range(4) if den[k] != den[(k + 1) % 4]]
            adentro = esq[den.index(True)]
            pedazos = [(medio[lados[0]], medio[lados[1]], adentro)]
        for p, q, c in pedazos:
            if _cruza(p, q, c) < 0:      # que el material quede a la izquierda
                p, q = q, p
            siguiente[p] = q

    # Coser: seguir de punto en punto hasta volver al inicio.
    resultado = []
    while siguiente:
        inicio, punto = next(iter(siguiente.items()))
        del siguiente[inicio]
        anillo = [inicio]
        while punto != inicio:
            anillo.append(punto)
            punto = siguiente.pop(punto)
        # Quitar el relleno de 1 pixel del np.pad.
        resultado.append([(x - 1, y - 1) for x, y in anillo])
    return resultado


def area_con_signo(polilinea):
    """Formula del cordon de zapato. > 0 antihorario (borde exterior), < 0 hueco."""
    p = np.asarray(polilinea, float)
    x, y = p[:, 0], p[:, 1]
    return 0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(np.roll(x, -1), y))


# ---------------------- SIMPLIFICACION (Douglas-Peucker) ---------------------
def _distancia_a_recta(puntos, a, b):
    """Distancia de cada punto a la recta (segmento) a-b."""
    ab = b - a
    largo2 = float(np.dot(ab, ab))
    if largo2 == 0.0:
        return np.linalg.norm(puntos - a, axis=1)
    t = np.clip((puntos - a) @ ab / largo2, 0.0, 1.0)
    return np.linalg.norm(puntos - (a + t[:, None] * ab), axis=1)


def _dp_abierta(p, tolerancia):
    """Douglas-Peucker sobre una polilinea abierta. Una banda de caucho entre los
    extremos: si ningun punto se aleja mas que la tolerancia, sobran todos; si no,
    se clava en el mas lejano y se repite a cada lado. Con pila, sin recursion."""
    conservar = np.zeros(len(p), bool)
    conservar[0] = conservar[-1] = True
    pila = [(0, len(p) - 1)]
    while pila:
        a, b = pila.pop()
        if b - a < 2:
            continue
        d = _distancia_a_recta(p[a + 1:b], p[a], p[b])
        k = int(np.argmax(d))
        if d[k] > tolerancia:
            k += a + 1
            conservar[k] = True
            pila += [(a, k), (k, b)]
    return conservar


def contornos_mm(mascara, pixel_mm, tolerancia_mm):
    """Todo junto: borde -> milimetros -> linea limpia. Devuelve las polilineas
    en mm y cuantos puntos tenian antes de simplificar."""
    crudos = contornos(mascara)
    limpios = [simplificar([(x * pixel_mm, y * pixel_mm) for x, y in c], tolerancia_mm)
               for c in crudos]
    return limpios, sum(len(c) for c in crudos)


def simplificar(polilinea, tolerancia):
    """Douglas-Peucker para un contorno CERRADO: se parte en dos en el punto mas
    lejano del primero y se simplifica cada mitad como polilinea abierta."""
    p = np.asarray(polilinea, float)
    if len(p) < 4:
        return [tuple(q) for q in p]
    lejos = int(np.argmax(np.linalg.norm(p - p[0], axis=1)))
    ida = _dp_abierta(p[:lejos + 1], tolerancia)
    vuelta = _dp_abierta(np.vstack([p[lejos:], p[:1]]), tolerancia)
    conservar = np.concatenate([ida, vuelta[1:-1]])
    return [tuple(q) for q in p[conservar]]
