# mis_reglas.py — la regla de bifurcación de las venas
#
# Trabajamos en las coordenadas del ala:
#   u = a lo largo del ala   (0 = base, 1 = ápice)
#   v = de través            (0 = costa, 1 = borde de fuga)
#
# Un TRAMO de vena es una tupla (u0, v0, u1, v1): sale de (u0, v0) y llega a (u1, v1).
# alas_procedurales.py llama a bifurcar() una vez por cada vena del abanico y dibuja
# todos los tramos que le devuelvas (con curva suave y grosor según la altura).


def bifurcar(u, v, v_destino, largo, abertura, generaciones):
    """Una vena que nace en (u, v), sube 'largo' y llega a v_destino.
    Si todavía le quedan generaciones, en su punta nacen DOS venas hijas.
    Devuelve la lista de todos los tramos: el suyo y los de sus hijas."""
    tramos = []

    # 1. El tramo de esta vena: de (u, v) hasta (u + largo, v_destino)
    tramos.append((u,v,u+largo,v_destino))
    
    # 2. Si generaciones es 0, la vena termina aquí: devuelve tramos
    if generaciones == 0:
        return tramos

    # 3. Si no, nacen dos hijas desde la punta (u + largo, v_destino):
    #    - una hacia v_destino - abertura / 2, la otra hacia v_destino + abertura / 2
    #    - las hijas son más cortas (largo * 0.4) y se abren menos (abertura * 0.5)
    #    - y les queda una generación menos
    #    Cada hija ES una vena, así que se construye llamando a... bifurcar.
    #    Suma sus tramos a tu lista.

    tramos += bifurcar(u + largo, v_destino, v_destino - abertura / 2,   # 3. hija izquierda
                       largo * 0.4, abertura * 0.5, generaciones - 1)
    tramos += bifurcar(u + largo, v_destino, v_destino + abertura / 2,   #    hija derecha
                       largo * 0.4, abertura * 0.5, generaciones - 1)
    
    return tramos


if __name__ == "__main__":
    # Prueba: una vena que sube 0.4 y se divide una vez.
    # Debería imprimir 3 tramos, más o menos:
    # [(0.0, 0.5, 0.4, 0.5), (0.4, 0.5, 0.56, 0.4), (0.4, 0.5, 0.56, 0.6)]
    print(bifurcar(0.0, 0.5, 0.5, 0.4, 0.2, 1))
