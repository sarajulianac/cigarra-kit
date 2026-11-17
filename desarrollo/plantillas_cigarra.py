"""
plantillas_cigarra.py — Etapas 1 y 2 de la prueba de forma de la cigarra.

  · Piezas plegadas (8 bandas del abdomen + pronoto): se DESARROLLAN. La superficie está hecha de
    columnas de puntos (cortes transversales); entre cada par de columnas hay una tira de
    cuadriláteros que se parte en triángulos y se coloca en el plano conservando la longitud de cada
    arista ("triangular con compás"). Si la pieza se puede abrir sin deformarse, el error es 0.
  · Piezas planas de cartón (chasis + 3 pares de patas): se PROYECTAN desde arriba.
  · Ranuras: salen de los objetos de corte del modelo, pero con medidas reales (grosor del material
    + holgura), no las del modelo.

Salida: SVG en milímetros reales, hoja carta, en la carpeta 'plantillas_impresion' junto al .blend.

Proyecto Final · Computación Visual Interactiva · Sara Cuadrado
Correr desde la pestaña Scripting de Blender con el archivo del prototipo abierto.
"""
import bpy, bmesh, os, math
from mathutils import Vector

# ============ PARÁMETROS ============
ESCALA         = 0.5
CHASIS         = "H_Chasis"
PLEGADAS       = [f"H_Banda_{i}" for i in range(1, 9)] + ["H_Pronoto"]
PATAS          = ["H_Patas_Ant", "H_Patas_Med", "H_Patas_Post"]
MARCAS         = ["H_corte_centro", "H_corte_ojo_L", "H_corte_ojo_R"]   # encuadernadores, etapa 3
GROSOR_CARTON  = 1.5    # mm
SOLAPA         = 5.0    # mm que se doblan por debajo del chasis
HOLGURA        = 0.6    # mm extra en el largo de cada ranura
ANCHO_RANURA   = 1.0    # mm (cartulina 200 g + holgura)
ALIVIO         = False  # cortes de alivio en la base de las pestañas (activar para materiales rígidos)
ALIVIO_LARGO   = 1.5    # mm que el corte de alivio entra en la pieza, en la base de cada pestaña
ALIVIO_ANCHO   = 0.8    # mm de ancho del corte de alivio (punta redonda)
HOJA_W, HOJA_H = 215.9, 279.4
MARGEN, SEP    = 12, 8
TOL            = 1e-4
# ====================================


# ---------- Escrita por Sara ----------
def longitud_arco(puntos):
    total = 0
    for i in range(len(puntos) - 1):
        a = puntos[i]
        b = puntos[i + 1]
        d = (b - a).length
        total = total + d
    return total
# --------------------------------------


def mm(valor_m):
    """Metros del modelo -> milímetros reales a la escala de producción."""
    return valor_m * 1000 * ESCALA


def vertices_mundo(nombre):
    o = bpy.data.objects[nombre]
    return [o.matrix_world @ v.co for v in o.data.vertices]


def centro(nombre):
    vs = vertices_mundo(nombre)
    return sum(vs, Vector()) / len(vs)


tope_chasis = max(p.z for p in vertices_mundo(CHASIS))


