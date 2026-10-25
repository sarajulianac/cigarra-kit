# =============================================================================
# cigarra_base.py - Modelo base parametrico de la cigarra (CVI - Proyecto final)
#
# Reglas de modelado aplicadas (salieron del prototipo con la mosca):
#  1. Marco local: cuerpo a lo largo de +X (cabeza adelante), Z arriba,
#     simetria exacta respecto al plano XZ. La orientacion final va en el padre.
#  2. Volumenes (cuerpo, ojos, patas) = mallas CERRADAS (manifold).
#  3. Membranas (alas) = planos aparte con prefijo "Ala"; su origen es la
#     bisagra, asi rotar el objeto = abrir o cerrar el ala.
#  4. Grosor minimo de apendices segun la escala real (ver GROSOR_MIN).
#  5. Patas casi planas, en una sola franja de altura bajo el cuerpo.
# =============================================================================
import bpy, bmesh, math
from mathutils import Vector, Matrix

RAIZ = "Cigarra"
PREFIJO = "C_"                 # evita choques de nombre con otros insectos del archivo
COLECCION = "Cigarra"
UBICACION = (0.0, -2.3, 1.0)
TAMANO_REAL_CM = 15.0
ANCHO_MIN_MM = 2.0
POSE = "exhibicion"            # "exhibicion" (alas abiertas) o "reposo" (alas en techo)
ANCHO_VENA_MM = 0.8            # venacion pensada para corte laser (minimo ~0.5 mm)

# ------------------------------------------------------------------ utilidades
def material(nombre, rgb, rough=0.5, alfa=1.0):
    m = bpy.data.materials.get(nombre) or bpy.data.materials.new(nombre)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Alpha"].default_value = alfa
    m.diffuse_color = (*rgb, alfa)
    if alfa < 1:
        m.surface_render_method = 'BLENDED'
    return m

def objeto(nombre, bm, mat, padre, col, suave=True, subdiv=0):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(nombre); bm.to_mesh(me); bm.free()
    if suave:
        for p in me.polygons: p.use_smooth = True
    ob = bpy.data.objects.new(PREFIJO + nombre, me); col.objects.link(ob)
    ob.parent = padre
    ob.data.materials.append(mat)
    if subdiv:
        ob.modifiers.new("suavizado", 'SUBSURF').levels = subdiv
    return ob

def loft(estaciones, n=28, aplanado=0.65):
    # [12.1] Malla cerrada por "anillos": cada estacion (x, ancho/2, alto/2, z centro)
    # es un anillo eliptico; se unen con quads y se tapan los extremos.
    bm = bmesh.new(); anillos = []
    for (x, ry, rz, zc) in estaciones:
        a = []
        for k in range(n):
            t = 2 * math.pi * k / n
            s = math.sin(t)
            a.append(bm.verts.new((x, ry * math.cos(t), zc + rz * s * (1 if s > 0 else aplanado))))
        anillos.append(a)
    for A, B in zip(anillos[:-1], anillos[1:]):
        for k in range(n):
            bm.faces.new((A[k], A[(k + 1) % n], B[(k + 1) % n], B[k]))
    for anillo, (x, ry, rz, zc) in ((anillos[0], estaciones[0]), (anillos[-1], estaciones[-1])):
        c = bm.verts.new((x, 0, zc))
        for k in range(n):
            bm.faces.new((anillo[k], anillo[(k + 1) % n], c))
    return bm

