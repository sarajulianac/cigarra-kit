# alas_procedurales.py — Cigarra para armar · Sara Cuadrado · CVI 2026-2
#
# Genera alas de cigarra a partir de parámetros, en 3 piezas:
#   1. ESTRUCTURA  (PLA, impresión 3D): venas gruesas + raíz que entra a la esfera del hombro
#   2. MEMBRANA    (acetato, láser): el contorno del ala, transparente
#   3. ADHESIVO    (vinilo, plotter de corte): venas finas que se pegan sobre la membrana
#
# Se corre dentro de Mecanismo_Alas.blend. NO toca la cigarra: todo va a la colección
# "Propuestas_Alas", al lado. Cada versión (A, B) es un diccionario de parámetros.
#
# Marco de cada ala (mm): la raíz en el origen, el ala crece hacia +y,
# la costa (borde de ataque) hacia +x. Es el mismo marco de Pose_Ant / Pose_Post.

import bpy, bmesh, math, random
from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt

MM = 0.001  # 1 mm en unidades de Blender

# ------------------------------------------------------------------ parámetros
# Contorno normalizado: (x / media_cuerda, y / largo), en sentido antihorario:
# sube por la costa, rodea el ápice y baja por el borde de fuga.
CONTORNO_ANT = [(0.08, 0.02), (0.32, 0.10), (0.58, 0.30), (0.76, 0.55), (0.80, 0.76),
                (0.62, 0.92), (0.22, 1.00), (-0.25, 0.985), (-0.70, 0.90), (-0.98, 0.72),
                (-0.96, 0.50), (-0.76, 0.30), (-0.50, 0.14), (-0.25, 0.05), (-0.06, 0.02)]
CONTORNO_POST = [(0.15, 0.12), (0.55, 0.25), (0.70, 0.50), (0.60, 0.75), (0.35, 0.93),
                 (0.00, 1.00), (-0.40, 0.95), (-0.80, 0.78), (-1.00, 0.55), (-0.95, 0.30),
                 (-0.60, 0.10), (-0.20, 0.05)]

ALA_ANT = dict(contorno=CONTORNO_ANT, largo=275, media_cuerda=38,
               venas=4, ultima_sin_bifurcar=True,          # 4 venas -> 8 celdas apicales
               nodal_costa=0.62, nodal_fuga=0.50,           # línea nodal (oblicua)
               basal=0.22, clavales=(0.28, 0.40),
               ambiental_costa=0.66, ambiental_fuga=0.52,
               fracciones=(0.14, 0.38, 0.62, 0.84), de_rm=2)
ALA_POST = dict(contorno=CONTORNO_POST, largo=157, media_cuerda=30,
                venas=3, ultima_sin_bifurcar=True,          # 3 venas -> 6 celdas apicales
                nodal_costa=0.56, nodal_fuga=0.46,
                basal=0.27, clavales=(0.38,),
                ambiental_costa=0.62, ambiental_fuga=0.50,
                fracciones=(0.2, 0.5, 0.8), de_rm=1)

VERSIONES = {
    "A": dict(nombre="A · limpia (verde)", color=(0.35, 0.75, 0.35, 1.0),
              # la estructura llega hasta la línea nodal; afuera de ella, todo es adhesivo
              estructura_hasta_nodal=True, costa_hasta=0.80, marco=False,
              ancho_costa=(3.5, 2.2), ancho_vena=(2.2, 1.6), ancho_fino=0.6,
              voronoi=None, origen=(0.22, 0.0)),
    "B": dict(nombre="B · tupida (ámbar)", color=(0.95, 0.55, 0.12, 1.0),
              # la estructura es toda la venación principal + un marco en el borde;
              # el adhesivo es una red secundaria de Voronoi dentro de las celdas
              estructura_hasta_nodal=False, costa_hasta=1.0, marco=True,
              ancho_costa=(3.0, 1.8), ancho_vena=(1.8, 1.2), ancho_fino=0.5,
              voronoi=dict(separacion=8.0, alargamiento=1.9, desde=0.18, semilla=7),
              origen=(0.43, 0.0)),
    "C": dict(nombre="C · orgánica (ant.)", color=(0.45, 0.85, 0.15, 1.0),
              # venas curvas en abanico, bifurcaciones en Y suave, borde continuo
              organica=True, solo_anterior=True, ancho_fino=0.6,
              origen=(0.63, 0.0)),
    "D": dict(nombre="D · boceto de Sara", color=(0.25, 0.8, 0.3, 1.0),
              # la regla de bifurcación la escribe Sara en mis_reglas.py
              sara=True, solo_anterior=True, ancho_fino=0.6,
              origen=(0.75, 0.0)),
}

