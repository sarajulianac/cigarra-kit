# =============================================================================
# cigarra_hibrida.py - Cigarra version hibrida, armable SIN PEGANTE
# Aplica el documento "Reglas de modelado - Cigarra":
#  - una tecnica por pieza (propiedad 'tecnica'), con 'union', 'apoyo',
#    'material' y 'orden' (orden de armado para el manual)
#  - chasis de carton = silueta dorsal + margen, con ranuras (booleanas / CSG)
#  - capas (cabeza, mesonoto) = volumenes cerrados
#  - plegados (pronoto, 8 bandas del abdomen) = superficies abiertas
#    DESARROLLABLES (conos), con pestanas y linea de grafado marcada (seam)
#  - patas = perfiles planos de carton, por pares, atrapados bajo el cuerpo
#  - alas = membrana + venacion planas, con pestana atrapada en el mesonoto
#  - ojos y remache central = componentes (encuadernadores con perla)
# =============================================================================
import bpy, bmesh, math
from mathutils import Vector, Matrix

RAIZ, COLECCION, PREFIJO = "Cigarra_H", "Cigarra_Hibrida", "H_"
UBICACION = (-1.6, -2.3, 1.0)
TAMANO_REAL_CM, LADO_MODELO = 15.0, 1.178
MM = LADO_MODELO / (TAMANO_REAL_CM * 10)      # unidades de Blender por mm real
CARTON, CARTULINA, HOLGURA = 1.5 * MM, 0.4 * MM, 0.3 * MM
ANCHO_VENA = 0.8 * MM          # venas finas (minimo laser)
ANCHO_VENA_P = 1.2 * MM        # costa y venas principales
D_OJO, D_REMACHE = 8 * MM, 4 * MM
Z_CHASIS = 0.075            # cara superior del chasis
Z_ALAS = 0.150              # plano de las alas (entre capas del mesonoto)
Z_FONDO = Z_CHASIS - CARTON - 0.008   # hasta donde bajan pestanas y patitas

CABEZA = [(0.245, 0.040, 0.022, 0.118), (0.238, 0.070, 0.034, 0.120), (0.225, 0.085, 0.040, 0.122),
          (0.205, 0.088, 0.042, 0.123), (0.190, 0.084, 0.040, 0.122)]
MESONOTO = [(0.112, 0.112, 0.062, 0.130), (0.085, 0.118, 0.072, 0.132), (0.055, 0.115, 0.075, 0.132),
            (0.025, 0.104, 0.070, 0.128), (0.000, 0.085, 0.058, 0.122), (-0.015, 0.064, 0.046, 0.118)]
OJO = (0.212, 0.072, 0.142)             # base de la perla; patitas DENTRO de la cabeza (ancho 0.088)
REMACHE_C = (0.108, 0.0, 0.188)    # borde delantero del mesonoto, OCULTO bajo el pronoto
ABD_X0, ABD_X1, N_BANDAS = 0.0, -0.205, 8
PRON_X = [0.198, 0.178, 0.162, 0.138, 0.122, 0.104]
def pron_w(x): return 0.085 + (0.198 - x) / (0.198 - 0.104) * (0.132 - 0.085)
def pron_top(x): return 0.172 + (0.198 - x) / (0.198 - 0.104) * (0.200 - 0.172)
def abd_ry(t): return 0.098 * max(0.0, 1 - t ** 3) ** 0.55 + 0.006
def abd_top(t): return (0.112 - 0.025 * t) + 0.85 * abd_ry(t)

ALA_ANT = [(0, 0.02), (0.08, 0.06), (0.25, 0.085), (0.5, 0.10), (0.75, 0.105), (0.9, 0.09), (0.98, 0.05),
           (1.0, 0.0), (0.97, -0.06), (0.88, -0.10), (0.7, -0.12), (0.45, -0.115), (0.25, -0.09), (0.1, -0.05), (0.02, -0.02)]
ALA_POST = [(0, 0.02), (0.15, 0.07), (0.4, 0.10), (0.7, 0.10), (0.9, 0.07), (1.0, 0.0), (0.95, -0.08),
            (0.75, -0.14), (0.45, -0.15), (0.2, -0.10), (0.05, -0.04)]
