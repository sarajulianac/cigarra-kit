# =============================================================================
# peineta.py  -  Peinetas de prueba para calibrar la holgura de las ranuras
#
# Antes de cortar el kit hay que saber que ancho DIBUJAR para que una pestana
# entre firme sin forzarla. El laser quema un hilo de material (kerf, ~0,1-0,2 mm)
# y eso varia con cada maquina y cada carton, asi que no se calcula: se mide.
#
# Las dos piezas se cortan en CARTON (el chasis es de carton):
#   1. Peine para carton: ranuras ABIERTAS de grosor + desfase. Se prueba
#      metiendo un retazo de carton en cada ranura.
#   2. Tira para cartulina: ranuras CERRADAS (rectangulos), como las del chasis
#      donde entran las pestanas de las bandas del abdomen y del pronoto.
#      Se prueba pasando una tira de cartulina por cada una.
# La ranura que sostiene sin forzar dice la holgura: ancho elegido - grosor.
#
# Uso (desde la carpeta cigarra-kit):  python3 -m cigarra.peineta
# =============================================================================
import os

from . import config
from .exportar import Lienzo

# Medidas de la pieza de prueba (mm). No son reglas del kit: solo de esta prueba.
PROFUNDIDAD = 10.0     # largo de cada ranura
DIENTE = 10.0          # carton entre ranuras: ancho de sobra para que no se doble
FRANJA_TEXTO = 12.0    # espacio bajo las ranuras para las etiquetas
MARGEN = 5.0           # borde de la hoja y separacion entre piezas


def anchos_de_prueba(grosor_mm):
    """Anchos a dibujar: grosor + cada desfase. round() quita el ruido decimal."""
    return [round(grosor_mm + d, 2) for d in config.PEINETA_DESFASES_MM]


def _coma(mm):
    return f"{mm:.1f}".replace(".", ",")


def contorno_peine(anchos, x0=0.0, y0=0.0):
    """Contorno del peine como UNA polilinea cerrada (el laser lo corta de un tiron).

    Se recorre el borde de arriba de izquierda a derecha; en cada ranura el
    camino baja PROFUNDIDAD, avanza el ancho de la ranura y vuelve a subir.
    Devuelve los puntos y el ancho y alto de la pieza.
    """
    ancho_total = sum(anchos) + DIENTE * (len(anchos) + 1)
    alto_total = PROFUNDIDAD + FRANJA_TEXTO
    puntos = [(x0, y0)]
    x = x0 + DIENTE
    for a in anchos:
        puntos += [(x, y0), (x, y0 + PROFUNDIDAD),
                   (x + a, y0 + PROFUNDIDAD), (x + a, y0)]
        x += a + DIENTE
    puntos += [(x0 + ancho_total, y0), (x0 + ancho_total, y0 + alto_total),
               (x0, y0 + alto_total)]
    return puntos, ancho_total, alto_total


def ranuras_cerradas(anchos, x0=0.0, y0=0.0):
    """Tira con ranuras rectangulares cerradas. Devuelve (borde, huecos, ancho, alto)."""
    ancho_total = sum(anchos) + DIENTE * (len(anchos) + 1)
    alto_total = DIENTE / 2 + PROFUNDIDAD + FRANJA_TEXTO
    borde = [(x0, y0), (x0 + ancho_total, y0),
             (x0 + ancho_total, y0 + alto_total), (x0, y0 + alto_total)]
    huecos = []
    x = x0 + DIENTE
    arriba, abajo = y0 + DIENTE / 2, y0 + DIENTE / 2 + PROFUNDIDAD
    for a in anchos:
        huecos.append([(x, arriba), (x + a, arriba), (x + a, abajo), (x, abajo)])
        x += a + DIENTE
    return borde, huecos, ancho_total, alto_total


def _etiquetas(lienzo, anchos, x0, y_ranura_abajo, alto_pieza, y0, titulo):
    x = x0 + DIENTE
    for a in anchos:
        lienzo.texto(x + a / 2, y_ranura_abajo + 5.0, _coma(a))
        x += a + DIENTE
    lienzo.texto(x0 + (x - x0) / 2, y0 + alto_pieza - 2.5, titulo, alto_mm=2.5)


def peineta_svg():
    """Arma el lienzo con las dos piezas, una debajo de la otra."""
    a_carton = anchos_de_prueba(config.CARTON_MM)
    a_cartulina = anchos_de_prueba(config.CARTULINA_MM)

    x0, y_peine = MARGEN, MARGEN
    peine, ancho_p, alto_p = contorno_peine(a_carton, x0, y_peine)
    y_tira = y_peine + alto_p + MARGEN
    borde, huecos, ancho_t, alto_t = ranuras_cerradas(a_cartulina, x0, y_tira)

    lienzo = Lienzo(max(ancho_p, ancho_t) + 2 * MARGEN, y_tira + alto_t + MARGEN)
    # Primero los huecos y despues los bordes exteriores: si la pieza se suelta
    # antes de cortar sus huecos, se mueve y los huecos salen corridos.
    for h in huecos:
        lienzo.polilinea(h)
    lienzo.polilinea(peine)
    lienzo.polilinea(borde)

    _etiquetas(lienzo, a_carton, x0, y_peine + PROFUNDIDAD, alto_p, y_peine,
               f"ranuras para cartón {_coma(config.CARTON_MM)} mm")
    _etiquetas(lienzo, a_cartulina, x0, y_tira + DIENTE / 2 + PROFUNDIDAD, alto_t, y_tira,
               f"ranuras para cartulina {_coma(config.CARTULINA_MM)} mm")
    return lienzo


if __name__ == "__main__":
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ruta = peineta_svg().guardar(os.path.join(raiz, "salida", "peineta_prueba.svg"))
    print("Carton:   ", [_coma(a) for a in anchos_de_prueba(config.CARTON_MM)], "mm")
    print("Cartulina:", [_coma(a) for a in anchos_de_prueba(config.CARTULINA_MM)], "mm")
    print("Guardado en:", ruta)