# =====================================================================
#  1. PIEZAS PLEGADAS: leer columnas y desarrollar
# =====================================================================
def leer_columnas(nombre):
    """Columnas de la pieza (de atrás hacia adelante). Cada columna es la lista de puntos 3D del
    arco, ordenada de pie a pie (sin los puntos de las pestañas). También devuelve qué pares de
    columnas vecinas llevan pestaña."""
    o = bpy.data.objects[nombre]
    bm = bmesh.new(); bm.from_mesh(o.data)
    xs = sorted({round(v.co.x, 4) for v in bm.verts})
    pie_z = min(v.co.z for v in bm.verts if abs(v.co.x - xs[0]) < TOL)     # columna sin pestaña
    corte = (pie_z + min(v.co.z for v in bm.verts)) / 2                     # entre el pie y la punta de la pestaña
    columnas, con_pestana = [], []
    for x in xs:
        col = {v for v in bm.verts if abs(v.co.x - x) < TOL}
        con_pestana.append(any(v.co.z < corte for v in col))
        arco = {v for v in col if v.co.z >= corte}
        vecinos = {v: [e.other_vert(v) for e in v.link_edges if e.other_vert(v) in arco] for v in arco}
        inicio = min((v for v in arco if len(vecinos[v]) == 1), key=lambda v: v.co.y)
        camino, anterior = [inicio], None
        while True:
            sig = [w for w in vecinos[camino[-1]] if w is not anterior]
            if not sig: break
            anterior = camino[-1]; camino.append(sig[0])
        columnas.append([o.matrix_world @ v.co for v in camino])
    bm.free()
    pares, k = [], 0                       # cada pestaña ocupa dos columnas seguidas (sin repetir)
    while k < len(xs) - 1:
        if con_pestana[k] and con_pestana[k + 1]:
            pares.append(k); k += 2
        else:
            k += 1
    return columnas, pares, (o.matrix_world @ Vector((0, 0, pie_z))).z


def tercer_punto(A, B, ra, rb, lejos_de):
    """Punto P del plano con |PA| = ra y |PB| = rb (intersección de dos circunferencias).
    De las dos soluciones, la que queda al otro lado de la recta AB respecto a 'lejos_de',
    para que la tira avance y no se doble sobre sí misma."""
    d = (B - A).length
    a = (ra*ra - rb*rb + d*d) / (2*d)
    h = math.sqrt(max(ra*ra - a*a, 0.0))
    u = (B - A) / d
    n = Vector((-u.y, u.x))
    lado_ref = n.dot(lejos_de - A)
    return A + u*a - n*h if lado_ref > 0 else A + u*a + n*h


def desarrollar(columnas):
    """Aplana todas las tiras entre columnas vecinas. Devuelve las columnas en 2D y el error máximo
    (diferencia entre las diagonales en 3D y en el plano: 0 = la pieza se abre sin deformarse)."""
    D = lambda P, Q: mm((P - Q).length)
    c0, c1 = columnas[0], columnas[1]
    plano = [[Vector((0, 0))], [Vector((D(c1[0], c0[0]), 0))]]
    abajo = Vector((0, -1e6))                      # la primera tira crece hacia +Y
    for i in range(len(c0) - 1):
        plano[1].append(tercer_punto(plano[0][i], plano[1][i], D(c1[i+1], c0[i]), D(c1[i+1], c1[i]),
                                     plano[1][i - 1] if i else abajo))
        plano[0].append(tercer_punto(plano[0][i], plano[1][i+1], D(c0[i+1], c0[i]), D(c0[i+1], c1[i+1]),
                                     plano[1][i]))
    for k in range(1, len(columnas) - 1):
        L3, R3, L = columnas[k], columnas[k + 1], plano[k]
        R = [tercer_punto(L[0], L[1], D(R3[0], L3[0]), D(R3[0], L3[1]), plano[k - 1][0])]
        for i in range(len(L3) - 1):
            R.append(tercer_punto(L[i+1], R[i], D(R3[i+1], L3[i+1]), D(R3[i+1], R3[i]), L[i]))
        plano.append(R)
    error = 0.0
    for k in range(len(columnas) - 1):
        L3, R3, L, R = columnas[k], columnas[k+1], plano[k], plano[k+1]
        for i in range(len(L3) - 1):
            error = max(error, abs((L[i] - R[i+1]).length - D(L3[i], R3[i+1])),
                               abs((L[i+1] - R[i]).length - D(L3[i+1], R3[i])))
    return plano, error


def normal_afuera(P, Q, interior):
    u = (Q - P).normalized()
    n = Vector((-u.y, u.x))
    return -n if n.dot(interior - P) > 0 else n


