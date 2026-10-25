# =============================================================================
# shadowbox_pipeline.py  -  Prototipo v0.2  (CVI - Proyecto final, Sara Cuadrado)
#
# Convierte un insecto 3D (un objeto vacio padre + sus partes) en las capas
# de un shadow box: mapa de alturas por rayos -> cortes por cuantiles ->
# capas apiladas -> plantillas PNG + maqueta 3D + reporte de fabricabilidad.
#
# Como usarlo: abrir en el Text Editor de Blender y pulsar "Run Script".
# Estructuras de datos del cap. 12 que aparecen (ver comentarios [12.x]).
# =============================================================================
import bpy, bmesh, os
import numpy as np
from collections import deque
from mathutils import Vector
from mathutils.bvhtree import BVHTree

# ---------------------------- PARAMETROS -------------------------------------
RAIZ = "Mosca"              # objeto vacio padre del insecto
PREFIJO_MEMBRANA = "Ala"    # partes que van a la lamina translucida
N_CAPAS = 5                 # capas opacas del cuerpo
CELDA = 0.002               # tamano de pixel en unidades de Blender (resolucion)
TAMANO_REAL_CM = 15.0       # lado mayor del insecto dentro de la caja
ANCHO_MIN_MM = 2.0          # ancho minimo cortable (bisturi ~2 mm, laser ~0.5 mm)
AREA_MIN_PIEZA_MM2 = 100    # piezas mas pequenas que esto son dificiles de pegar
COLECCION = "ShadowBox_Proto"
UBICACION_MAQUETA = (0.62, 0.0, 1.0)
SEPARACION = 0.035          # distancia entre capas en la maqueta
GROSOR = 0.004              # grosor de cada lamina en la maqueta


# ---------------------- 1. MALLA EN EL MARCO LOCAL ---------------------------
def malla_local(partes, matriz_inversa_padre):
    # [12.2] Grafo de escena: la posicion mundial de cada parte es el producto de
    # las matrices de su cadena de padres. Multiplicar por la inversa del padre
    # devuelve todo al marco propio del insecto (donde es simetrico).
    # [12.1] Malla de triangulos: se triangula y se guarda a que parte
    # pertenece cada triangulo (dato por cara).
    dg = bpy.context.evaluated_depsgraph_get()
    bm = bmesh.new()
    parte_de_triangulo = []
    for pid, o in enumerate(partes):
        me = o.evaluated_get(dg).to_mesh()
        t = bmesh.new(); t.from_mesh(me)
        bmesh.ops.transform(t, matrix=matriz_inversa_padre @ o.matrix_world, verts=t.verts)
        bmesh.ops.triangulate(t, faces=t.faces)
        tmp = bpy.data.meshes.new("_tmp"); t.to_mesh(tmp); t.free()
        n0 = len(bm.faces); bm.from_mesh(tmp); bpy.data.meshes.remove(tmp)
        parte_de_triangulo += [pid] * (len(bm.faces) - n0)
        o.evaluated_get(dg).to_mesh_clear()
    return bm, parte_de_triangulo


# ---------------------- 2. MAPA DE ALTURAS POR RAYOS -------------------------
def mapa_de_alturas(bm, parte_de_triangulo, limites):
    # [12.3] BVH: jerarquia de cajas envolventes. Cada rayo descarta ramas
    # enteras del arbol en vez de probar todos los triangulos (O(log n)).
    # El resultado es un arreglo 2D [12.5] equivalente a un z-buffer (cap. 9),
    # visto con una camara ortografica cenital (cap. 8).
    bvh = BVHTree.FromBMesh(bm)
    x0, y0, W, H, z_arriba = limites
    altura = np.full((H, W), np.nan, np.float32)
    parte = np.full((H, W), -1, np.int16)
    abajo = Vector((0, 0, -1))
    for j in range(H):
        for i in range(W):
            hit, _n, fi, _d = bvh.ray_cast(Vector((x0 + i * CELDA, y0 + j * CELDA, z_arriba)), abajo)
            if hit is not None:
                altura[j, i] = hit.z
                parte[j, i] = parte_de_triangulo[fi]
    return altura, parte


# ---------------------- 3. CORTES POR CUANTILES ------------------------------
def cortes_por_cuantiles(altura, n):
    # Cortes equidistantes desperdician capas (abajo solo hay patas delgadas).
    # Con cuantiles cada capa recibe la misma cantidad de area visible: es una
    # ecualizacion de histograma de la profundidad (misma idea que el bajo
    # relieve de Weyrich et al. 2007 y la asignacion "equitativa" de Chiba &
    # Matsuyama 2022).
    vals = altura[np.isfinite(altura)]
    cortes = np.quantile(vals, np.linspace(0, 1, n + 1)[:-1])
    cortes[0] = -np.inf
    return cortes