# Versión D (boceto de Sara): rieles en V + abanico de venas que se bifurcan y quedan libres
D_NUDO_U = 0.06                       # el circulito sobre la raíz: de ahí salen las venas
D_VENAS = [0.22, 0.42, 0.62, 0.80]    # hacia qué v apunta cada vena del abanico
D_LARGO = 0.38                        # cuánto sube cada vena antes de dividirse (en u)
D_ABERTURA = 0.14                     # cuánto se separan las dos hijas (en v)
D_GENERACIONES = 1                    # cuántas veces se divide
D_COSTA_HASTA = 0.78                  # hasta dónde llega el riel grueso de la costa
D_FUGA_HASTA = 0.55                   # hasta dónde llega el riel grueso del borde de fuga

# Árbol de venas del ala anterior (versión C), en coordenadas del ala (u, v):
#   u = a lo largo del ala (0 = base, 1 = ápice), medido por longitud de arco de cada borde
#   v = de través (0 = costa, 1 = borde de fuga)
# Un dict con u, v es una BIFURCACIÓN. Una HOJA es ("C", u) o ("T", u): la vena llega al borde
# de la costa (C) o al borde de fuga (T) a esa altura u. v0 = dónde arranca la vena en la base.
ARBOL_ANT = [
    dict(v0=0.14, w=2.4, u=0.50, v=0.13, hijos=[("C", 0.70),
         dict(u=0.72, v=0.15, hijos=[("C", 0.82), ("C", 0.90)])]),                               # R
    dict(v0=0.30, w=2.2, u=0.45, v=0.40, hijos=[
         dict(u=0.73, v=0.32, hijos=[("C", 0.97), ("T", 0.96)]),
         dict(u=0.70, v=0.60, hijos=[("T", 0.89), ("T", 0.81)])]),                              # M
    dict(v0=0.48, w=2.2, u=0.36, v=0.68, hijos=[
         dict(u=0.60, v=0.80, hijos=[("T", 0.73), ("T", 0.64)]), ("T", 0.48)]),                # Cu
    dict(v0=0.72, w=1.6, hijos=[("T", 0.30)]),                                                  # clavales
    dict(v0=0.86, w=1.4, hijos=[("T", 0.19)]),
]
# Ala posterior (versión C): 3 venas -> 6 celdas apicales
ARBOL_POST = [
    dict(v0=0.15, w=2.2, u=0.50, v=0.14, hijos=[("C", 0.72), ("C", 0.86)]),                     # R
    dict(v0=0.35, w=2.0, u=0.45, v=0.42, hijos=[
         dict(u=0.72, v=0.40, hijos=[("C", 0.97), ("T", 0.95)]), ("T", 0.84)]),                 # M
    dict(v0=0.55, w=2.0, u=0.38, v=0.70, hijos=[("T", 0.70), ("T", 0.55)]),                     # Cu
    dict(v0=0.80, w=1.4, hijos=[("T", 0.32)]),                                                  # clavál
]
FILAS_TRANSVERSALES = [(0.56, 0.03), (0.80, 0.02)]   # (r, escalonado): arcos de celdas
COSTA_HASTA = 0.50     # la costa gruesa llega hasta el ápice; de ahí sigue el borde fino

GROSOR_ESTRUCTURA = 1.2   # mm, PLA
GROSOR_MEMBRANA = 0.25    # mm, acetato
GROSOR_ADHESIVO = 0.1     # mm, vinilo
INICIO_ALA = 18.0         # mm: donde termina la lengüeta de la raíz (Raiz_Ant / Raiz_Post)
SEPARACION_POST = 85.0    # mm: el ala posterior se muestra al lado de la anterior


# ------------------------------------------------------------------ geometría 2D
def longitud_arco(puntos):
    """Suma de distancias entre puntos consecutivos (la de Sara, de plantillas_cigarra.py)."""
    return sum((puntos[i + 1] - puntos[i]).length for i in range(len(puntos) - 1))


