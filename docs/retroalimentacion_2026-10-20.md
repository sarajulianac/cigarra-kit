# Retroalimentación del profesor — Proyecto final (cigarra para armar)

## 1. Alas: procedurales, no calcadas
- Los patrones de las venas tienen que ver con **fractales**.
- Buscar cómo esas líneas pueden **generarse con un algoritmo** que las dibuje y genere también la textura.

## 2. El modelo 3D y las piezas son estructuras distintas
- El kit es una **aproximación** del modelo 3D, no la misma malla.
- Una vez las piezas tienen posición fija y no se modifican, probablemente basta la **lista indexada**. La half-edge puede servir para analizar el modelo original, pero no es imprescindible para las piezas.

## 3. Cómo iniciar el pipeline
1. Tomar el modelo y **quitarle las alas**.
2. Calcular una **vista ortográfica desde arriba** (no hace falta perspectiva) y sacar la silueta en una imagen de un solo color → **primera pieza: el chasis**.
3. Después decidir **cómo se ensambla**: p. ej. arcos/tiras con muescas en los extremos que entran en **huecos del chasis** (segundo paso de construcción).

## 4. Grafo de escena vs árbol de armado
- El grafo de escena es poco útil aquí, salvo que se haga un simulador.
- Lo que se necesita es una **estructura de armado**: un **árbol** (qué pieza va sobre cuál, numeradas). Ese número de pieza es el que pasa al **manual de ensamble**.
- Si se reutilizan piezas (más largas, más cortas), podría ser un **grafo** en vez de un árbol.

## 5. Cortes por cuantiles = curvas de nivel
- Le pareció un análisis interesante. Son **curvas de nivel**, como en un mapa visto desde arriba: el primer algoritmo para obtener las capas, sin que todas estén a la misma distancia.
- Recomendación: **empezar con una versión sencilla**, armarla y ver cómo se ve antes de agregar más piezas. No se sabe cuánto gana el resultado con más complejidad y más material.

## 6. Textura en perspectiva
- "No tenemos ojos ortográficos, tenemos ojos en proyección."
- La textura de cada pieza debería ser lo que el observador vería **en perspectiva** desde su punto de vista: calcular la textura desde esa cámara y pegarla a cada pieza.

## 7. Uniones
- Falta **definir bien las uniones**.
- Mirar **origami** y técnicas para unir figuras de papel. Entre más sencillas las uniones, mejor.