def segmento(bm, p0, p1, r0, r1, lados=10):
    # cilindro conico cerrado entre dos puntos
    p0, p1 = Vector(p0), Vector(p1); d = (p1 - p0).normalized()
    # base horizontal d x Z: con un numero par de lados, el lado R es el
    # reflejo EXACTO del lado L (misma teselacion, no solo la misma forma)
    u = d.cross(Vector((0, 0, 1)))
    u = u.normalized() if u.length > 1e-6 else d.orthogonal().normalized()
    v = d.cross(u)
    def anillo(p, r):
        return [bm.verts.new(p + r * (math.cos(2*math.pi*k/lados) * u + math.sin(2*math.pi*k/lados) * v)) for k in range(lados)]
    A, B = anillo(p0, r0), anillo(p1, r1)
    for k in range(lados):
        bm.faces.new((A[k], A[(k+1) % lados], B[(k+1) % lados], B[k]))
    for R, p in ((A, p0), (B, p1)):
        c = bm.verts.new(p)
        for k in range(lados):
            bm.faces.new((R[k], R[(k+1) % lados], c))

def articulacion(bm, p, r):
    bmesh.ops.create_icosphere(bm, subdivisions=2, radius=r, matrix=Matrix.Translation(p))

def chaikin(pts, it=3):
    for _ in range(it):
        nuevo = []
        for i in range(len(pts)):
            a, b = Vector(pts[i]), Vector(pts[(i + 1) % len(pts)])
            nuevo += [a * 0.75 + b * 0.25, a * 0.25 + b * 0.75]
        pts = nuevo
    return pts

def ala(contorno_uv, largo, escala_cuerda, lado):
    # Membrana plana: origen en la bisagra, envergadura a lo largo de +Y (o -Y).
    pts = chaikin([(v * largo * escala_cuerda, u * largo) for (u, v) in contorno_uv])
    bm = bmesh.new()
    vs = [bm.verts.new((p.x, lado * p.y, 0.0)) for p in pts]
    bm.faces.new(vs if lado > 0 else list(reversed(vs)))
    bmesh.ops.triangulate(bm, faces=bm.faces)
    return bm

def cinta(bm, pts, ancho, z):
    # Vena = cinta plana de ancho constante a lo largo de una polilinea.
    pts = [Vector((p[0], p[1], z)) for p in pts]
    izq, der = [], []
    for i, p in enumerate(pts):
        a = pts[max(i - 1, 0)]; b = pts[min(i + 1, len(pts) - 1)]
        t = (b - a).normalized(); n = Vector((-t.y, t.x, 0)) * (ancho / 2)
        izq.append(bm.verts.new(p + n)); der.append(bm.verts.new(p - n))
    for i in range(len(pts) - 1):
        bm.faces.new((izq[i], izq[i + 1], der[i + 1], der[i]))

def venacion(contorno_uv, venas_uv, largo, escala_cuerda, lado, ancho):
    # Misma transformacion (u,v) -> (x,y) que la membrana, 1 mm por encima.
    def xy(u, v): return (v * largo * escala_cuerda, lado * u * largo)
    bm = bmesh.new()
    borde = chaikin([(v, u) for (u, v) in contorno_uv])          # vena marginal
    cx = sum(p.x for p in borde) / len(borde); cy = sum(p.y for p in borde) / len(borde)
    borde = [Vector((cx + (p.x - cx) * 0.97, cy + (p.y - cy) * 0.97)) for p in borde]
    cinta(bm, [xy(p.y, p.x) for p in borde] + [xy(borde[0].y, borde[0].x)], ancho, 0.002)
    for vena in venas_uv:
        cinta(bm, [xy(u, v) for (u, v) in vena], ancho, 0.002)
    return bm

# ------------------------------------------------------------------ anatomia
CABEZA = [(0.245, 0.040, 0.022, 0.118), (0.238, 0.070, 0.034, 0.120), (0.225, 0.085, 0.040, 0.122),
          (0.205, 0.088, 0.042, 0.123), (0.190, 0.084, 0.040, 0.122)]
PRONOTO = [(0.198, 0.082, 0.042, 0.124), (0.175, 0.098, 0.052, 0.126), (0.150, 0.115, 0.058, 0.128),
           (0.128, 0.128, 0.060, 0.128), (0.115, 0.130, 0.056, 0.128), (0.106, 0.118, 0.050, 0.128)]