def pieza_plegada(nombre):
    columnas, pares, pie_z = leer_columnas(nombre)
    plano, error = desarrollar(columnas)
    T = mm(pie_z - tope_chasis) + GROSOR_CARTON + SOLAPA
    n = len(plano[0]) - 1
    contorno, dobleces, pestanas = [], [], []

    def alivio(P, e, nrm):
        """Corte de alivio en la esquina interna de la pestaña: una ranurita de punta redonda que
        prolonga el lado de la pestaña hacia dentro de la pieza. Quita la esquina viva de 90°,
        que es donde empieza el rasgado. 'e' apunta desde la pestaña hacia afuera (sobre el pie)."""
        A = P + e*ALIVIO_ANCHO
        M = (A + P) / 2 - nrm*ALIVIO_LARGO
        r = ALIVIO_ANCHO / 2
        arco = [M + e*r*math.cos(t) - nrm*r*math.sin(t)
                for t in (j * math.pi / 8 for j in range(9))]     # de A' a P' rodeando por dentro
        return A, arco                                             # arco va de A-nrm*L a P-nrm*L

    def borde_extremo(i, vecino, orden, paso):
        """Recorre el extremo i (un pie) de columna en columna, metiendo las pestañas."""
        out, saltar = [], False
        for k in orden:
            k2 = k + paso
            P, Q = plano[k][i], plano[k2][i]
            par = min(k, k2)
            if par not in pares:
                if not saltar:                       # este punto ya entró como 'Q' de la pestaña anterior
                    out.append(P)
                saltar = False
                continue
            assert not saltar, "dos pestañas seguidas sin columna libre entre ellas"
            saltar = True
            nrm = normal_afuera(P, Q, (plano[k][vecino] + plano[k2][vecino]) / 2)
            e = (Q - P).normalized()                 # de P hacia Q, a lo ancho de la pestaña
            if ALIVIO:
                A, arco = alivio(P, -e, nrm)         # alivio del lado de P (afuera = -e)
                out += [A] + arco + [P, P + nrm*T, Q + nrm*T, Q]
                B, arco = alivio(Q, e, nrm)          # alivio del lado de Q (afuera = +e)
                out += arco[::-1] + [B]
            else:
                out += [P, P + nrm*T, Q + nrm*T, Q]
            dobleces.append((P + nrm*(T - SOLAPA), Q + nrm*(T - SOLAPA)))
        return out

    K = len(plano)
    assert 0 not in pares and K - 2 not in pares, "las pestañas deben estar en columnas interiores"
    contorno += plano[0][:]                                     # borde de atrás, de pie a pie
    contorno += borde_extremo(n, n - 1, range(0, K - 1), +1)    # pie final, cruzando columnas
    contorno += plano[K - 1][::-1]                              # borde de adelante, de vuelta
    contorno += borde_extremo(0, 1, range(K - 1, 0, -1), -1)    # pie inicial
    # Pestañas en 3D: los dos puntos del pie entre los que cuelga cada pestaña. La ranura del chasis
    # se dibuja sobre ese segmento (visto desde arriba): mismo centro, mismo largo y MISMO ÁNGULO.
    # Ojo: en las bandas de la cola el pie corre en diagonal, así que el ancho real de la pestaña
    # NO es solo su diferencia en X.
    for k in pares:
        for i in (0, n):
            pestanas.append((columnas[k][i], columnas[k + 1][i]))
    return {"nombre": nombre, "contorno": contorno, "dobleces": dobleces, "pestanas": pestanas,
            "error": error, "T": T,
            "arcos": [mm(longitud_arco(columnas[0])), mm(longitud_arco(columnas[-1]))]}


def acomodar(pieza):
    """Gira la pieza para que su eje largo quede vertical y la lleva a la esquina (0, 0)."""
    pts = pieza["contorno"]
    eje = max(((p, q) for p in pts[::3] for q in pts[::3]), key=lambda pq: (pq[0] - pq[1]).length)
    v = eje[1] - eje[0]
    ang = math.pi/2 - math.atan2(v.y, v.x)
    c, s = math.cos(ang), math.sin(ang)
    rot = lambda p: Vector((c*p.x - s*p.y, s*p.x + c*p.y))
    pts = [rot(p) for p in pts]
    dob = [(rot(a), rot(b)) for a, b in pieza["dobleces"]]
    off = Vector((min(p.x for p in pts), min(p.y for p in pts)))
    pieza["plano"] = [p - off for p in pts]
    pieza["plano_dob"] = [(a - off, b - off) for a, b in dob]
    pieza["w"] = max(p.x for p in pieza["plano"]); pieza["h"] = max(p.y for p in pieza["plano"])
    return pieza