def punto_en_arco(puntos, s):
    """El punto que está a distancia s (medida a lo largo de la curva) desde el inicio."""
    for i in range(len(puntos) - 1):
        d = (puntos[i + 1] - puntos[i]).length
        if s <= d:
            return puntos[i].lerp(puntos[i + 1], s / d if d else 0)
        s -= d
    return puntos[-1].copy()


def catmull_rom_cerrada(P, pasos=16):
    """Curva suave que pasa por todos los puntos de control P (cerrada)."""
    n, out = len(P), []
    for i in range(n):
        p0, p1, p2, p3 = P[i - 1], P[i], P[(i + 1) % n], P[(i + 2) % n]
        for k in range(pasos):
            t = k / pasos
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    return out


def desplazar(poly, d):
    """Contorno paralelo hacia adentro, a distancia d (poly en sentido antihorario)."""
    n, out = len(poly), []
    for i in range(n):
        t = (poly[(i + 1) % n] - poly[i - 1]).normalized()
        out.append(poly[i] + Vector((-t.y, t.x)) * d)
    return out


def x_en_y(poly, y, lado):
    """Dónde cruza el contorno la horizontal y: lado 'costa' (x mayor) o 'fuga' (x menor)."""
    xs = []
    for i in range(len(poly)):
        a, b = poly[i], poly[(i + 1) % len(poly)]
        if (a.y - y) * (b.y - y) <= 0 and a.y != b.y:
            xs.append(a.x + (y - a.y) / (b.y - a.y) * (b.x - a.x))
    return max(xs) if lado == "costa" else min(xs)


def adentro(poly, p):
    c, n = False, len(poly)
    for i in range(n):
        a, b = poly[i], poly[i - 1]
        if (a.y > p.y) != (b.y > p.y) and p.x < (b.x - a.x) * (p.y - a.y) / (b.y - a.y) + a.x:
            c = not c
    return c


def recortar(poly, a, b):
    """Recorta el segmento ab al interior del contorno (None si queda afuera)."""
    ia, ib = adentro(poly, a), adentro(poly, b)
    if ia and ib:
        return a, b
    if not ia and not ib:
        return None
    for i in range(len(poly)):
        c, d = poly[i], poly[(i + 1) % len(poly)]
        r, s = b - a, d - c
        den = r.x * s.y - r.y * s.x
        if abs(den) < 1e-12:
            continue
        t = ((c - a).x * s.y - (c - a).y * s.x) / den
        u = ((c - a).x * r.y - (c - a).y * r.x) / den
        if 0 <= t <= 1 and 0 <= u <= 1:
            q = a + r * t
            return (a, q) if ia else (q, b)
    return None


def curva(a, b, comba=0.0, pasos=8):
    """Vena de a a b, levemente curva (comba en mm, hacia la costa)."""
    m = (a + b) / 2
    n = Vector((-(b - a).y, (b - a).x)).normalized()
    c = m + n * comba
    return [a.lerp(c, t).lerp(c.lerp(b, t), t) for t in (k / pasos for k in range(pasos + 1))]


