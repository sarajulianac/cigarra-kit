# =============================================================================
# trazado_alas.py - Marco para CALCAR la venacion sobre la foto de referencia
#  - crear_trazado("Ant"): vacio 'Trazado_Ala_Ant' + curvas editables generadas
#    desde la venacion actual. Nombres:
#       T_Contorno          -> silueta de la membrana (curva cerrada)
#       T_Corte_<nombre>    -> venas que se CORTAN a laser (celosia, una pieza)
#       T_Impresa_<nombre>  -> venas que se IMPRIMEN sobre la membrana
#  - colocar_referencia("Ant", ruta): pone la foto de fondo alineada al ala.
# Coordenadas del marco = coordenadas locales del ala izquierda:
#   x = cuerda (costa hacia +x), y = envergadura (base en 0, punta en +y).
# Despues de editar, correr cigarra_hibrida.py: lee estas curvas.
# =============================================================================
import bpy, math
from mathutils import Vector, Matrix

UBIC_MARCO = {"Ant": (-2.6, -2.6, 1.0), "Post": (-3.1, -2.6, 1.0)}
# foto original: base del ala y escala (px), rotacion para dejar la envergadura vertical
REF = {"Ant": dict(base_frac=(325 / 868, 335 / 1375), alto_px=1375, largo_px=927, rot_grados=180.74)}

def _ns_cigarra():
    ns = {"__name__": "cigarra"}
    exec(compile(bpy.data.texts["cigarra_hibrida.py"].as_string(), "cigarra_hibrida.py", "exec"), ns)
    return ns

def _curva(nombre, pts, padre, col, ciclica=False, color=(1, 1, 1, 1)):
    cu = bpy.data.curves.new(nombre, 'CURVE'); cu.dimensions = '2D' if ciclica else '3D'
    if ciclica: cu.fill_mode = 'NONE'
    sp = cu.splines.new('BEZIER'); sp.bezier_points.add(len(pts) - 1); sp.use_cyclic_u = ciclica
    for bp, (x, y) in zip(sp.bezier_points, pts):
        bp.co = (x, y, 0.004); bp.handle_left_type = bp.handle_right_type = 'AUTO'
    ob = bpy.data.objects.new(nombre, cu); col.objects.link(ob); ob.parent = padre; ob.color = color
    return ob

def _diezmar(pts, n_max=8):
    if len(pts) <= n_max: return pts
    paso = (len(pts) - 1) / (n_max - 1)
    return [pts[round(i * paso)] for i in range(n_max)]

def crear_trazado(n="Ant"):
    ns = _ns_cigarra()
    cont, venas, largo, cuerda, _, _ = ns["ALAS"][n]
    col = bpy.data.collections.get("Trazado_Alas") or bpy.data.collections.new("Trazado_Alas")
    if col.name not in bpy.context.scene.collection.children: bpy.context.scene.collection.children.link(col)
    viejo = bpy.data.objects.get(f"Trazado_Ala_{n}")
    if viejo:
        for c in list(viejo.children): bpy.data.objects.remove(c, do_unlink=True)
        bpy.data.objects.remove(viejo, do_unlink=True)
    marco = bpy.data.objects.new(f"Trazado_Ala_{n}", None); col.objects.link(marco)
    marco.location = UBIC_MARCO[n]; marco.empty_display_type = 'ARROWS'; marco.empty_display_size = 0.08
    def xy(p): return (p[1] * largo * cuerda, p[0] * largo)
    _curva("T_Contorno", [xy(p) for p in cont], marco, col, ciclica=True, color=(0.3, 0.9, 0.4, 1))
    reg = []; ns["venacion"](cont, venas, largo, cuerda, 1, registro=reg)
    for nombre, pts, clase in reg:
        pref = "T_Corte_" if clase == "corte" else "T_Impresa_"
        _curva(pref + nombre, _diezmar([xy(p) for p in pts]), marco, col,
               color=(1.0, 0.45, 0.1, 1) if clase == "corte" else (0.2, 0.8, 1.0, 1))
    return marco

def colocar_referencia(n, ruta):
    marco = bpy.data.objects[f"Trazado_Ala_{n}"]; r = REF[n]
    ns = _ns_cigarra(); largo = ns["ALAS"][n][2]
    img = bpy.data.images.load(ruta, check_existing=True)
    w, h = img.size; u = largo / r["largo_px"] * (h / r["alto_px"]) ** 0 * (r["alto_px"] / h)   # unidades por pixel
    ref = bpy.data.objects.get(f"Referencia_Ala_{n}") or bpy.data.objects.new(f"Referencia_Ala_{n}", None)
    if ref.name not in bpy.data.collections["Trazado_Alas"].objects: bpy.data.collections["Trazado_Alas"].objects.link(ref)
    ref.empty_display_type = 'IMAGE'; ref.data = img; ref.parent = marco
    ref.empty_display_size = max(w, h) * u; ref.use_empty_image_alpha = True; ref.color[3] = 0.85
    ref.empty_image_depth = 'BACK'
    # vector del centro de la imagen a la base del ala (y hacia arriba), rotado
    bx, by = r["base_frac"]
    v = Vector(((bx - 0.5) * w * u, (0.5 - by) * h * u, 0.0))
    R = Matrix.Rotation(math.radians(r["rot_grados"]), 3, 'Z')
    ref.rotation_euler = (0, 0, math.radians(r["rot_grados"])); ref.location = -(R @ v) + Vector((0, 0, -0.002))
    return ref

if __name__ == "__main__":
    crear_trazado("Ant")
    print("marco de calco creado:", [c.name for c in bpy.data.objects["Trazado_Ala_Ant"].children][:6], "...")
