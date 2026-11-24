# produccion_prueba.py — Cigarra para armar · archivos para la prueba de impresión 3D
#
# Genera, a partir de Mecanismo_Alas.blend:
#   · ala_A_estructura.stl, ala_C_estructura.stl  (estructura + raíz en UNA pieza, plana)
#   · hombro_1_tapa … hombro_4_base.stl           (esfera en 4 rodajas sobre el tornillo M3)
#   · soporte_lengueta.stl, soporte_columna.stl
# Todo en mm, en la carpeta prueba_impresion/ junto al .blend. No modifica la cigarra.

import bpy, bmesh, math, os, struct
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

D = os.path.dirname(bpy.data.filepath)
OUT = os.path.join(D, "prueba_impresion")
os.makedirs(OUT, exist_ok=True)
AP = {"__name__": "alas_procedurales"}
exec(compile(open(os.path.join(D, "alas_procedurales.py"), encoding="utf-8").read(), "alas_procedurales", "exec"), AP)
MM = 0.001

# ---------------------------------------------------------------- parámetros de impresión
GROSOR_ALA = 1.6       # mm, estructura impresa (la raíz es de 2.0)
GROSOR_RAIZ = 2.0
ANCHO_MIN = 1.0        # mm, ninguna vena más delgada (boquilla 0.4 = 2 perímetros)
R_PASADOR = 1.75       # mm, agujero para tornillo M3 (holgura 0.25)
VOXEL = 0.15           # mm, resolución con que se fusionan las venas en un solo sólido

R_ESFERA = 10.0
SUBIR_ESFERA = 2.5     # mm a lo largo del eje: la cabeza del tornillo queda al ras sin tocar la raíz
HOLGURA_FIJA = 0.15    # bolsillo de la raíz anterior (ajustada)
HOLGURA_GIRO = 0.30    # bolsillos que giran (raíz posterior, lengüeta)
LENGUETA_Z = (-4.5, -2.0)   # mm en el marco del eje: lengüeta del soporte, 2.5 de grueso
CABEZA = dict(r=3.0, desde=8.0)            # avellanado de la cabeza M3 (relativo al centro)
TUERCA = dict(r=3.4, hasta=-7.6)           # hexágono de la tuerca M3


# ---------------------------------------------------------------- utilidades
def ob(n): return bpy.data.objects[n]


def bm_a_objeto(bm, nombre, col):
    me = bpy.data.meshes.new(nombre); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(nombre, me); col.objects.link(o)
    return o


def coleccion():
    c = bpy.data.collections.get("Produccion_Prueba")
    if c:
        for o in list(c.all_objects): bpy.data.objects.remove(o, do_unlink=True)
    else:
        c = bpy.data.collections.new("Produccion_Prueba"); bpy.context.scene.collection.children.link(c)
    return c


def aplicar(o):
    """Devuelve una malla nueva con todos los modificadores aplicados."""
    dg = bpy.context.evaluated_depsgraph_get()
    e = o.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(e, preserve_all_data_layers=False, depsgraph=dg)
    o.modifiers.clear(); old = o.data; o.data = me; bpy.data.meshes.remove(old)
    return o


def remesh(o, voxel_mm, objetivo=250000):
    """Fusiona sólidos superpuestos en uno solo (voxeles) y simplifica las caras planas."""
    m = o.modifiers.new("vox", "REMESH"); m.mode = "VOXEL"; m.voxel_size = voxel_mm * MM
    m.use_smooth_shade = False
    aplicar(o)
    n = len(o.data.polygons)
    if n > objetivo:   # simplificar hasta ~objetivo caras (colapso de aristas: conserva el sólido)
        d = o.modifiers.new("simple", "DECIMATE"); d.decimate_type = "COLLAPSE"
        d.ratio = objetivo / (2 * n); d.use_collapse_triangulate = True   # n caras cuadradas = 2n triángulos
        aplicar(o)
    return o


def booleano(o, cortador, op="DIFFERENCE"):
    m = o.modifiers.new("b", "BOOLEAN"); m.operation = op; m.object = cortador; m.solver = "EXACT"
    return aplicar(o)