# ------------------------------------------------------------------ el ala
def venacion(ala, v):
    """Devuelve el contorno y dos listas de venas: (polilínea, ancho_inicio, ancho_fin)."""
    L, H = ala["largo"], ala["media_cuerda"]
    contorno = catmull_rom_cerrada([Vector((x * H, y * L)) for x, y in ala["contorno"]])
    i_apice = max(range(len(contorno)), key=lambda i: contorno[i].y)
    adentro_1 = desplazar(contorno, 1.6)

    estructura, adhesivo = [], []
    E = estructura
    F = adhesivo if v["estructura_hasta_nodal"] else estructura
    vc0, vc1 = v["ancho_costa"]
    vv0, vv1 = v["ancho_vena"]
    fino = v["ancho_fino"]

    # Costa: el borde de ataque, la vena más gruesa
    off_c = desplazar(contorno, vc0 / 2)
    costa = [off_c[i] for i in range(i_apice + 1)
             if INICIO_ALA <= contorno[i].y <= v["costa_hasta"] * L]
    E.append((costa, vc0, vc1))

    # Célula basal: S es la punta de la lengüeta; de ahí salen el tallo R+M y el Cu
    S = Vector((0, INICIO_ALA))
    yb = ala["basal"] * L
    P_rm = Vector((x_en_y(adentro_1, yb, "fuga") * 0.38 + x_en_y(adentro_1, yb, "costa") * 0.62, yb))
    P_cu = Vector((x_en_y(adentro_1, yb * 0.92, "fuga") * 0.65 + x_en_y(adentro_1, yb * 0.92, "costa") * 0.35, yb * 0.92))
    E.append(([S, costa[0]], vc0 * 0.9, vc0 * 0.9))
    E.append((curva(S, P_rm, 1.5), vv0 * 1.2, vv0 * 1.1))
    E.append((curva(S, P_cu, -1.5), vv0 * 1.2, vv0 * 1.1))
    E.append(([P_rm, P_cu], vv1, vv1))  # arcúlo: cierra la célula basal

    # Línea nodal (oblicua) y las venas largas que llegan a ella
    yc, yf = ala["nodal_costa"] * L, ala["nodal_fuga"] * L
    Nc = Vector((x_en_y(adentro_1, yc, "costa"), yc))
    Nf = Vector((x_en_y(adentro_1, yf, "fuga"), yf))
    N = [Nc.lerp(Nf, f) for f in ala["fracciones"]]
    for i, n in enumerate(N):
        o = P_rm if i < ala["de_rm"] else P_cu
        E.append((curva(o, n, 2.0), vv0, vv1))
    E.append(([Nc] + N + [Nf], vv1, vv1))

    # Venas clavales: del tallo al borde de fuga
    for t in ala["clavales"]:
        y = t * L
        E.append((curva(S, Vector((x_en_y(adentro_1, y, "fuga"), y)), -2.0), vv1, vv1 * 0.8))

    # Vena ambiental: corre paralela al borde en la zona apical
    off_a = desplazar(contorno, 2.5)
    ya_c, ya_f = ala["ambiental_costa"] * L, ala["ambiental_fuga"] * L
    ambiental = [off_a[i] for i in range(len(contorno))
                 if (i <= i_apice and contorno[i].y >= ya_c) or (i > i_apice and contorno[i].y >= ya_f)]
    F.append((ambiental, fino if F is adhesivo else vv1, fino if F is adhesivo else vv1))

    # Bifurcaciones: cada vena se abre en 2 al llegar a la ambiental -> celdas apicales.
    # Los puntos de llegada se reparten por longitud de arco a lo largo de la ambiental.
    n_fin = 2 * len(N) - (1 if ala["ultima_sin_bifurcar"] else 0)
    La = longitud_arco(ambiental)
    llegadas = [punto_en_arco(ambiental, La * (k + 1) / (n_fin + 1)) for k in range(n_fin)]
    horquillas, k = [], 0
    for i, n in enumerate(N):
        cuantas = 1 if (ala["ultima_sin_bifurcar"] and i == len(N) - 1) else 2
        destinos = llegadas[k:k + cuantas]; k += cuantas
        centro = sum(destinos, Vector((0, 0))) / len(destinos)
        h = n.lerp(centro, 0.3)
        horquillas.append(h)
        F.append(([n, h], fino if F is adhesivo else vv1, fino if F is adhesivo else vv1))
        for d in destinos:
            F.append((curva(h, d, 1.0), fino if F is adhesivo else vv1, fino if F is adhesivo else vv1 * 0.9))
    # venas transversales entre horquillas (la segunda fila de celdas)
    adhesivo.append((horquillas, fino, fino))

    # B: marco por todo el borde (el ala queda tensa como un bastidor)
    if v["marco"]:
        off_m = desplazar(contorno, vv1 / 2 + 0.4)
        marco = [off_m[i] for i in range(len(contorno)) if contorno[i].y >= INICIO_ALA - 4]
        E.append((marco, vv1, vv1))
    else:
        # A: el borde de fuga en la zona del clavo también lleva una vena fina
        tramo = [off_a[i] for i in range(i_apice, len(contorno))
                 if ala["clavales"][-1] * L <= contorno[i].y <= ya_f + 2]
        adhesivo.append((tramo, fino, fino))

    # B: red secundaria de Voronoi (células alargadas a lo largo del ala)
    if v["voronoi"]:
        adhesivo.extend(red_voronoi(contorno, ala, v["voronoi"], fino))

    return contorno, estructura, adhesivo