def capas_apiladas(altura, cortes):
    # Capa k = todo lo que esta a altura >= corte k. Asi cada capa queda
    # CONTENIDA en la de abajo, que le sirve de base para pegarla
    # (relacion de inclusion).
    lleno = np.isfinite(altura)
    h = np.where(lleno, altura, -np.inf)
    return [lleno & (h >= c) for c in cortes]


# ---------------------- 4. ANALISIS DE FABRICABILIDAD ------------------------
def componentes(mascara):
    # Busqueda en anchura (BFS) sobre la rejilla: el grafo de vecindad de
    # pixeles. Cada componente es una pieza fisica separada.
    H, W = mascara.shape
    etiqueta = np.zeros(mascara.shape, np.int32); k = 0; tamanos = []
    for j0, i0 in zip(*np.nonzero(mascara)):
        if etiqueta[j0, i0]:
            continue
        k += 1; cola = deque([(j0, i0)]); etiqueta[j0, i0] = k; s = 0
        while cola:
            j, i = cola.popleft(); s += 1
            for a, b in ((j + 1, i), (j - 1, i), (j, i + 1), (j, i - 1)):
                if 0 <= a < H and 0 <= b < W and mascara[a, b] and not etiqueta[a, b]:
                    etiqueta[a, b] = k; cola.append((a, b))
        tamanos.append(s)
    return tamanos


def _erosion(m, r):
    for _ in range(r):
        n = m.copy()
        n[1:, :] &= m[:-1, :]; n[:-1, :] &= m[1:, :]; n[:, 1:] &= m[:, :-1]; n[:, :-1] &= m[:, 1:]
        m = n
    return m


def _dilatacion(m, r):
    for _ in range(r):
        n = m.copy()
        n[1:, :] |= m[:-1, :]; n[:-1, :] |= m[1:, :]; n[:, 1:] |= m[:, :-1]; n[:, :-1] |= m[:, 1:]
        m = n
    return m


def zonas_fragiles(mascara, radio_px):
    # Apertura morfologica: lo que desaparece al erosionar y volver a dilatar
    # es mas delgado que el ancho minimo de corte.
    return mascara & ~_dilatacion(_erosion(mascara, radio_px), radio_px)


# ---------------------- 5. SALIDAS -------------------------------------------
def carpeta_salida():
    if bpy.data.filepath:
        d = os.path.join(os.path.dirname(bpy.data.filepath), "shadowbox_salida")
    else:
        d = os.path.join(bpy.app.tempdir, "shadowbox_salida")
        print("AVISO: el .blend no esta guardado; las plantillas van a una carpeta temporal.")
    os.makedirs(d, exist_ok=True)
    return d


def guardar_png(mascara, nombre, carpeta):
    H, W = mascara.shape
    rgb = np.where(mascara[..., None], 0.0, 1.0).astype(np.float32) * np.ones(3, np.float32)
    rgba = np.concatenate([rgb[::-1], np.ones((H, W, 1), np.float32)], axis=2)
    im = bpy.data.images.get(nombre) or bpy.data.images.new(nombre, W, H)
    if tuple(im.size) != (W, H):
        im.scale(W, H)
    im.pixels.foreach_set(rgba.ravel())
    im.filepath_raw = os.path.join(carpeta, nombre + ".png"); im.file_format = 'PNG'; im.save()


def material(nombre, rgb, alfa=1.0):
    m = bpy.data.materials.get(nombre) or bpy.data.materials.new(nombre)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (*rgb, 1); b.inputs["Roughness"].default_value = 0.8
    b.inputs["Alpha"].default_value = alfa; m.diffuse_color = (*rgb, alfa)
    if alfa < 1:
        m.surface_render_method = 'BLENDED'
    return m


