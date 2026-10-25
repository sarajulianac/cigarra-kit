# =============================================================================
# maqueta.py  -  Maqueta 3D del kit en Blender: las piezas cortadas, apiladas
#
# Para "armarlo y ver como se ve" antes de cortar (retroalimentacion del 20 oct).
# Cada pieza es una curva 2D de Blender con relleno y extrusion: asi los
# huecos se rellenan bien solos y el grosor es el del carton real.
# Todo va en una coleccion aparte que se rehace en cada corrida; los modelos
# de Sara (Cigarra, Cigarra_H...) no se tocan.
# =============================================================================
import bpy

from . import config

COLECCION = "Maqueta_Capas"
# Tonos de carton: el chasis mas oscuro, las capas mas claras hacia arriba.
TONOS = [(0.35, 0.24, 0.14), (0.55, 0.40, 0.25), (0.70, 0.55, 0.36), (0.84, 0.72, 0.52),
         (0.93, 0.85, 0.68)]


def _coleccion_limpia():
    col = bpy.data.collections.get(COLECCION) or bpy.data.collections.new(COLECCION)
    if col.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(col)
    for obj in list(col.objects):
        datos = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        if datos is not None and datos.users == 0:
            bpy.data.curves.remove(datos)
    return col


def _material(nombre, rgb):
    mat = bpy.data.materials.get(nombre) or bpy.data.materials.new(nombre)
    mat.use_nodes = True
    # Buscar el nodo por tipo, no por nombre (el nombre cambia con el idioma).
    bsdf = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.9
    mat.diffuse_color = (*rgb, 1.0)   # color en la vista Solid
    return mat


def _a_blender(contorno_mm, rejilla):
    """Contorno en mm (origen en el centro del pixel 0) -> coordenadas de la rejilla."""
    px = config.PIXEL_MM
    return [(rejilla.x0 + (x / px + 0.5) * rejilla.celda,
             rejilla.y0 + (y / px + 0.5) * rejilla.celda) for x, y in contorno_mm]


def construir(niveles, rejilla, ubicacion, grosor_mm=config.CARTON_MM):
    """niveles: lista de (nombre_nivel, piezas); cada pieza es una lista de
    contornos en mm (el exterior y sus huecos). El nivel k se apoya sobre el k-1."""
    col = _coleccion_limpia()
    raiz = bpy.data.objects.new(COLECCION, None)
    col.objects.link(raiz)
    raiz.location = ubicacion
    raiz.empty_display_size = 0.1
    grosor = config.a_blender(grosor_mm)

    for k, (nombre_nivel, piezas) in enumerate(niveles):
        mat = _material(f"M_{nombre_nivel}", TONOS[min(k, len(TONOS) - 1)])
        for letra, contornos in zip("abcdefghijklmnopqrstuvwxyz", piezas):
            nombre = f"M_{nombre_nivel}_{letra}"
            curva = bpy.data.curves.new(nombre, 'CURVE')
            curva.dimensions = '2D'
            curva.fill_mode = 'BOTH'           # rellena; los huecos quedan huecos
            curva.extrude = grosor / 2          # extruye a cada lado: grosor total
            for c in contornos:
                pts = _a_blender(c, rejilla)
                spline = curva.splines.new('POLY')
                spline.points.add(len(pts) - 1)
                spline.points.foreach_set("co", [v for x, y in pts for v in (x, y, 0.0, 1.0)])
                spline.use_cyclic_u = True
            curva.materials.append(mat)
            obj = bpy.data.objects.new(nombre, curva)
            obj.location.z = k * grosor + grosor / 2   # cada nivel sobre el anterior
            obj.parent = raiz
            obj["nivel"] = k
            col.objects.link(obj)
    return raiz