def escribir_stl(o, ruta, matriz=None):
    """STL binario en mm. matriz: transformación extra (por ejemplo, acostar la pieza)."""
    M = (matriz or Matrix()) @ o.matrix_world
    me = o.data; me.calc_loop_triangles()
    tris = []
    for t in me.loop_triangles:
        p = [M @ me.vertices[i].co * 1000 for i in t.vertices]
        n = (p[1] - p[0]).cross(p[2] - p[0]).normalized()
        tris.append((n, p))
    # apoyar en z = 0
    zmin = min(v.z for _, p in tris for v in p)
    with open(ruta, "wb") as f:
        f.write(b"cigarra-kit".ljust(80, b" ")); f.write(struct.pack("<I", len(tris)))
        for n, p in tris:
            f.write(struct.pack("<3f", *n))
            for v in p: f.write(struct.pack("<3f", v.x, v.y, v.z - zmin))
            f.write(b"\0\0")
    return len(tris)


def es_solido(o):
    bm = bmesh.new(); bm.from_mesh(o.data)
    malo = sum(1 for e in bm.edges if not e.is_manifold); bm.free()
    return malo == 0


def prisma_de_contorno(pts2d, z0, z1, holgura, M=None):
    """Envolvente convexa de pts2d (mm), agrandada 'holgura', extruida de z0 a z1 (mm)."""
    P = sorted(set((round(p[0], 4), round(p[1], 4)) for p in pts2d))
    def cruz(o, a, b): return (a[0]-o[0])*(b[1]-o[1]) - (a[1]-o[1])*(b[0]-o[0])
    lo, hi = [], []
    for p in P:
        while len(lo) >= 2 and cruz(lo[-2], lo[-1], p) <= 0: lo.pop()
        lo.append(p)
    for p in reversed(P):
        while len(hi) >= 2 and cruz(hi[-2], hi[-1], p) <= 0: hi.pop()
        hi.append(p)
    casco = [Vector(p) for p in lo[:-1] + hi[:-1]]
    casco = AP["desplazar"](casco, -holgura)   # antihorario: negativo = hacia afuera
    bm = bmesh.new()
    M = M or Matrix()
    b = [bm.verts.new(M @ Vector((p.x, p.y, z0)) * MM) for p in casco]
    t = [bm.verts.new(M @ Vector((p.x, p.y, z1)) * MM) for p in casco]
    bm.faces.new(list(reversed(b))); bm.faces.new(t)
    n = len(casco)
    for i in range(n):
        bm.faces.new((b[i], b[(i+1) % n], t[(i+1) % n], t[i]))
    return bm


def cilindro(r, z0, z1, M=None, lados=32, hexagono=False):
    bm = bmesh.new(); M = M or Matrix()
    k = 6 if hexagono else lados
    b = [bm.verts.new(M @ Vector((r*math.cos(2*math.pi*i/k), r*math.sin(2*math.pi*i/k), z0)) * MM) for i in range(k)]
    t = [bm.verts.new(M @ Vector((r*math.cos(2*math.pi*i/k), r*math.sin(2*math.pi*i/k), z1)) * MM) for i in range(k)]
    bm.faces.new(list(reversed(b))); bm.faces.new(t)
    for i in range(k): bm.faces.new((b[i], b[(i+1) % k], t[(i+1) % k], t[i]))
    return bm


def mm_local(o):
    return [Vector(v.co) * 1000 for v in o.data.vertices]


# ---------------------------------------------------------------- 1. alas
def eje_en_pose(pose):
    """El eje de giro (punto y dirección) en el marco de la pose del ala, en reposo, en mm."""
    bpy.context.scene.frame_set(1)
    M = ob(pose).matrix_world.inverted() @ ob("Eje_L").matrix_world
    p = M @ Vector((0, 0, 0)) * 1000
    d = (M.to_3x3() @ Vector((0, 0, 1))).normalized()
    return p, d