MESONOTO = [(0.112, 0.112, 0.062, 0.130), (0.085, 0.118, 0.072, 0.132), (0.055, 0.115, 0.075, 0.132),
            (0.025, 0.104, 0.070, 0.128), (0.000, 0.085, 0.058, 0.122), (-0.015, 0.064, 0.046, 0.118)]
def abdomen_estaciones(n=34, x0=0.000, x1=-0.205, segmentos=8):
    est = []
    for i in range(n + 1):
        t = i / n; x = x0 + (x1 - x0) * t
        perfil = 0.098 * (1 - t ** 3.0) ** 0.55 + 0.006       # cono romo
        anillo = 1 + 0.025 * math.cos(2 * math.pi * segmentos * t)  # crestas suaves de los segmentos
        est.append((x, perfil * anillo, 0.85 * perfil * anillo, 0.112 - 0.025 * t))
    return est

ALA_ANT = [(0, 0.02), (0.08, 0.06), (0.25, 0.085), (0.5, 0.10), (0.75, 0.105), (0.9, 0.09), (0.98, 0.05),
           (1.0, 0.0), (0.97, -0.06), (0.88, -0.10), (0.7, -0.12), (0.45, -0.115), (0.25, -0.09), (0.1, -0.05), (0.02, -0.02)]
ALA_POST = [(0, 0.02), (0.15, 0.07), (0.4, 0.10), (0.7, 0.10), (0.9, 0.07), (1.0, 0.0), (0.95, -0.08),
            (0.75, -0.14), (0.45, -0.15), (0.2, -0.10), (0.05, -0.04)]
# venas (u = a lo largo del ala 0..1, v = cuerda): longitudinales + transversales + celdas apicales
VENAS_ANT = [
    [(0.03, 0.02), (0.30, 0.075), (0.60, 0.090), (0.72, 0.092)],
    [(0.03, 0.01), (0.35, 0.030), (0.72, 0.035)],
    [(0.03, 0.00), (0.35, -0.010), (0.72, -0.020)],
    [(0.03, -0.01), (0.30, -0.050), (0.60, -0.075), (0.72, -0.090)],
    [(0.03, -0.015), (0.25, -0.070), (0.45, -0.100)],
    [(0.45, 0.085), (0.45, -0.098)],                       # transversal media
    [(0.72, 0.096), (0.72, -0.102)],                       # transversal apical
    [(0.72, 0.070), (0.88, 0.088)], [(0.72, 0.035), (0.96, 0.055)], [(0.72, 0.000), (0.995, 0.005)],
    [(0.72, -0.035), (0.97, -0.055)], [(0.72, -0.070), (0.88, -0.095)],
]
VENAS_POST = [
    [(0.04, 0.015), (0.40, 0.080), (0.62, 0.090)],
    [(0.04, 0.000), (0.62, 0.020), (0.95, 0.030)],
    [(0.04, -0.015), (0.62, -0.050), (0.90, -0.075)],
    [(0.04, -0.025), (0.35, -0.110), (0.55, -0.140)],
    [(0.62, 0.095), (0.62, -0.125)],
]
BISAGRA_ANT = (0.075, 0.085, 0.175)
BISAGRA_POST = (0.040, 0.080, 0.165)
POSES = {  # (rot X dihedro, rot Y, rot Z) en grados para el ala IZQUIERDA; la derecha es espejo
    "exhibicion": {"Ant": (6, 0, 24), "Post": (4, 0, 56)},
    "reposo":     {"Ant": (-4, 38, 84), "Post": (-3, 30, 88)},
}
# patas: puntos cadera -> rodilla -> tobillo -> punta (lado izquierdo, +Y) y radios
PATAS = {
    "Ant":  ([(0.140, 0.040, 0.078), (0.175, 0.110, 0.060), (0.225, 0.140, 0.050), (0.250, 0.150, 0.046)], (0.022, 0.012, 0.0095)),
    "Med":  ([(0.075, 0.050, 0.074), (0.085, 0.130, 0.058), (0.115, 0.175, 0.050), (0.130, 0.195, 0.046)], (0.014, 0.011, 0.0095)),
    "Post": ([(0.010, 0.055, 0.072), (-0.015, 0.130, 0.058), (-0.065, 0.175, 0.050), (-0.085, 0.195, 0.046)], (0.015, 0.011, 0.0095)),
}