def red_voronoi(contorno, ala, p, fino):
    """Venas secundarias: el dual de una triangulación de Delaunay de puntos al azar.
    Se calcula en un espacio estirado (y / alargamiento) para que las celdas salgan largas."""
    rnd = random.Random(p["semilla"])
    k, sep = p["alargamiento"], p["separacion"]
    xs = [q.x for q in contorno]; ys = [q.y for q in contorno]
    semillas = []
    for _ in range(6000):  # muestreo por dardos: ningún par más cerca que 'sep'
        q = Vector((rnd.uniform(min(xs) - sep, max(xs) + sep), rnd.uniform(min(ys) - sep, max(ys) + sep) / k))
        if all((q - s).length >= sep for s in semillas):
            semillas.append(q)
    vs, _, caras, *_ = delaunay_2d_cdt(semillas, [], [], 0, 1e-6)
    def circuncentro(a, b, c):
        d = 2 * (a.x * (b.y - c.y) + b.x * (c.y - a.y) + c.x * (a.y - b.y))
        ux = ((a.length_squared) * (b.y - c.y) + (b.length_squared) * (c.y - a.y) + (c.length_squared) * (a.y - b.y)) / d
        uy = ((a.length_squared) * (c.x - b.x) + (b.length_squared) * (a.x - c.x) + (c.length_squared) * (b.x - a.x)) / d
        return Vector((ux, uy * k))  # volver al espacio real
    centros = [circuncentro(*(Vector(vs[i]) for i in f)) for f in caras]
    vecinos = {}
    for fi, f in enumerate(caras):
        for j in range(3):
            vecinos.setdefault(tuple(sorted((f[j], f[(j + 1) % 3]))), []).append(fi)
    zona = desplazar(contorno, 2.5)
    venas = []
    for fs in vecinos.values():
        if len(fs) != 2:
            continue
        a, b = centros[fs[0]], centros[fs[1]]
        if min(a.y, b.y) < p["desde"] * ala["largo"]:
            continue
        r = recortar(zona, a, b)
        if r:
            venas.append(([r[0], r[1]], fino, fino))
    return venas


