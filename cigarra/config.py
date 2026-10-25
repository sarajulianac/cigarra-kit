# =============================================================================
# config.py  -  Configuracion central del kit (CVI - Proyecto final, Sara Cuadrado)
#
# Unico lugar donde viven la escala y las reglas de fabricacion. Todos los
# modulos del paquete importan de aqui; ninguno repite estos numeros.
#
# Convencion: las medidas fisicas se escriben en MILIMETROS REALES (lo que se
# mide con regla en el carton). Para pasarlas a unidades de Blender se
# multiplica por MM, o se usa a_blender().
#
# Este archivo no importa bpy: se puede leer y probar fuera de Blender.
# =============================================================================

# ---------------------------- ESCALA -----------------------------------------
# Envergadura de la cigarra armada (alas abiertas), en cm.
TAMANO_REAL_CM = 30.0

# Lado del modelo en Blender que corresponde a TAMANO_REAL_CM.
# Ojo: medido con las cajas envolventes, la envergadura actual de los modelos
# es ~1,23 (Cigarra 1,234; Cigarra_H 1,230). Se conserva 1,178 a proposito,
# asi que el kit real sale de ~31,4 cm de envergadura.
LADO_MODELO = 1.178

# Unidades de Blender por milimetro real.
MM = LADO_MODELO / (TAMANO_REAL_CM * 10)


def a_blender(mm):
    """Convierte milimetros reales a unidades de Blender."""
    return mm * MM


def a_mm(unidades):
    """Convierte unidades de Blender a milimetros reales."""
    return unidades / MM


# ---------------------------- VISTA (mapa de alturas) ------------------------
# Tamano de cada pixel del mapa de alturas, en mm reales. ~3 veces mas fino
# que el ancho minimo del laser (0,8 mm), para que los bordes no salgan en escalera.
PIXEL_MM = 0.25

# ---------------------------- CONTORNOS --------------------------------------
# Douglas-Peucker: la linea limpia no se aleja mas de esto del borde trazado.
# Regla: menor o igual al paso de calibracion de la peineta (0,1 mm) y mucho
# menor que el ancho minimo del laser. Del mismo orden que el error del propio
# pixel (~0,12 mm): bajarla mas solo copia la cuadricula.
# Solo se simplifican bordes TRAZADOS (chasis, capas); ranuras y pestanas
# nunca: se calculan exactas y se agregan despues de simplificar.
TOLERANCIA_MM = 0.1

# Borde del chasis alrededor de la silueta del cuerpo (asoma detras de las piezas).
MARGEN_CHASIS_MM = 1.5

# ---------------------------- CAPAS (curvas de nivel) ------------------------
# Capas encima del chasis. El chasis es el nivel 0; con 3 capas los cortes van
# en el 25, 50 y 75 % del area visible del cuerpo (cuantiles).
N_CAPAS = 3
# Islas mas pequenas que esto se descartan: no se pueden agarrar ni sujetar
# con una pestana (~5 x 5 mm). El prototipo usaba 100 mm2 (bisturi + pegante).
AREA_MIN_PIEZA_MM2 = 25.0

# ---------------------------- MATERIALES (grosor, mm) ------------------------
CARTON_MM = 1.5
CARTULINA_MM = 0.4

# Holgura TOTAL de las ranuras (no por lado): la ranura mide grosor + holgura.
# Una por material, porque cada uno se comprime distinto. Valores provisionales;
# se calibran con la peineta de prueba (ver abajo).
HOLGURA_CARTON_MM = 0.3
HOLGURA_CARTULINA_MM = 0.3

# ---------------------------- ANCHOS MINIMOS (mm) ----------------------------
# Lo mas delgado que cada tecnica puede cortar o imprimir sin romperse.
ANCHO_MIN_BISTURI_MM = 2.0
ANCHO_MIN_LASER_MM = 0.8
ANCHO_MIN_IMPRESO_MM = 0.3

# ---------------------------- PEINETA DE PRUEBA ------------------------------
# Ranuras de ancho grosor + desfase (para carton y para cartulina), para probar
# con el laser real cual ajusta mejor (de -0,2 a +0,3 mm en pasos de 0,1).
# Se escriben a mano en vez de generarlas con un paso decimal para evitar
# errores de redondeo (0,30000004).
PEINETA_DESFASES_MM = (-0.2, -0.1, 0.0, 0.1, 0.2, 0.3)

# ---------------------------- ARCHIVOS PARA EL LASER -------------------------
# Convencion de colores mas comun (rojo = cortar, azul = grabar). Confirmar con
# el lugar de corte (Comercial Papelera) y cambiar aqui si usan otra.
COLOR_CORTE = "#ff0000"
COLOR_GRABADO = "#0000ff"
# Trazo "linea fina": muchos programas de laser solo cortan lineas muy delgadas.
TRAZO_MM = 0.1