# =====================================================================
#  2. PIEZAS PLANAS: contorno visto desde arriba
# =====================================================================
def contornos_superiores(nombre):
    """Contornos de la cara de arriba de la malla base (sin sus booleanos de ranuras).
    Las patas están modeladas como varias piezas que se traslapan (barra + segmentos), así que
    primero se UNEN con un booleano 'self union' para obtener una sola silueta recortable."""
    o = bpy.data.objects[nombre]
    tmp = bpy.data.objects.new("_tmp_union", o.data.copy())
    tmp.matrix_world = o.matrix_world
    bpy.context.scene.collection.objects.link(tmp)
    lejos = bpy.data.objects.new("_tmp_lejos", bpy.data.meshes.new("_tmp_lejos"))
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=0.01); bm.to_mesh(lejos.data); bm.free()
    lejos.location = (100, 100, 100)
    bpy.context.scene.collection.objects.link(lejos)
    m = tmp.modifiers.new("union", 'BOOLEAN')
    m.operation, m.solver, m.object, m.use_self = 'UNION', 'EXACT', lejos, True
    ev = tmp.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = bpy.data.meshes.new_from_object(ev)
    bm = bmesh.new(); bm.from_mesh(me)
    bm.transform(tmp.matrix_world)
    cerca = [v for v in bm.verts if v.co.x < 50]
    z = max(v.co.z for v in cerca)
    arriba = {f for f in bm.faces if all(abs(v.co.z - z) < 1e-5 for v in f.verts)}
    borde = [e for e in bm.edges if sum(1 for f in e.link_faces if f in arriba) == 1]
    vecinos = {}
    for e in borde:
        a, b = e.verts
        vecinos.setdefault(a, []).append(b); vecinos.setdefault(b, []).append(a)
    restantes, lazos = set(vecinos), []
    while restantes:
        s = restantes.pop(); lazo, anterior = [s], None
        while True:
            sig = [w for w in vecinos[lazo[-1]] if w is not anterior]
            if not sig or sig[0] is s: break
            anterior = lazo[-1]; lazo.append(sig[0]); restantes.discard(sig[0])
        lazos.append([v.co.copy() for v in lazo])
    bm.free()
    for ob in (tmp, lejos): bpy.data.objects.remove(ob, do_unlink=True)
    bpy.data.meshes.remove(me)
    return sorted(lazos, key=len, reverse=True)       # el primero es la silueta exterior


def pestana_cerca(p, pestanas):
    """La pestaña (par de puntos del pie) cuyo centro queda más cerca del punto p, visto desde arriba."""
    return min(pestanas, key=lambda t: ((t[0].xy + t[1].xy) / 2 - p.xy).length)