# ------------------------------------------------------------------ versión orgánica
def suave(t):
    """smoothstep: arranca y llega con pendiente 0 -> las ramas salen tangentes a la madre."""
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def venacion_organica(ala, v):
    """Venas en coordenadas del ala: P(u, v) = costa(u) + v * (fuga(u) - costa(u)).
    costa(u) y fuga(u) recorren cada borde desde la raíz hasta el ápice por longitud de arco,
    así que una vena con v constante corre paralela al contorno y todas se cierran en el ápice.
    Entre bifurcaciones v cambia con smoothstep (las hijas salen tangentes a la madre);
    el último tramo cae al borde con t² (sale recto y entra al borde en ángulo)."""
    L, H = ala["largo"], ala["media_cuerda"]
    contorno = catmull_rom_cerrada([Vector((x * H, y * L)) for x, y in ala["contorno"]])
    borde_in = desplazar(contorno, 1.6)
    i_ap = max(range(len(borde_in)), key=lambda i: borde_in[i].y)
    lado_c = [p for p in borde_in[:i_ap + 1] if p.y >= INICIO_ALA - 6]
    lado_t = [p for p in reversed(borde_in[i_ap:]) if p.y >= INICIO_ALA - 6] + [borde_in[i_ap]]
    Lc, Lt = longitud_arco(lado_c), longitud_arco(lado_t)
    B = Vector((0, INICIO_ALA))

    def P(u, v_):
        c = punto_en_arco(lado_c, u * Lc); t = punto_en_arco(lado_t, u * Lt)
        return c.lerp(t, v_)

    def uv(n):
        if isinstance(n, tuple):
            return (n[1], 0.0 if n[0] == "C" else 1.0)
        return (n["u"], n["v"])

    tramos = []  # (ua, va, ub, vb, w0, w1, es_hoja)

    def rama(n, ua, va, w):
        ub, vb = uv(n)
        if isinstance(n, tuple):
            tramos.append((ua, va, ub, vb, w, w * 0.6, True)); return
        tramos.append((ua, va, ub, vb, w, w * 0.85, False))
        for c in n["hijos"]:
            rama(c, ub, vb, w * 0.78)

    est = []
    arbol = ARBOL_POST if ala is ALA_POST else ARBOL_ANT
    for n in arbol:
        u0 = 0.05
        est.append(([B, P(u0, n["v0"])], n["w"], n["w"]))
        if "u" in n:
            rama(n, u0, n["v0"], n["w"])
        else:
            for c in n["hijos"]:
                rama(c, u0, n["v0"], n["w"])

    def en(t, k):
        ua, va, ub, vb, *_ , hoja = t
        u_ = ua + (ub - ua) * k
        v_ = va + (vb - va) * (k * k if hoja else suave(k))
        return u_, v_

    for t in tramos:
        est.append(([P(*en(t, k / 30)) for k in range(31)], t[4], t[5]))

    # Transversales: unen venas vecinas a una misma altura u (escalonada)
    for fila, (uc, esc) in enumerate(FILAS_TRANSVERSALES):
        act = [t for t in tramos if t[2] != t[0] and min(t[0], t[2]) < uc < max(t[0], t[2])]
        v_en = lambda t, u_: en(t, (u_ - t[0]) / (t[2] - t[0]))[1]
        act.sort(key=lambda t: v_en(t, uc))
        for k, (ta, tb) in enumerate(zip(act, act[1:])):
            u_ = uc + esc * math.sin(2.3 * k + fila)
            # la altura escalonada tiene que quedar dentro de los dos tramos
            u_ = max(u_, min(ta[0], ta[2]) + 0.01, min(tb[0], tb[2]) + 0.01)
            u_ = min(u_, max(ta[0], ta[2]) - 0.01, max(tb[0], tb[2]) - 0.01)
            va, vb = v_en(ta, u_), v_en(tb, u_)
            pa, pb = P(u_, va), P(u_, vb)
            if 0.5 < (pa - pb).length < 30:
                est.append(([P(u_, va + (vb - va) * j / 6) for j in range(7)], 1.0, 1.0))

    # Borde: costa gruesa de la raíz al ápice, y vena marginal fina por el borde de fuga
    off = desplazar(contorno, 1.4)
    i2 = max(range(len(off)), key=lambda i: off[i].y)
    costa = [p for p in off[:i2 + 1] if p.y >= INICIO_ALA - 6]
    marg = [p for p in off[i2:] if p.y >= INICIO_ALA - 6]
    est.append((costa, 3.6, 2.0))
    est.append((marg, 2.0, 1.2))
    est.append(([B, costa[0]], 3.0, 3.0))
    return contorno, est, []


def coordenadas_ala(ala):
    """Contorno y la función P(u, v) -> punto (mm) en las coordenadas del ala."""
    L, H = ala["largo"], ala["media_cuerda"]
    contorno = catmull_rom_cerrada([Vector((x * H, y * L)) for x, y in ala["contorno"]])
    borde_in = desplazar(contorno, 1.6)
    i_ap = max(range(len(borde_in)), key=lambda i: borde_in[i].y)
    lado_c = [p for p in borde_in[:i_ap + 1] if p.y >= INICIO_ALA - 6]
    lado_t = [p for p in reversed(borde_in[i_ap:]) if p.y >= INICIO_ALA - 6] + [borde_in[i_ap]]
    Lc, Lt = longitud_arco(lado_c), longitud_arco(lado_t)

    def P(u, v_):
        return punto_en_arco(lado_c, u * Lc).lerp(punto_en_arco(lado_t, u * Lt), v_)
    return contorno, P


def cargar_reglas_de_sara():
    """Lee mis_reglas.py (junto al .blend) y devuelve su función bifurcar, o None."""
    import os
    ruta = os.path.join(os.path.dirname(bpy.data.filepath), "mis_reglas.py")
    if not os.path.exists(ruta):
        print("· No encuentro mis_reglas.py"); return None
    g = {"__name__": "mis_reglas"}
    exec(compile(open(ruta, encoding="utf-8").read(), ruta, "exec"), g)
    return g.get("bifurcar")