# Venacion segun la foto de referencia (ala de cigarra real). Coordenadas (u, v):
# u = a lo largo del ala 0..1, v = cuerda (v > 0 = costa / borde de ataque).
#  - costa gruesa + celda costal RELLENA hasta el "nodo"
#  - celda basal larga; venas longitudinales curvas (R, M, Cu) con celdas ulnares
#  - linea transversal apical curva + vena ambiente METIDA hacia adentro del borde
#    (franja de membrana limpia) -> celdas apicales alargadas
VENAS_ANT = dict(
    nodo=0.62, ambiente_hasta=0.40, inset=0.014, apicales=7,
    R=[(0.0, 0.004), (0.20, 0.062), (0.40, 0.082), (0.62, 0.094)],               # banda costal angosta
    principales=[[(0.62, 0.094), (0.66, 0.088), (0.685, 0.080)],                 # R distal
                 [(0.0, 0.0), (0.15, 0.020), (0.30, 0.030)],                      # tronco M
                 [(0.0, -0.008), (0.15, -0.028), (0.30, -0.036)],                 # tronco Cu
                 [(0.30, 0.030), (0.45, 0.045), (0.58, 0.044), (0.672, 0.036)],  # M1+2
                 [(0.30, -0.003), (0.45, -0.010), (0.58, -0.016), (0.655, -0.020)],
                 [(0.30, -0.036), (0.45, -0.055), (0.56, -0.066), (0.630, -0.070)]],
    finas=[[(0.30, 0.030), (0.30, -0.036)],                                       # cierre de la celda basal
           [(0.52, 0.044), (0.52, -0.014)],                                       # una sola transversal media
           [(0.0, -0.014), (0.16, -0.058), (0.32, -0.092), (0.42, -0.108)]],     # sutura del clavo
    al_ambiente=[[(0.30, -0.036), (0.42, -0.074), (0.50, -0.094), (0.56, -0.106)]],
    arco=[(0.71, 0.104), (0.685, 0.080), (0.672, 0.036), (0.655, -0.020), (0.630, -0.070), (0.590, -0.100), (0.540, -0.116)])
VENAS_POST = dict(
    nodo=0.55, ambiente_hasta=0.30, inset=0.012, apicales=5,
    R=[(0.0, 0.004), (0.25, 0.060), (0.55, 0.085)],
    principales=[[(0.55, 0.085), (0.62, 0.080), (0.68, 0.076)],
                 [(0.0, 0.0), (0.30, 0.010), (0.50, 0.002), (0.69, 0.000)],
                 [(0.0, -0.010), (0.30, -0.060), (0.50, -0.095), (0.64, -0.112)]],
    finas=[[(0.40, 0.072), (0.40, 0.006)], [(0.42, 0.005), (0.42, -0.078)]],
    al_ambiente=[[(0.0, -0.020), (0.22, -0.100), (0.36, -0.140)]],
    arco=[(0.72, 0.098), (0.68, 0.076), (0.69, 0.000), (0.64, -0.112), (0.58, -0.138)])
ALAS = {"Ant": (ALA_ANT, VENAS_ANT, 0.55, 1.15, (0.075, 0.085, Z_ALAS), 24),
        "Post": (ALA_POST, VENAS_POST, 0.32, 1.30, (0.040, 0.080, Z_ALAS - 0.004), 56)}
# patas por pares: barra central (x0, x1, medio ancho y) + polilinea de la pata L + anchos de segmento
PATAS = {
    "Ant":  ((0.120, 0.160, 0.130), [(0.140, 0.120), (0.180, 0.160), (0.225, 0.185), (0.250, 0.195)], (0.034, 0.020, 0.0165)),
    "Med":  ((0.060, 0.090, 0.060), [(0.075, 0.055), (0.090, 0.140), (0.115, 0.185), (0.130, 0.205)], (0.024, 0.019, 0.0165)),
    "Post": ((-0.005, 0.025, 0.065), [(0.010, 0.060), (-0.020, 0.140), (-0.065, 0.185), (-0.085, 0.205)], (0.026, 0.019, 0.0165)),
}

# ------------------------------------------------------------------ utilidades
def material(n, rgb, rough=0.5, alfa=1.0):
    m = bpy.data.materials.get(n) or bpy.data.materials.new(n); m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (*rgb, 1); b.inputs["Roughness"].default_value = rough
    b.inputs["Alpha"].default_value = alfa; m.diffuse_color = (*rgb, alfa)
    if alfa < 1: m.surface_render_method = 'BLENDED'
    return m

def material_degradado(n):
    m = bpy.data.materials.get(n) or bpy.data.materials.new(n); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes.get("Principled BSDF")
    attr = nt.nodes.get("degradado") or nt.nodes.new("ShaderNodeVertexColor"); attr.name = "degradado"; attr.layer_name = "degradado"
    nt.links.new(attr.outputs["Color"], b.inputs["Base Color"]); nt.links.new(attr.outputs["Alpha"], b.inputs["Alpha"])
    b.inputs["Roughness"].default_value = 0.2; m.surface_render_method = 'BLENDED'; m.diffuse_color = (0.6, 0.9, 0.6, 0.4)
    return m