def raiz(parte, col):
    """La raíz plana con su agujero OBLICUO: el tornillo la cruza a lo largo del eje de giro."""
    pts = [(p.x, p.y) for p in mm_local(ob(f"Raiz_{parte}"))]
    o = bm_a_objeto(prisma_de_contorno(pts, 0, GROSOR_RAIZ, 0.0), f"_raiz_{parte}", col)
    p, d = eje_en_pose(f"Pose_{parte}")
    M = Matrix.Translation(p) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()
    c = bm_a_objeto(cilindro(R_PASADOR, -15, 15, M), f"_pasador_{parte}", col)
    booleano(o, c); bpy.data.objects.remove(c)
    return o


def ala(clave, col, parte="Ant"):
    v = AP["VERSIONES"][clave]
    gen = AP["venacion_organica"] if v.get("organica") else AP["venacion"]
    contorno, est, adh = gen(AP["ALA_ANT"] if parte == "Ant" else AP["ALA_POST"], v)
    bm = bmesh.new()
    for pts, w0, w1 in est:
        AP["cinta"](bm, pts, max(w0, ANCHO_MIN), max(w1, ANCHO_MIN), 0.0, GROSOR_ALA)
    o = bm_a_objeto(bm, f"Ala_{clave}_{parte}_estructura", col)
    r = raiz(parte, col)
    # unir venas + raíz en un solo sólido (voxeles), y luego volver a abrir el agujero oblicuo
    bm = bmesh.new(); bm.from_mesh(o.data); bm.from_mesh(r.data); bm.to_mesh(o.data); bm.free()
    bpy.data.objects.remove(r)
    remesh(o, VOXEL)
    p, d = eje_en_pose(f"Pose_{parte}")
    M = Matrix.Translation(p) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()
    c = bm_a_objeto(cilindro(R_PASADOR, -15, 15, M), "_pasador", col)
    booleano(o, c); bpy.data.objects.remove(c)
    return o, contorno


def hacer_alas(col, parte="Ant"):
    info = {}
    for i, clave in enumerate(("A", "C")):
        o, contorno = ala(clave, col, parte)
        o.location.x = (0.9 + 0.1 * i)   # a un lado de todo
        nombre = f"ala_{clave}_estructura" if parte == "Ant" else f"ala_{clave}_posterior_estructura"
        ruta = os.path.join(OUT, nombre + ".stl")
        # acostada en diagonal para una cama de 256 x 256
        rot = Matrix.Rotation(math.radians(-45), 4, "Z")
        n = escribir_stl(o, ruta, rot @ Matrix.Translation(-o.matrix_world.translation))
        dims = [round(x * 1000, 1) for x in o.dimensions]
        info[clave] = dict(triangulos=n, medidas_mm=dims, solido=es_solido(o))
    return info


# ---------------------------------------------------------------- 2. hombro (esfera en 4 rodajas)
def marco_en_eje(nombre, frame=1):
    bpy.context.scene.frame_set(frame)
    M = ob("Eje_L").matrix_world.inverted() @ ob(nombre).matrix_world
    return Matrix.Translation(M.translation * 1000) @ M.to_3x3().to_4x4()   # en mm


def angulo_z(nombre, frame):
    bpy.context.scene.frame_set(frame)
    return math.degrees(ob(nombre).matrix_local.to_euler().z)


def recorridos():
    """Cuánto gira la raíz posterior respecto a la esfera, y la esfera respecto al soporte."""
    a0, p0 = angulo_z("Pivote_Ant_L", 1), angulo_z("Pivote_Post_L", 1)
    rel_post, rel_lengueta = [], []
    for f in range(1, 121):
        a, p = angulo_z("Pivote_Ant_L", f) - a0, angulo_z("Pivote_Post_L", f) - p0
        rel_post.append(p - a)          # la posterior vista desde la esfera
        rel_lengueta.append(-a)         # la lengüeta (fija) vista desde la esfera
    bpy.context.scene.frame_set(1)
    return (min(rel_post), max(rel_post)), (min(rel_lengueta), max(rel_lengueta))