def venacion_sara(ala, v):
    contorno, P = coordenadas_ala(ala)
    B = Vector((0, INICIO_ALA))
    est = []

    # Rieles en V: costa y borde de fuga, gruesos y adelgazándose
    for v_, hasta, w0, w1 in ((0.0, D_COSTA_HASTA, 3.8, 2.0), (1.0, D_FUGA_HASTA, 3.2, 1.6)):
        est.append(([B] + [P(D_NUDO_U + (hasta - D_NUDO_U) * k / 40, v_) for k in range(41)], w0, w1))

    # El nudo (circulito) de donde sale el abanico
    nudo = P(D_NUDO_U, 0.5)
    est.append(([B, nudo], 3.0, 3.0))
    est.append(([nudo + Vector((math.cos(a), math.sin(a))) * 3.2 for a in
                 (2 * math.pi * k / 24 for k in range(25))], 1.4, 1.4))

    # Las venas: la regla de Sara
    bifurcar = cargar_reglas_de_sara()
    tramos = []
    if bifurcar:
        for vd in D_VENAS:
            tramos += bifurcar(D_NUDO_U, 0.5, vd, D_LARGO, D_ABERTURA, D_GENERACIONES) or []
    print(f"· Regla de Sara: {len(tramos)} tramos")
    for (u0, v0, u1, v1) in tramos:
        # cada tramo se dibuja con una curva suave (sale con la dirección de su madre)
        pts = [P(u0 + (u1 - u0) * k / 20, v0 + (v1 - v0) * suave(k / 20)) for k in range(21)]
        w = max(1.0, 2.6 - 2.4 * u0)   # más gruesas cerca de la base
        est.append((pts, w, max(0.9, w * 0.7)))
    return contorno, est, []


# ------------------------------------------------------------------ mallas
def cinta(bm, pts, w0, w1, z0, z1):
    """Una vena como cinta plana con grosor: ancho de w0 a w1 a lo largo de la curva."""
    if len(pts) < 2:
        return
    L = longitud_arco(pts) or 1.0
    s, izq, der = 0.0, [], []
    for i, p in enumerate(pts):
        if i: s += (pts[i] - pts[i - 1]).length
        a = pts[max(i - 1, 0)]; b = pts[min(i + 1, len(pts) - 1)]
        t = (b - a).normalized()
        n = Vector((-t.y, t.x)) * ((w0 + (w1 - w0) * s / L) / 2)
        izq.append(p + n); der.append(p - n)
    def v(q, z): return bm.verts.new((q.x * MM, q.y * MM, z * MM))
    ab = [(v(a, z0), v(b, z0), v(a, z1), v(b, z1)) for a, b in zip(izq, der)]
    for (a0, b0, a1, b1), (c0, d0, c1, d1) in zip(ab, ab[1:]):
        bm.faces.new((a1, b1, d1, c1)); bm.faces.new((a0, c0, d0, b0))
        bm.faces.new((a0, a1, c1, c0)); bm.faces.new((b0, d0, d1, b1))
    for (a0, b0, a1, b1), sig in ((ab[0], 1), (ab[-1], -1)):
        bm.faces.new((a0, b0, b1, a1) if sig > 0 else (a0, a1, b1, b0))
    # uniones redondas en las puntas (para que los cruces no queden con huecos)
    for p, w in ((pts[0], w0), (pts[-1], w1)):
        r = w / 2
        bot = [v(p + Vector((math.cos(a), math.sin(a))) * r, z0) for a in (2 * math.pi * j / 12 for j in range(12))]
        top = [v(p + Vector((math.cos(a), math.sin(a))) * r, z1) for a in (2 * math.pi * j / 12 for j in range(12))]
        bm.faces.new(top); bm.faces.new(list(reversed(bot)))
        for j in range(12):
            bm.faces.new((bot[j], bot[(j + 1) % 12], top[(j + 1) % 12], top[j]))


def objeto(nombre, bm, material, padre, col):
    me = bpy.data.meshes.new(nombre); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(nombre, me); col.objects.link(ob)
    ob.data.materials.append(material); ob.parent = padre
    return ob