def objeto(nombre, bm, mat, props, suave=False, subdiv=0):
    if props.get("tecnica") in ("membrana", "celosia"):
        # laminas planas: todas las normales hacia +Z (cara visible hacia la pared opuesta)
        bm.normal_update()
        for f in bm.faces:
            if f.normal.z < 0: f.normal_flip()
    else:
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(PREFIJO + nombre); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = suave
    ob = bpy.data.objects.new(PREFIJO + nombre, me); COL.objects.link(ob); ob.parent = RAIZ_OB
    ob.data.materials.append(mat)
    for k, v in props.items(): ob[k] = v
    if subdiv: ob.modifiers.new("suavizado", 'SUBSURF').levels = subdiv
    return ob

def ranuras(ob, col_cortes):
    m = ob.modifiers.new("ranuras", 'BOOLEAN'); m.operation = 'DIFFERENCE'
    m.operand_type = 'COLLECTION'; m.collection = col_cortes
    try: m.solver = 'EXACT'
    except Exception: pass

def cortador(nombre, c, dims, cols):
    me = bpy.data.meshes.new(PREFIJO + nombre); bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation(c) @ Matrix.Diagonal((*dims, 1)))
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(PREFIJO + nombre, me); ob.parent = RAIZ_OB
    for c_ in cols: c_.objects.link(ob)
    ob.display_type = 'WIRE'
    return ob

def caja(bm, c, dims):
    bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation(c) @ Matrix.Diagonal((*dims, 1)))

def losa(bm, poli, z0, z1):
    # prisma cerrado (manifold) a partir de un poligono 2D en sentido antihorario
    b = [bm.verts.new((x, y, z0)) for x, y in poli]; t = [bm.verts.new((x, y, z1)) for x, y in poli]
    bm.faces.new(list(reversed(b))); bm.faces.new(t)
    n = len(poli)
    for i in range(n): bm.faces.new((b[i], b[(i + 1) % n], t[(i + 1) % n], t[i]))

def estadio(p0, p1, w0, w1, n=8):
    p0, p1 = Vector(p0), Vector(p1); d = (p1 - p0).normalized(); a0 = math.atan2(d.x, -d.y)
    pts = [p0 + w0 / 2 * Vector((math.cos(a0 + math.pi * k / n), math.sin(a0 + math.pi * k / n))) for k in range(n + 1)]
    pts += [p1 + w1 / 2 * Vector((math.cos(a0 + math.pi + math.pi * k / n), math.sin(a0 + math.pi + math.pi * k / n))) for k in range(n + 1)]
    return [(p.x, p.y) for p in pts]

def loft(est, n=28, apl=0.65):
    bm = bmesh.new(); A = []
    for (x, ry, rz, zc) in est:
        A.append([bm.verts.new((x, ry * math.cos(2*math.pi*k/n), zc + rz * math.sin(2*math.pi*k/n) * (1 if math.sin(2*math.pi*k/n) > 0 else apl))) for k in range(n)])
    for P, Q in zip(A[:-1], A[1:]):
        for k in range(n): bm.faces.new((P[k], P[(k+1) % n], Q[(k+1) % n], Q[k]))
    for R, e in ((A[0], est[0]), (A[-1], est[-1])):
        c = bm.verts.new((e[0], 0, e[3]))
        for k in range(n): bm.faces.new((R[k], R[(k+1) % n], c))
    return bm

def cupula(bm, c, r, n=24, m=8):
    c = Vector(c); anillos = []
    for k in range(m):
        lat = math.pi / 2 * k / m
        anillos.append([bm.verts.new(c + Vector((r*math.cos(lat)*math.cos(2*math.pi*i/n), r*math.cos(lat)*math.sin(2*math.pi*i/n), r*math.sin(lat)))) for i in range(n)])
    for P, Q in zip(anillos[:-1], anillos[1:]):
        for i in range(n): bm.faces.new((P[i], P[(i+1) % n], Q[(i+1) % n], Q[i]))
    cima = bm.verts.new(c + Vector((0, 0, r))); base = bm.verts.new(c)
    for i in range(n):
        bm.faces.new((anillos[-1][i], anillos[-1][(i+1) % n], cima)); bm.faces.new((anillos[0][(i+1) % n], anillos[0][i], base))

def remache(bm, c, r):
    # cabeza de perla + dos patitas que bajan y se abren bajo el chasis
    cupula(bm, c, r)
    x, y, z = c; alto = z - Z_FONDO
    for s in (-1, 1):
        caja(bm, (x, y + s * 0.0025, Z_FONDO + alto / 2), (2 * MM, 0.003, alto))
        caja(bm, (x + s * 0.015, y + s * 0.0025, Z_FONDO + 0.0015), (0.03, 2 * MM, 0.003))

