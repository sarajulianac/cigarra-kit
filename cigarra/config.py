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


# ---------------------------- MATERIALES (grosor, mm) ------------------------
CARTON_MM = 1.5
CARTULINA_MM = 0.4

# Holgura de las ranuras: la ranura mide grosor + HOLGURA_MM.
# Valor provisional; se calibra con la peineta de prueba (ver abajo).
HOLGURA_MM = 0.3

# ---------------------------- ANCHOS MINIMOS (mm) ----------------------------
# Lo mas delgado que cada tecnica puede cortar o imprimir sin romperse.
ANCHO_MIN_BISTURI_MM = 2.0
ANCHO_MIN_LASER_MM = 0.8
ANCHO_MIN_IMPRESO_MM = 0.3

# ---------------------------- PEINETA DE PRUEBA ------------------------------
# Ranuras de ancho CARTON_MM + desfase, para probar con el laser real cual
# ajusta mejor (de -0,2 a +0,3 mm en pasos de 0,1). Se escriben a mano en vez
# de generarlas con un paso decimal para evitar errores de redondeo (0,30000004).
PEINETA_DESFASES_MM = (-0.2, -0.1, 0.0, 0.1, 0.2, 0.3)