def material(nombre, color, alpha=1.0, rough=0.5):
    m = bpy.data.materials.get(nombre) or bpy.data.materials.new(nombre)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = color
    b.inputs["Roughness"].default_value = rough
    b.inputs["Alpha"].default_value = alpha
    m.diffuse_color = (color[0], color[1], color[2], alpha)
    if alpha < 1:
        for attr, val in (("blend_method", "BLEND"), ("surface_render_method", "BLENDED")):
            try: setattr(m, attr, val)
            except Exception: pass
    return m


def construir():
    sc = bpy.context.scene
    col = bpy.data.collections.get("Propuestas_Alas")
    if col:  # rehacer desde cero (solo esta colección)
        for o in list(col.all_objects):
            bpy.data.objects.remove(o, do_unlink=True)
    else:
        col = bpy.data.collections.new("Propuestas_Alas"); sc.collection.children.link(col)

    m_mem = material("Acetato_propuesta", (0.85, 0.93, 1.0, 1.0), alpha=0.25, rough=0.05)
    m_adh = material("Vinilo_negro", (0.02, 0.02, 0.02, 1.0), rough=0.4)
    # capas de abajo (pared) hacia arriba (quien mira): membrana, adhesivo, estructura
    zm0, zm1 = 0.0, GROSOR_MEMBRANA
    za0, za1 = zm1, zm1 + GROSOR_ADHESIVO
    ze0, ze1 = za1, za1 + GROSOR_ESTRUCTURA
    informe = {}

    for clave, v in VERSIONES.items():
        m_est = material(f"PLA_estructura_{clave}", v["color"], rough=0.35)
        base = bpy.data.objects.new(f"Propuesta_{clave}", None)
        base.location = (v["origen"][0], v["origen"][1], 0); base.empty_display_size = 0.01
        col.objects.link(base)
        txt = bpy.data.curves.new(f"Rotulo_{clave}", "FONT"); txt.body = v["nombre"]; txt.size = 0.012
        t = bpy.data.objects.new(f"Rotulo_{clave}", txt); t.parent = base
        t.location = (-0.04, -0.03, 0); col.objects.link(t)

        alas = (("Ant", ALA_ANT, 0.0),) if v.get("solo_anterior") else \
               (("Ant", ALA_ANT, 0.0), ("Post", ALA_POST, SEPARACION_POST))
        for parte, ala, dx in alas:
            hijo = bpy.data.objects.new(f"{clave}_Ala_{parte}", None)
            hijo.parent = base; hijo.location = (dx * MM, 0, 0); hijo.empty_display_size = 0.005
            col.objects.link(hijo)
            gen = venacion_sara if v.get("sara") else venacion_organica if v.get("organica") else venacion
            contorno, est, adh = gen(ala, v)

            bm = bmesh.new()
            for pts, w0, w1 in est: cinta(bm, pts, w0, w1, ze0, ze1)
            objeto(f"{clave}_{parte}_1_Estructura", bm, m_est, hijo, col)

            bm = bmesh.new()
            vb = [bm.verts.new((p.x * MM, p.y * MM, zm0 * MM)) for p in contorno]
            f = bm.faces.new(vb)
            r = bmesh.ops.extrude_face_region(bm, geom=[f])
            bmesh.ops.translate(bm, verts=[e for e in r["geom"] if isinstance(e, bmesh.types.BMVert)],
                                vec=(0, 0, GROSOR_MEMBRANA * MM))
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
            objeto(f"{clave}_{parte}_2_Membrana", bm, m_mem, hijo, col)

            bm = bmesh.new()
            for pts, w0, w1 in adh: cinta(bm, pts, w0, w1, za0, za1)
            objeto(f"{clave}_{parte}_3_Adhesivo", bm, m_adh, hijo, col)

            # la raíz que entra a la esfera es la misma del mecanismo (malla compartida)
            raiz = bpy.data.objects.get(f"Raiz_{parte}")
            if raiz:
                rr = bpy.data.objects.new(f"{clave}_{parte}_1_Raiz", raiz.data)
                rr.parent = hijo; col.objects.link(rr)

            largo_adh = sum(longitud_arco(p) for p, _, _ in adh)
            informe[f"{clave}_{parte}"] = dict(venas_estructura=len(est), venas_adhesivo=len(adh),
                                               metros_corte_adhesivo=round(2 * largo_adh / 1000, 2))
    return informe


if __name__ == "__main__":
    print(construir())