def construir():
    col = bpy.data.collections.get(COLECCION) or bpy.data.collections.new(COLECCION)
    if col.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(col)
    for o in list(col.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    raiz = bpy.data.objects.new(RAIZ, None); col.objects.link(raiz)
    raiz.location = UBICACION; raiz.empty_display_type = 'ARROWS'; raiz.empty_display_size = 0.15

    m_cuerpo = material("Cig_cuerpo", (0.36, 0.30, 0.16), 0.45)
    m_torax = material("Cig_torax", (0.33, 0.42, 0.22), 0.45)
    m_ojo = material("Cig_ojo", (0.10, 0.18, 0.10), 0.15)
    m_pata = material("Cig_pata", (0.45, 0.60, 0.35), 0.5)
    m_ala = material("Cig_ala", (0.60, 0.88, 0.62), 0.2, 0.30)
    m_vena = material("Cig_vena", (0.40, 0.72, 0.30), 0.4)
    # ancho de vena en unidades del modelo (el insecto con alas abiertas mide ~1.23)
    ancho_vena = ANCHO_VENA_MM / (TAMANO_REAL_CM * 10) * 1.23

    objeto("Cabeza", loft(CABEZA), m_torax, raiz, col, subdiv=1)
    objeto("Pronoto", loft(PRONOTO), m_torax, raiz, col, subdiv=1)
    objeto("Mesonoto", loft(MESONOTO), m_torax, raiz, col, subdiv=1)
    objeto("Abdomen", loft(abdomen_estaciones()), m_cuerpo, raiz, col, subdiv=1)

    for lado, suf in ((1, "L"), (-1, "R")):
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=16, radius=0.034,
                                  matrix=Matrix.Translation((0.212, lado * 0.108, 0.126)) @ Matrix.Diagonal((0.9, 1.0, 0.95, 1)))
        objeto(f"Ojo_{suf}", bm, m_ojo, raiz, col)

        for nombre, (pts, radios) in PATAS.items():
            bm = bmesh.new()
            P = [Vector((x, lado * y, z)) for (x, y, z) in pts]
            for i in range(3):
                segmento(bm, P[i], P[i + 1], radios[i], radios[min(i + 1, 2)])
                articulacion(bm, P[i + 1], radios[min(i + 1, 2)] * 1.05)
            articulacion(bm, P[0], radios[0] * 1.1)
            objeto(f"Pata_{nombre}_{suf}", bm, m_pata, raiz, col)

        for nombre, contorno, venas, largo, cuerda, bisagra in (("Ant", ALA_ANT, VENAS_ANT, 0.55, 1.5, BISAGRA_ANT),
                                                                 ("Post", ALA_POST, VENAS_POST, 0.32, 1.6, BISAGRA_POST)):
            rx, ry, rz = POSES[POSE][nombre]
            rot = (math.radians(lado * rx), math.radians(ry), math.radians(lado * rz))
            loc = (bisagra[0], lado * bisagra[1], bisagra[2])
            ob = objeto(f"Ala_{nombre}_{suf}", ala(contorno, largo, cuerda, lado), m_ala, raiz, col, suave=False)
            ve = objeto(f"Vena_{nombre}_{suf}", venacion(contorno, venas, largo, cuerda, lado, ancho_vena), m_vena, raiz, col, suave=False)
            for o in (ob, ve):
                o.location = loc; o.rotation_euler = rot
    return raiz

if __name__ == "__main__":
    r = construir()
    print("Cigarra construida:", len(r.children), "partes, pose", POSE)