def ranura_de_pestana(pest, a_hoja):
    """Rectángulo de la ranura en la hoja: a lo largo del pie de la pestaña (con su ángulo real),
    largo = ancho de la pestaña + holgura, ancho = ANCHO_RANURA. a_hoja convierte un punto del
    modelo a milímetros sobre la hoja."""
    P, Q = Vector(a_hoja(pest[0])), Vector(a_hoja(pest[1]))
    u = (Q - P).normalized()
    n = Vector((-u.y, u.x))
    m = (P + Q) / 2
    L = (Q - P).length + HOLGURA
    esquinas = [m + u*s*L/2 + n*t*ANCHO_RANURA/2 for s, t in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    return f'<polygon points="{poly(esquinas)}" {CORTE}/>', m, (Q - P).length


# =====================================================================
#  3. SVG
# =====================================================================
CORTE  = 'fill="none" stroke="#000" stroke-width="0.25"'
DOBLEZ = 'stroke="#d0451b" stroke-width="0.3" stroke-dasharray="2,1.5"'
MARCA  = 'fill="none" stroke="#1b6fd0" stroke-width="0.25"'

def texto(x, y, s, tam=3, rot=None, ancla="start", color="#333"):
    r = f' transform="rotate({rot} {x:.2f} {y:.2f})"' if rot is not None else ""
    return f'<text x="{x:.2f}" y="{y:.2f}" font-family="Helvetica" font-size="{tam}" fill="{color}" text-anchor="{ancla}"{r}>{s}</text>'

def poly(pts):
    return " ".join(f"{p[0]:.2f},{p[1]:.2f}" for p in pts)

def linea(a, b, estilo):
    return f'<line x1="{a[0]:.2f}" y1="{a[1]:.2f}" x2="{b[0]:.2f}" y2="{b[1]:.2f}" {estilo}/>'

def encabezado_y_pie(titulo, nota=""):
    out = [texto(MARGEN, 12, titulo, 4)]
    if nota: out.append(texto(MARGEN, 17, nota, 2.8, color="#666"))
    out += [f'<rect x="{MARGEN}" y="{HOJA_H-25}" width="10" height="10" {CORTE}/>',
            texto(MARGEN + 12, HOJA_H - 17, "1 cm — medir con regla antes de cortar · imprimir al 100 %"),
            linea((140, HOJA_H-20), (148, HOJA_H-20), CORTE) + texto(150, HOJA_H - 19, "cortar"),
            linea((165, HOJA_H-20), (173, HOJA_H-20), DOBLEZ) + texto(175, HOJA_H - 19, "doblar")]
    return out

def marca_encuadernador(cx, cy):
    return (f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="1.5" {MARCA}/>'
            + linea((cx-3, cy), (cx+3, cy), MARCA) + linea((cx, cy-3), (cx, cy+3), MARCA))


hojas = []

# ---------- Hojas de cartulina: piezas plegadas ----------
plegadas = [acomodar(pieza_plegada(n)) for n in PLEGADAS]
todas_pestanas = [t for p in plegadas for t in p["pestanas"]]
alto_util = HOJA_H - 24 - 32
grupos, actual, x = [], [], MARGEN
for p in plegadas:
    if x + p["w"] > HOJA_W - MARGEN:
        grupos.append(actual); actual, x = [], MARGEN
    actual.append((p, x)); x += p["w"] + SEP
grupos.append(actual)

for g in grupos:
    svg = []
    for p, x in g:
        y = 24 + (alto_util - p["h"]) / 2
        mov = lambda q: (q.x + x, q.y + y)
        svg.append(f'<polygon points="{poly([mov(q) for q in p["plano"]])}" {CORTE}/>')
        svg += [linea(mov(a), mov(b), DOBLEZ) for a, b in p["plano_dob"]]
        etiqueta = p["nombre"].replace("H_", "").replace("_", " ").upper()
        cx = sum(q.x for q in p["plano"]) / len(p["plano"]) + x
        svg.append(texto(cx, y + p["h"]/2, etiqueta, 3, rot=-90, ancla="middle"))
    nombres = ", ".join(p["nombre"].replace("H_", "").replace("_", " ") for p, _ in g)
    hojas.append(svg + encabezado_y_pie(f"Piezas plegadas · escala {ESCALA} · cartulina 200 g", nombres))

# ---------- Hoja del chasis (papel, guía para cortar cartón) ----------
lazos = contornos_superiores(CHASIS)
borde = lazos[0]
xmin, xmax = min(p.x for p in borde), max(p.x for p in borde)
ymin, ymax = min(p.y for p in borde), max(p.y for p in borde)
ox, oy = (HOJA_W - mm(ymax - ymin)) / 2, (HOJA_H - mm(xmax - xmin)) / 2 + 4
a_hoja = lambda p: (ox + mm(p.y - ymin), oy + mm(xmax - p.x))           # cabeza arriba
svg = [f'<polygon points="{poly([a_hoja(p) for p in l])}" {CORTE}/>' for l in lazos]
cortes = [o.name for o in bpy.data.collections["H_Cortes_Chasis"].objects]
reporte = []
for nombre in cortes:
    c = centro(nombre); px, py = a_hoja(c)
    if nombre in MARCAS:
        svg.append(marca_encuadernador(px, py))
    else:
        forma, _, ancho = ranura_de_pestana(pestana_cerca(c, todas_pestanas), a_hoja)
        svg.append(forma)
        reporte.append((nombre, ancho))
        if nombre.startswith("H_corte_banda") and nombre.endswith("_0"):
            svg.append(texto(HOJA_W/2, py + 1, nombre.split("banda")[1][0], 2.5, ancla="middle"))
        if nombre == "H_corte_pronoto_0":
            svg.append(texto(HOJA_W/2, py + 1, "P", 2.5, ancla="middle"))
svg.append(texto(HOJA_W/2, oy - 3, "↑ cabeza", 3, ancla="middle"))
hojas.append(svg + encabezado_y_pie(f"Chasis · escala {ESCALA} · cartón 1.5 mm",
             "1–8 ranuras de las bandas · P ranuras del pronoto · azul: encuadernadores (perforar en la etapa 3)"))

# ---------- Hoja de patas (papel, guía para cortar cartón) ----------
# El largo de las patas (Y del modelo) va vertical; la cabeza (X+) hacia la derecha.
svg, x = [], MARGEN + 4
for nombre in PATAS:
    lazos = contornos_superiores(nombre)
    borde = lazos[0]
    pxmin, pxmax = min(p.x for p in borde), max(p.x for p in borde)
    pymin, pymax = min(p.y for p in borde), max(p.y for p in borde)
    y0 = 24 + (alto_util - mm(pymax - pymin)) / 2
    mov = lambda p, x=x, y0=y0, pxmin=pxmin, pymax=pymax: (x + mm(p.x - pxmin), y0 + mm(pymax - p.y))
    svg += [f'<polygon points="{poly([mov(p) for p in l])}" {CORTE}/>' for l in lazos]
    for m in bpy.data.objects[nombre].modifiers:
        if m.type == 'BOOLEAN' and m.collection:
            for o in m.collection.objects:
                forma, _, ancho = ranura_de_pestana(pestana_cerca(centro(o.name), todas_pestanas), mov)
                svg.append(forma)
                reporte.append((nombre + "/" + o.name, ancho))
    svg.append(texto(x + mm(pxmax - pxmin)/2, y0 - 3, nombre.replace("H_", "").replace("_", " "), 3, ancla="middle"))
    x += mm(pxmax - pxmin) + SEP
hojas.append(svg + encabezado_y_pie(f"Patas · escala {ESCALA} · cartón 1.5 mm",
             "Cabeza hacia la derecha → · Ranuras de las patas anteriores: para las pestañas traseras del pronoto"))


# =====================================================================
#  4. Guardar
# =====================================================================
carpeta = os.path.join(os.path.dirname(bpy.data.filepath), "plantillas_impresion")
os.makedirs(carpeta, exist_ok=True)
for f in os.listdir(carpeta):
    if f.endswith(".svg"): os.remove(os.path.join(carpeta, f))
nombres = []
for i, cuerpo in enumerate(hojas):
    tipo = "cartulina" if i < len(grupos) else "papel_guia_carton"
    nombre = f"hoja{i+1}_{tipo}.svg"; nombres.append(nombre)
    with open(os.path.join(carpeta, nombre), "w", encoding="utf-8") as fh:
        fh.write("\n".join([f'<svg xmlns="http://www.w3.org/2000/svg" width="{HOJA_W}mm" height="{HOJA_H}mm" viewBox="0 0 {HOJA_W} {HOJA_H}">']
                           + cuerpo + ['</svg>']))

for p in plegadas:
    print(f'{p["nombre"]:12s} arcos {p["arcos"][0]:6.1f} / {p["arcos"][1]:6.1f} mm · pestañas {len(p["pestanas"])} '
          f'de {p["T"]:.1f} mm · caja {p["w"]:.0f}x{p["h"]:.0f} · error {p["error"]:.2f} mm')
for nombre, ancho in reporte:
    print(f"ranura {nombre:38s} pestaña {ancho:5.2f} mm -> ranura {ancho + HOLGURA:5.2f} mm")
print("Hojas:", nombres)
print("Guardado en:", carpeta)