def chaikin(pts, it=3):
    for _ in range(it):
        q = []
        for i in range(len(pts)):
            a, b = Vector(pts[i]), Vector(pts[(i + 1) % len(pts)]); q += [a * 0.75 + b * 0.25, a * 0.25 + b * 0.75]
        pts = q
    return pts

def cinta(bm, pts, ancho, z, mat_idx=0):
    pts = [Vector((p[0], p[1], z)) for p in pts]; L, R = [], []
    for i, p in enumerate(pts):
        a, b = pts[max(i-1, 0)], pts[min(i+1, len(pts)-1)]; t = (b - a).normalized(); n = Vector((-t.y, t.x, 0)) * (ancho / 2)
        L.append(bm.verts.new(p + n)); R.append(bm.verts.new(p - n))
    for i in range(len(pts) - 1): bm.faces.new((L[i], L[i+1], R[i+1], R[i])).material_index = mat_idx

def pestana_ala(bm, lado, z):
    q = [(-0.012, 0.004), (0.012, 0.004), (0.012, -0.06), (-0.012, -0.06)]
    v = [bm.verts.new((x, lado * y, z)) for x, y in q]
    bm.faces.new(v if lado < 0 else list(reversed(v)))

def membrana(cont, largo, cuerda, lado):
    # Membrana subdividida para que el degradado tenga resolucion. Color: verde en
    # la base y la costa, casi transparente hacia la punta (como la foto).
    pts = chaikin([(v * largo * cuerda, u * largo) for (u, v) in cont]); bm = bmesh.new()
    vs = [bm.verts.new((p.x, lado * p.y, 0.0)) for p in pts]
    bm.faces.new(vs if lado > 0 else list(reversed(vs)))
    bmesh.ops.triangulate(bm, faces=bm.faces)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=3, use_grid_fill=True)
    pestana_ala(bm, lado, 0.0)
    capa = bm.loops.layers.float_color.new("degradado")
    base, punta, borde_c = (0.30, 0.85, 0.40, 0.70), (0.55, 0.90, 0.85, 0.22), (0.30, 0.85, 0.35, 0.85)
    for f in bm.faces:
        for l in f.loops:
            u = min(1.0, max(0.0, abs(l.vert.co.y) / largo)); vx = l.vert.co.x / (largo * cuerda * 0.105)
            k = min(1.0, max(0.0, 0.8 * (1 - u) ** 1.6 + 0.35 * max(0.0, vx) * (1 - 0.5 * u)))
            col = tuple(punta[c] + (base[c] - punta[c]) * k for c in range(4))
            l[capa] = borde_c if l.vert.is_boundary and l.vert.co.z == 0.0 and abs(l.vert.co.y) > 0.01 else col
    return bm

def chaikin_abierto(pts, it=3):
    pts = [Vector(p) for p in pts]
    for _ in range(it):
        q = [pts[0]]
        for a, b in zip(pts[:-1], pts[1:]): q += [a * 0.75 + b * 0.25, a * 0.25 + b * 0.75]
        pts = q + [pts[-1]]
    return pts

IMPRESA = 0.3 * MM            # venas impresas sobre la membrana (opcion C)

def venacion(cont, V, largo, cuerda, lado, registro=None):
    # Opcion C: costa, R, troncos, venas principales, ambiente y clavo = CORTADAS (celosia);
    # arco apical, celdas apicales y transversales medias = IMPRESAS sobre la membrana.
    # Si se pasa 'registro', solo se anotan las lineas (u, v) para crear el trazado editable.
    def xy(p): return (p[1] * largo * cuerda, lado * p[0] * largo)
    borde = chaikin(list(cont)); n = len(borde); itip = max(range(n), key=lambda i: borde[i].x)
    def normal_in(i):
        tg = borde[(i + 1) % n] - borde[i - 1]; return Vector((tg.y, -tg.x)).normalized()
    inset = [borde[i] + V["inset"] * normal_in(i) for i in range(n)]
    i_ini = next(i for i in range(itip + 1) if borde[i].x >= V["nodo"])
    i_fin = max(i for i in range(itip, n) if borde[i].x >= V["ambiente_hasta"])
    ambiente = inset[i_ini:i_fin + 1]
    costa = [Vector((0.0, 0.004))] + [borde[i] + 0.004 * normal_in(i) for i in range(1, i_ini + 1)]
    def cerca(p, linea): return min(linea, key=lambda q: (q - Vector(p)).length)
    lineas = []                                   # (nombre, puntos uv, clase)
    lineas.append(("Costa", costa, "corte")); lineas.append(("R", [Vector(p) for p in V["R"]], "corte"))
    lineas.append(("Ambiente", ambiente, "corte"))
    for k, v_ in enumerate(V["principales"]): lineas.append((f"Principal_{k+1}", [Vector(p) for p in v_], "corte"))
    for k, v_ in enumerate(V["al_ambiente"]): lineas.append((f"Al_ambiente_{k+1}", [Vector(p) for p in v_[:-1]] + [cerca(v_[-1], ambiente)], "corte"))
    for k, v_ in enumerate(V["finas"]):
        clase = "corte" if (k == 0 or k == len(V["finas"]) - 1) else "impresa"     # cierre basal y clavo se cortan
        lineas.append((f"Fina_{k+1}", [Vector(p) for p in v_], clase))
    arco = [cerca(V["arco"][0], ambiente)] + [Vector(p) for p in V["arco"][1:-1]] + [cerca(V["arco"][-1], ambiente)]
    lineas.append(("Arco", arco, "impresa"))
    arco_s = chaikin_abierto(arco); a0 = ambiente.index(arco[0]); a1 = ambiente.index(arco[-1]); kk = V["apicales"]
    for i in range(1, kk + 1):
        S = arco_s[round(i / (kk + 1) * (len(arco_s) - 1))]; E = ambiente[round(a0 + (a1 - a0) * i / (kk + 1))]
        lineas.append((f"Apical_{i}", [S, (S + E) / 2 + 0.006 * (E - S).orthogonal().normalized(), E], "impresa"))
    if registro is not None:
        registro.extend(lineas); return None
    return piezas_desde_lineas([(nm, [xy(p) for p in pts], cl) for nm, pts, cl in lineas], lado)