def barrido(bm_fn, desde, hasta, paso=2.0, margen=2.0):
    """Une copias giradas alrededor del eje: el espacio que una pieza recorre al girar."""
    bm = bmesh.new()
    ang = desde - margen
    while ang <= hasta + margen + 1e-6:
        R = Matrix.Rotation(math.radians(ang), 4, "Z")
        b = bm_fn(R); me = bpy.data.meshes.new("_t"); b.to_mesh(me); b.free()
        bm.from_mesh(me); bpy.data.meshes.remove(me)
        ang += paso
    return bm


def unir_bm(lista):
    bm = bmesh.new()
    for b in lista:
        me = bpy.data.meshes.new("_t"); b.to_mesh(me); b.free(); bm.from_mesh(me); bpy.data.meshes.remove(me)
    return bm


def rodaja(c, planos, col, nombre):
    """Esfera de centro c (mm) recortada por planos [(punto, normal, conservar_lado_positivo)]."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=96, v_segments=48, radius=R_ESFERA * MM,
                              matrix=Matrix.Translation(c * MM))
    for co, no, positivo in planos:
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        r = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co * MM, plane_no=no,
                                   clear_inner=positivo, clear_outer=not positivo)
        borde = [e for e in bm.edges if e.is_boundary]
        bmesh.ops.holes_fill(bm, edges=borde, sides=0)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm_a_objeto(bm, nombre, col)


def libre(cav_bvh, p_mm, r_mm):
    """¿Hay al menos r_mm de material entre p y cualquier hueco?"""
    loc, n, i, dist = cav_bvh.find_nearest(p_mm * MM)
    if loc is None: return True
    afuera = (p_mm * MM - loc).dot(n) > 0
    return afuera and dist * 1000 > r_mm


def hacer_hombro(col):
    c = Vector((0, 0, SUBIR_ESFERA))
    M_ant, M_post = marco_en_eje("Pose_Ant"), marco_en_eje("Pose_Post")
    raiz_ant = [(p.x, p.y) for p in mm_local(ob("Raiz_Ant"))]
    raiz_post = [(p.x, p.y) for p in mm_local(ob("Raiz_Post"))]
    M_len = marco_en_eje("Soporte_Lengueta")
    leng = [(M_len @ p) for p in mm_local(ob("Soporte_Lengueta"))]
    leng2d = [(p.x, p.y) for p in leng]
    (pmin, pmax), (lmin, lmax) = recorridos()

    # --- el hueco: todo lo que la esfera tiene que dejar libre
    partes = [
        prisma_de_contorno(raiz_ant, -HOLGURA_FIJA, GROSOR_RAIZ + HOLGURA_FIJA, HOLGURA_FIJA, M_ant),
        barrido(lambda R: prisma_de_contorno(raiz_post, -HOLGURA_GIRO, GROSOR_RAIZ + HOLGURA_GIRO,
                                             HOLGURA_GIRO, R @ M_post), pmin, pmax),
        barrido(lambda R: prisma_de_contorno(leng2d, LENGUETA_Z[0] - HOLGURA_GIRO, LENGUETA_Z[1] + HOLGURA_GIRO,
                                             HOLGURA_GIRO, R), lmin, lmax, paso=3.0),
        cilindro(R_PASADOR, -30, 30),
        cilindro(CABEZA["r"], c.z + CABEZA["desde"], c.z + 20),
        cilindro(TUERCA["r"], c.z - 20, c.z + TUERCA["hasta"], hexagono=True),
    ]
    cav = bm_a_objeto(unir_bm(partes), "_hueco", col)
    remesh(cav, 0.1, objetivo=40000)
    bmc = bmesh.new(); bmc.from_mesh(cav.data); cav_bvh = BVHTree.FromBMesh(bmc); bmc.free()

    # --- planos de corte: la cara de abajo de cada raíz y de la lengüeta
    n1 = (M_ant.to_3x3() @ Vector((0, 0, 1))).normalized(); p1 = M_ant @ Vector((0, 0, GROSOR_RAIZ / 2))  # a mitad de la raíz: la amarra a tapa y medio
    n2 = (M_post.to_3x3() @ Vector((0, 0, 1))).normalized(); p2 = M_post.translation.copy()
    n3 = Vector((0, 0, 1)); p3 = Vector((0, 0, LENGUETA_Z[0]))
    piezas = [
        ("hombro_1_tapa", [(p1, n1, True)], n1),
        ("hombro_2_medio", [(p1, n1, False), (p2, n2, True)], n2),
        ("hombro_3_bajo", [(p2, n2, False), (p3, n3, True)], n3),
        ("hombro_4_base", [(p3, n3, False)], -n3),
    ]
    objs = []
    for nombre, planos, abajo in piezas:   # abajo: la dirección que queda hacia ARRIBA al imprimir
        o = rodaja(c, planos, col, nombre)
        booleano(o, cav)
        objs.append((o, abajo))

    # --- pines de registro entre rodajas (para que no giren entre ellas)
    pines = []
    for k, (co, no) in enumerate(((p1, n1), (p2, n2), (p3, n3))):
        base = no.orthogonal().normalized(); otro = no.cross(base)
        cand = []
        for i in range(24):
            a = 2 * math.pi * i / 24
            for r in (6.0, 5.0, 7.0):
                q = co + (base * math.cos(a) + otro * math.sin(a)) * r
                # el pin cruza el plano: revisar arriba y abajo
                if all(libre(cav_bvh, q + no * h, 1.6) for h in (-1.6, 0.0, 1.6)) and \
                        (q - c).length < R_ESFERA - 2.2:
                    cand.append((a, r, q)); break
        if k != 1:   # plano 1: la raíz anterior amarra tapa y medio; plano 3: la base es simétrica
            continue
        if len(cand) < 2:
            print("· pocos sitios para pines en el plano", k + 1, len(cand)); continue
        # los dos más separados
        mejor = max(((x, y) for x in cand for y in cand), key=lambda t: (t[0][2] - t[1][2]).length)
        for _, _, q in mejor:
            M = Matrix.Translation(q) @ no.to_track_quat("Z", "Y").to_matrix().to_4x4()
            pines.append((k, M))
    for k, M in pines:
        arriba, abajo_o = objs[k][0], objs[k + 1][0]
        clavo = bm_a_objeto(cilindro(1.0, -0.6, 1.5, M, lados=24), "_clavo", col)
        booleano(abajo_o, clavo, "UNION"); bpy.data.objects.remove(clavo)
        hueco = bm_a_objeto(cilindro(1.2, -0.05, 1.8, M, lados=24), "_hueco_pin", col)
        booleano(arriba, hueco); bpy.data.objects.remove(hueco)
    bpy.data.objects.remove(cav)

    info = {}
    for o, abajo in objs:
        # acostar sobre su cara plana
        R = abajo.to_track_quat("Z", "Y").to_matrix().to_4x4().inverted()
        n = escribir_stl(o, os.path.join(OUT, o.name + ".stl"), R)
        info[o.name] = dict(tri=n, solido=es_solido(o), vol_mm3=round(volumen(o), 1))
    info["recorrido_posterior"] = (round(pmin, 1), round(pmax, 1))
    info["recorrido_lengueta"] = (round(lmin, 1), round(lmax, 1))
    info["pines"] = len(pines)
    return info, objs


# ---------------------------------------------------------------- 3. soporte
def en_mundo(o):
    """bmesh de un objeto con su transformación aplicada (metros, mundo)."""
    bm = bmesh.new(); bm.from_mesh(o.data); bm.transform(o.matrix_world); return bm


def hacer_soporte(col):
    bpy.context.scene.frame_set(1)
    E = ob("Eje_L").matrix_world
    M_len = marco_en_eje("Soporte_Lengueta")
    leng2d = [((M_len @ p).x, (M_len @ p).y) for p in mm_local(ob("Soporte_Lengueta"))]
    b = prisma_de_contorno(leng2d, LENGUETA_Z[0], LENGUETA_Z[1], 0.0)
    b.transform(E)                                   # del marco del eje al mundo
    for n in ("Soporte_Columna", "Soporte_Pie"):
        me = bpy.data.meshes.new("_t"); b.to_mesh(me); b.free()
        b = en_mundo(ob(n)); b.from_mesh(me); bpy.data.meshes.remove(me)
    o = bm_a_objeto(b, "soporte", col)
    remesh(o, 0.12, objetivo=60000)
    pas = bm_a_objeto(cilindro(R_PASADOR, -30, 30), "_pas", col); pas.matrix_world = E
    booleano(o, pas); bpy.data.objects.remove(pas)
    n = escribir_stl(o, os.path.join(OUT, "soporte.stl"))
    return dict(tri=n, solido=es_solido(o), medidas_mm=[round(x * 1000, 1) for x in o.dimensions])


# ---------------------------------------------------------------- 4. membranas (SVG carta, mm)
def recortar_semiplano(poly, y0):
    out = []
    for i in range(len(poly)):
        a, b = poly[i - 1], poly[i]
        ia, ib = a.y >= y0, b.y >= y0
        if ia != ib:
            t = (y0 - a.y) / (b.y - a.y); out.append(a.lerp(b, t))
        if ib: out.append(b)
    return out


def hacer_membranas(y_corte=12.0):
    """Hoja carta: las dos membranas (A y C, mismo contorno) con la huella de su estructura."""
    W, H = 215.9, 279.4
    partes = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}mm" height="{H}mm" viewBox="0 0 {W} {H}">']
    for i, clave in enumerate(("A", "C")):
        v = AP["VERSIONES"][clave]
        gen = AP["venacion_organica"] if v.get("organica") else AP["venacion"]
        contorno, est, adh = gen(AP["ALA_ANT"], v)
        memb = recortar_semiplano(contorno, y_corte)
        xs = [p.x for p in memb]; ys = [p.y for p in memb]
        ox = 15 + i * 100 - min(xs); oy = 8 + max(ys)          # el ápice arriba
        T = lambda p: (round(ox + p.x, 2), round(oy - p.y, 2))
        g = []
        for pts, w0, w1 in est:   # huella de la estructura, solo como guía (gris)
            d = " ".join(f"{x},{y}" for x, y in (T(p) for p in pts))
            g.append(f'<polyline points="{d}" fill="none" stroke="#b8d8b0" stroke-width="{max((w0 + w1) / 2, ANCHO_MIN):.2f}" stroke-linecap="round" stroke-linejoin="round"/>')
        for pts, w0, w1 in adh:   # venas del adhesivo (A), finas
            d = " ".join(f"{x},{y}" for x, y in (T(p) for p in pts))
            g.append(f'<polyline points="{d}" fill="none" stroke="#999" stroke-width="0.3"/>')
        d = " ".join(f"{x},{y}" for x, y in (T(p) for p in memb))
        g.append(f'<polygon points="{d}" fill="none" stroke="#000" stroke-width="0.25"/>')
        g.append(f'<text x="{15 + i * 100}" y="{H - 14}" font-family="Helvetica" font-size="3.2" fill="#333">'
                 f'Membrana ala anterior · versión {clave} · {round(max(ys) - y_corte)} mm</text>')
        partes += g
    partes.append(f'<rect x="170" y="{H - 22}" width="10" height="10" fill="none" stroke="#000" stroke-width="0.25"/>'
                  f'<text x="182" y="{H - 15}" font-family="Helvetica" font-size="3" fill="#333">1 cm</text>'
                  f'<text x="15" y="{H - 8}" font-family="Helvetica" font-size="3" fill="#333">'
                  f'Imprimir al 100 %. Negro = cortar (acetato o papel). Verde = dónde va la estructura impresa (guía).</text>')
    partes.append("</svg>")
    ruta = os.path.join(OUT, "membranas_A_C_carta.svg")
    open(ruta, "w", encoding="utf-8").write("\n".join(partes))
    return ruta


def volumen(o):
    bm = bmesh.new(); bm.from_mesh(o.data); v = bm.calc_volume(signed=True) * 1e9; bm.free()
    return v


if __name__ == "__main__":
    col = coleccion()
    print("alas", hacer_alas(col))
    print("membranas", hacer_membranas())
    print("hombro", hacer_hombro(col)[0])
    print("soporte", hacer_soporte(col))