def construir_maqueta(capas, celda):
    col = bpy.data.collections.get(COLECCION) or bpy.data.collections.new(COLECCION)
    if col.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(col)
    for o in list(col.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    paleta = [(0.20, 0.27, 0.40), (0.30, 0.45, 0.60), (0.55, 0.62, 0.55), (0.85, 0.65, 0.35), (0.95, 0.55, 0.16)]
    H, W = capas[0].shape
    bx, by, bz = UBICACION_MAQUETA
    for k, m in enumerate(capas):
        es_alas = (k == len(capas) - 1)
        idx = {}; verts = []; caras = []
        def v(j, i):
            if (j, i) not in idx:
                idx[(j, i)] = len(verts); verts.append(((i - W / 2) * celda, (j - H / 2) * celda, 0.0))
            return idx[(j, i)]
        for j, i in zip(*np.nonzero(m)):
            caras.append((v(j, i), v(j, i + 1), v(j + 1, i + 1), v(j + 1, i)))
        nombre = "SB_alas" if es_alas else f"SB_capa{k + 1}"
        me = bpy.data.meshes.new(nombre); me.from_pydata(verts, [], caras); me.update()
        ob = bpy.data.objects.new(nombre, me); col.objects.link(ob)
        ob.location = (bx, by, bz + 0.01 + k * SEPARACION)
        ob.modifiers.new("grosor", 'SOLIDIFY').thickness = GROSOR
        ob.data.materials.append(material("SB_alas", (0.7, 0.85, 1.0), 0.35) if es_alas
                                 else material(f"SB_m{k}", paleta[k % len(paleta)]))
    # fondo de la caja
    me = bpy.data.meshes.new("SB_fondo"); bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    bm.to_mesh(me); bm.free()
    fondo = bpy.data.objects.new("SB_fondo", me); col.objects.link(fondo)
    fondo.location = (bx, by, bz + 0.004); fondo.scale = (W * celda + 0.08, H * celda + 0.08, 0.008)
    fondo.data.materials.append(material("SB_papel", (0.93, 0.91, 0.86)))


# ---------------------- PROGRAMA PRINCIPAL -----------------------------------
def main():
    raiz = bpy.data.objects[RAIZ]
    inv = raiz.matrix_world.inverted()
    cuerpo = sorted([o for o in raiz.children if not o.name.startswith(PREFIJO_MEMBRANA)], key=lambda o: o.name)
    membranas = sorted([o for o in raiz.children if o.name.startswith(PREFIJO_MEMBRANA)], key=lambda o: o.name)

    bm_c, tri_c = malla_local(cuerpo, inv)
    bm_m, tri_m = malla_local(membranas, inv)

    # [12.3.1] Caja envolvente del insecto completo -> tamano de la rejilla
    pts = [v.co for v in bm_c.verts] + [v.co for v in bm_m.verts]
    xs = [p.x for p in pts]; ys = [p.y for p in pts]; zs = [p.z for p in pts]
    pad = 0.02
    x0, x1, y0, y1 = min(xs) - pad, max(xs) + pad, min(ys) - pad, max(ys) + pad
    W = int((x1 - x0) / CELDA) + 1; H = int((y1 - y0) / CELDA) + 1
    limites = (x0, y0, W, H, max(zs) + 0.1)

    altura, parte = mapa_de_alturas(bm_c, tri_c, limites)
    altura_m, _ = mapa_de_alturas(bm_m, tri_m, limites)
    bm_c.free(); bm_m.free()

    lado_mayor = max(x1 - x0, y1 - y0) - 2 * pad
    mm_por_px = CELDA / lado_mayor * TAMANO_REAL_CM * 10
    radio = max(1, int(round(ANCHO_MIN_MM / mm_por_px / 2)))
    d_min_modelo = ANCHO_MIN_MM / 10 / TAMANO_REAL_CM * lado_mayor

    cortes = cortes_por_cuantiles(altura, N_CAPAS)
    capas = capas_apiladas(altura, cortes)
    alas = np.isfinite(altura_m)

    print("=" * 64)
    print(f"Rejilla {W}x{H} | 1 px = {mm_por_px:.2f} mm reales | insecto = {TAMANO_REAL_CM} cm")
    print(f"Grosor minimo de cualquier apendice en el modelo: {d_min_modelo:.4f} unidades")
    print("Cortes (z local):", np.round(cortes[1:], 3))
    for k, m in enumerate(capas):
        tam = componentes(m)
        peq = [s for s in tam if s * mm_por_px ** 2 < AREA_MIN_PIEZA_MM2]
        frag = zonas_fragiles(m, radio)
        print(f"Capa {k + 1}: {m.sum() * mm_por_px ** 2 / 100:6.1f} cm2 | piezas {len(tam)} "
              f"| pequenas {len(peq)} | fragil {100 * frag.sum() / max(1, m.sum()):4.1f}%")
    print(f"Lamina translucida (membranas): {alas.sum() * mm_por_px ** 2 / 100:.1f} cm2")
    nombres = [o.name for o in cuerpo]
    ocultas = [n for i, n in enumerate(nombres) if not (parte == i).any()]
    if ocultas:
        print("Partes NO visibles desde arriba:", ", ".join(ocultas))
    print("=" * 64)

    carpeta = carpeta_salida()
    for k, m in enumerate(capas):
        guardar_png(m, f"SB_plantilla_capa{k + 1}", carpeta)
    guardar_png(alas, "SB_plantilla_alas", carpeta)
    print("Plantillas en:", carpeta)

    construir_maqueta(capas + [alas], CELDA)
    print("Maqueta 3D en la coleccion:", COLECCION)


if __name__ == "__main__":
    main()