def piezas_desde_lineas(lineas_xy, lado):
    # lineas en coordenadas locales del ala (x = cuerda, y = envergadura). Devuelve
    # (bm celosia cortada, bm impresion). Material 0 verde, 1 costa, 2 distal.
    corte, impresa = bmesh.new(), bmesh.new()
    largo_y = max(abs(p[1]) for _, pts, _ in lineas_xy for p in pts) or 1.0
    def mat(p): return 0 if abs(p[1]) / largo_y < 0.45 else 2
    def ancho(nm, cl):
        if cl == "impresa": return IMPRESA
        return 1.6 * MM if nm == "Costa" else (ANCHO_VENA if nm.startswith(("Ambiente", "Fina", "Al_ambiente")) else ANCHO_VENA_P)
    costa = R = None
    for nm, pts, cl in lineas_xy:
        bm = corte if cl == "corte" else impresa; z = 0.0012 if cl == "impresa" else (0.0030 if nm in ("Costa", "R") else 0.0026)
        w = ancho(nm, cl); P = chaikin_abierto([Vector(p) for p in pts])
        for a, b in zip(P[:-1], P[1:]):
            cinta(bm, [a, b], w, z, 1 if nm in ("Costa", "R") else mat((a + b) / 2))
        for p in P[1:-1]:
            bmesh.ops.create_circle(bm, cap_ends=True, segments=8, radius=w / 2, matrix=Matrix.Translation((p.x, p.y, z)))
        if nm == "Costa": costa = P
        if nm == "R": R = P
    if costa and R:                                   # celda costal rellena
        try:
            f = corte.faces.new([corte.verts.new((p.x, p.y, 0.0022)) for p in costa + list(reversed(R))]); f.material_index = 1
        except ValueError: pass
    pestana_ala(corte, lado, 0.0026)
    return corte, impresa

def leer_trazado(nombre_marco, lado):
    # Lee las curvas que Sara calco sobre la foto: hijos del vacio 'nombre_marco'.
    # Nombre de cada curva: T_Contorno, T_Corte_<algo> o T_Impresa_<algo>.
    marco = bpy.data.objects.get(nombre_marco)
    if not marco: return None
    inv = marco.matrix_world.inverted(); dg = bpy.context.evaluated_depsgraph_get()
    contorno, lineas = None, []
    for c in marco.children:
        if c.type != 'CURVE': continue
        me = c.evaluated_get(dg).to_mesh(); M = inv @ c.matrix_world
        pts = [(M @ v.co) for v in me.vertices]; c.evaluated_get(dg).to_mesh_clear()
        pts = [(p.x, lado * p.y) for p in pts]
        if c.name.startswith("T_Contorno"): contorno = pts
        elif c.name.startswith("T_Corte_"): lineas.append((c.name[8:].split(".")[0], pts, "corte"))
        elif c.name.startswith("T_Impresa_"): lineas.append((c.name[10:].split(".")[0], pts, "impresa"))
    return contorno, lineas

def membrana_xy(pts, lado):
    bm = bmesh.new(); vs = [bm.verts.new((x, y, 0.0)) for x, y in pts]
    area = sum(pts[i][0] * pts[i - 1][1] - pts[i - 1][0] * pts[i][1] for i in range(len(pts)))
    bm.faces.new(vs if area < 0 else list(reversed(vs)))
    bmesh.ops.triangulate(bm, faces=bm.faces); bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=3, use_grid_fill=True)
    pestana_ala(bm, lado, 0.0)
    largo = max(abs(y) for _, y in pts); xmax = max(x for x, _ in pts)
    capa = bm.loops.layers.float_color.new("degradado")
    base, punta, borde_c = (0.30, 0.85, 0.40, 0.70), (0.55, 0.90, 0.85, 0.22), (0.30, 0.85, 0.35, 0.85)
    for f in bm.faces:
        for l in f.loops:
            u = min(1.0, abs(l.vert.co.y) / largo); vx = l.vert.co.x / xmax
            k = min(1.0, max(0.0, 0.8 * (1 - u) ** 1.6 + 0.35 * max(0.0, vx) * (1 - 0.5 * u)))
            col = tuple(punta[c] + (base[c] - punta[c]) * k for c in range(4))
            l[capa] = borde_c if l.vert.is_boundary and abs(l.vert.co.y) > 0.01 else col
    return bm

def plegado_conico(estaciones, phi, n_phi, pestanas_j, dz=0.0, apoyado=False):
    # estaciones: (x, medio ancho w, altura h sobre el chasis). Con el MISMO angulo phi
    # en todas, cada arco es una copia escalada del anterior -> superficie conica,
    # desarrollable (curvatura gaussiana 0): se puede hacer con una sola lamina.
    bm = bmesh.new(); V = []
    for (x, w, h) in estaciones:
        R = w / math.sin(phi)
        # apoyado: los bordes del arco descansan en el chasis (bandas);
        # si no, se fija la altura de la cumbre (pronoto). En ambos casos R y el
        # centro deben variar LINEALMENTE con x para que sea un cono de verdad.
        zc = (Z_CHASIS + dz - R * math.cos(phi)) if apoyado else (Z_CHASIS + dz + h - R)
        V.append([bm.verts.new((x, R * math.sin(-phi + 2 * phi * k / n_phi), zc + R * math.cos(-phi + 2 * phi * k / n_phi))) for k in range(n_phi + 1)])
    for j in range(len(V) - 1):
        for k in range(n_phi): bm.faces.new((V[j][k], V[j][k+1], V[j+1][k+1], V[j+1][k]))
    tabs = []
    for j in pestanas_j:
        for k in (0, n_phi):
            a, b = V[j][k], V[j+1][k]
            c = bm.verts.new((b.co.x, b.co.y, Z_FONDO)); d = bm.verts.new((a.co.x, a.co.y, Z_FONDO))
            bm.faces.new((a, b, c, d))
            e = bm.edges.get((a, b)); e.seam = True          # linea de grafado
            tabs.append(((a.co + b.co) / 2, abs(a.co.x - b.co.x)))
    return bm, tabs

def interp(est, x):
    xs = [e[0] for e in est]
    if not (min(xs) <= x <= max(xs)): return 0.0
    for a, b in zip(est[:-1], est[1:]):
        if min(a[0], b[0]) <= x <= max(a[0], b[0]):
            t = (x - a[0]) / (b[0] - a[0]) if b[0] != a[0] else 0; return a[1] + t * (b[1] - a[1])
    return 0.0

def ancho_cuerpo(x):
    w = max(interp(CABEZA, x), interp(MESONOTO, x))
    if PRON_X[-1] <= x <= PRON_X[0]: w = max(w, pron_w(x))
    if ABD_X1 <= x <= ABD_X0: w = max(w, abd_ry((ABD_X0 - x) / (ABD_X0 - ABD_X1)))
    r = D_OJO / 2; dx = x - OJO[0]
    if abs(dx) < r: w = max(w, OJO[1] + 0.6 * math.sqrt(r * r - dx * dx))
    return w

# ------------------------------------------------------------------ construir
def construir():
    global COL, RAIZ_OB
    COL = bpy.data.collections.get(COLECCION) or bpy.data.collections.new(COLECCION)
    if COL.name not in bpy.context.scene.collection.children: bpy.context.scene.collection.children.link(COL)
    cortes = {}
    for n in ("Chasis", "Barra", "Cabeza", "Centro"):
        c = bpy.data.collections.get(PREFIJO + "Cortes_" + n) or bpy.data.collections.new(PREFIJO + "Cortes_" + n)
        if c.name not in COL.children: COL.children.link(c)
        c.hide_viewport = True; c.hide_render = True; cortes[n] = c
    for c in [COL] + list(cortes.values()):
        for o in list(c.objects): bpy.data.objects.remove(o, do_unlink=True)
    RAIZ_OB = bpy.data.objects.new(RAIZ, None); COL.objects.link(RAIZ_OB)
    RAIZ_OB.location = UBICACION; RAIZ_OB.empty_display_size = 0.15

    m = dict(carton=material("H_carton", (0.58, 0.45, 0.30), 0.85), torax=material("Cig_torax", (0.33, 0.42, 0.22), 0.45),
             banda=material("Cig_cuerpo", (0.36, 0.30, 0.16), 0.45), pata=material("H_pata", (0.30, 0.42, 0.22), 0.7),
             ojo=material("Cig_ojo", (0.10, 0.18, 0.10), 0.15), perla=material("H_perla", (0.75, 0.80, 0.70), 0.2),
             ala=material_degradado("H_ala_degradado"), vena=material("H_vena_verde", (0.45, 0.85, 0.40), 0.35),
             costa=material("H_vena_costa", (0.22, 0.70, 0.25), 0.35), distal=material("H_vena_distal", (0.82, 0.97, 0.92), 0.3))

    # 1. chasis: silueta dorsal + 1.3 mm de margen
    xs = [0.245 - i * (0.245 - ABD_X1) / 90 for i in range(91)]
    ws = [max(ancho_cuerpo(x), 0.004) + 1.3 * MM for x in xs]
    poli = [(x, w) for x, w in zip(xs, ws)] + [(x, -w) for x, w in reversed(list(zip(xs, ws)))]
    bm = bmesh.new(); losa(bm, poli, Z_CHASIS - CARTON, Z_CHASIS)
    chasis = objeto("Chasis", bm, m["carton"], dict(tecnica="chasis", union="base", apoyo="pared o fondo (separadores 5-10 mm)", material="carton 1,5 mm", orden=1))
    ranuras(chasis, cortes["Chasis"])

    # 2. patas por pares (perfil de carton) sobre el chasis
    for i, (n, ((bx0, bx1, by), pts, anchos)) in enumerate(PATAS.items()):
        bm = bmesh.new(); losa(bm, [(bx0, -by), (bx1, -by), (bx1, by), (bx0, by)], Z_CHASIS, Z_CHASIS + CARTON)
        for lado in (1, -1):
            P = [(x, lado * y) for x, y in pts]
            for s in range(3):
                pol = estadio(P[s], P[s + 1], anchos[s], anchos[min(s + 1, 2)])
                if lado < 0: pol = list(reversed(pol))
                losa(bm, pol if lado > 0 else list(reversed(pol)), Z_CHASIS, Z_CHASIS + CARTON)
        ob = objeto(f"Patas_{n}", bm, m["pata"], dict(tecnica="perfil", material="carton 1,5 mm", apoyo="chasis",
                    union="atrapada por las pestanas del pronoto" if n == "Ant" else "atrapada entre chasis y mesonoto", orden=2 if n != "Ant" else 3))
        if n == "Ant": ranuras(ob, cortes["Barra"])

    # 3. bandas del abdomen (plegado), de atras hacia adelante
    L = (ABD_X0 - ABD_X1) / N_BANDAS
    for i in range(N_BANDAS):
        xf = ABD_X0 - i * L + 0.004
        xb = max(ABD_X1, ABD_X0 - (i + 1) * L - 0.35 * L)
        tt = lambda x: min(1.0, max(0.0, (ABD_X0 - x) / (ABD_X0 - ABD_X1)))
        wf, wb = 0.95 * abd_ry(tt(xf)), 0.95 * abd_ry(tt(xb))
        xm = (xf + xb) / 2; wm, hm = 0.95 * abd_ry(tt(xm)), abd_top(tt(xm)) - Z_CHASIS
        phi = 2 * math.atan(hm / wm)            # arco por los bordes del chasis y la cumbre del perfil
        est = [(xf + s * (xb - xf), wf + s * (wb - wf), 0.0) for s in (0.0, 0.35, 0.65, 1.0)]   # w lineal -> cono
        bm, tabs = plegado_conico(est, phi, 16, [1], dz=0.0025 * (N_BANDAS - 1 - i), apoyado=True)
        objeto(f"Banda_{i + 1}", bm, m["banda"], dict(tecnica="plegado", union="ranura + pestana", apoyo="chasis",
               material="cartulina 200 g", orden=4 + (N_BANDAS - 1 - i)), suave=True)
        for k, (c, lx) in enumerate(tabs):
            cortador(f"corte_banda{i + 1}_{k}", (c.x, c.y, Z_CHASIS - CARTON / 2), (lx + HOLGURA, CARTULINA + 2 * HOLGURA, CARTON * 4), [cortes["Chasis"]])

    # 4. mesonoto (capas) con ranura del remache central
    ob = objeto("Mesonoto", loft(MESONOTO), m["torax"], dict(tecnica="capas", union="remache central", apoyo="chasis",
                material="cartulina", orden=12), suave=True, subdiv=1)
    ranuras(ob, cortes["Centro"])
    # 5. alas planas (membrana + venacion) con pestana atrapada en el mesonoto
    for lado, suf in ((1, "L"), (-1, "R")):
        for n, (cont, venas, largo, cuerda, bis, rz) in ALAS.items():
            loc = (bis[0], lado * bis[1], bis[2]); rot = (0.0, 0.0, math.radians(lado * rz))
            props = dict(union="atrapada entre capas del mesonoto", apoyo="mesonoto", orden=13)
            tz = leer_trazado(f"Trazado_Ala_{n}", lado)
            if tz and tz[0]:
                bm_m = membrana_xy(tz[0], lado); bm_c, bm_i = piezas_desde_lineas(tz[1], lado)
            else:
                bm_m = membrana(cont, largo, cuerda, lado); bm_c, bm_i = venacion(cont, venas, largo, cuerda, lado)
            a = objeto(f"Ala_{n}_{suf}", bm_m, m["ala"], dict(props, tecnica="membrana", material="acetato"))
            v = objeto(f"Vena_{n}_{suf}", bm_c, m["vena"], dict(props, tecnica="celosia", material="papel fino, corte laser"))
            p_ = objeto(f"Impresion_{n}_{suf}", bm_i, m["distal"], dict(props, tecnica="impresion", material="tinta sobre el acetato de la membrana"))
            v.data.materials.append(m["costa"]); v.data.materials.append(m["distal"])
            for o in (a, v, p_): o.location = loc; o.rotation_euler = rot
    # 6. remache central (componente)
    bm = bmesh.new(); remache(bm, REMACHE_C, D_REMACHE / 2)
    for v in bm.verts:                       # cabeza plana: cabe entre mesonoto y pronoto
        if v.co.z > REMACHE_C[2]: v.co.z = REMACHE_C[2] + (v.co.z - REMACHE_C[2]) * 0.3
    objeto("Remache_Centro", bm, m["carton"], dict(tecnica="componente", union="remache", apoyo="mesonoto + chasis",
           material="encuadernador cabeza plana 4 mm (oculto)", diametro_mm=4.0, orden=14), suave=True)
    cortador("corte_centro", (REMACHE_C[0], 0, 0.1), (2 * MM + HOLGURA, 0.008, 0.25), [cortes["Chasis"], cortes["Centro"]])
    # 7. pronoto (plegado) con pestanas que atraviesan barra de patas delanteras y chasis
    est = [(x, pron_w(x), pron_top(x) - Z_CHASIS) for x in PRON_X]
    wm, hm = est[2][1], est[2][2]
    bm, tabs = plegado_conico(est, math.radians(60), 12, [1, 3])
    objeto("Pronoto", bm, m["torax"], dict(tecnica="plegado", union="ranura + pestana", apoyo="chasis + barra de patas delanteras",
           material="cartulina 200 g", orden=15), suave=True)
    for k, (c, lx) in enumerate(tabs):
        cols = [cortes["Chasis"]] + ([cortes["Barra"]] if 0.12 < c.x < 0.16 else [])
        cortador(f"corte_pronoto_{k}", (c.x, c.y, Z_CHASIS - 0.004), (lx + HOLGURA, CARTULINA + 2 * HOLGURA, 0.03), cols)
    # 8. cabeza (capas) + 9. ojos (componente remache que la sujeta al chasis)
    ob = objeto("Cabeza", loft(CABEZA), m["torax"], dict(tecnica="capas", union="remache (ojos)", apoyo="chasis",
                material="cartulina", orden=16), suave=True, subdiv=1)
    ranuras(ob, cortes["Cabeza"])
    for lado, suf in ((1, "L"), (-1, "R")):
        c = (OJO[0], lado * OJO[1], OJO[2])
        bm = bmesh.new(); remache(bm, c, D_OJO / 2)
        objeto(f"Ojo_{suf}", bm, m["ojo"], dict(tecnica="componente", union="remache", apoyo="cabeza + chasis",
               material="encuadernador perla 8 mm", diametro_mm=8.0, orden=17), suave=True)
        cortador(f"corte_ojo_{suf}", (c[0], c[1], 0.1), (2 * MM + HOLGURA, 0.008, 0.25), [cortes["Chasis"], cortes["Cabeza"]])
    return RAIZ_OB

if __name__ == "__main__":
    r = construir(); bpy.context.view_layer.update()
    print("Cigarra hibrida:", len([o for o in r.children if o.type == 'MESH' and not o.name.startswith(PREFIJO + 'corte')]), "piezas")
