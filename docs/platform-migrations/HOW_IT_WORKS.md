# Cómo funciona

Esto es para explicarlo en una entrevista, en castellano rioplatense, sin adornos. El repo corre en tu máquina sobre datos sintéticos. No se conecta a una plataforma real.

## La analogía

Pensalo como una mudanza.

Tenés una casa vieja (la plataforma de ML actual) y una casa nueva (un lakehouse con un registro de experimentos y un registro de modelos). Antes de cargar el camión hacés un inventario: qué cajas hay, quién es dueño de cada una, y qué caja no se puede mover hasta que salga otra. Ese inventario es el manifiesto.

Después armás las tandas. No subís el escritorio si las patas todavía están en el camión de atrás. Esas tandas son las olas de migración.

Cuando la caja llega, no alcanza con decir "está". Abrís y te fijás que tenga las mismas cosas: el esquema, la cantidad de filas, y que los números no se hayan ido a cualquier lado. Eso es la paridad. Si algo no cierra, no firmás la entrega.

El checklist de la puerta es el gate. Si falta la llave de rollback, no cerrás la casa vieja.

## El recorrido, paso a paso

1. **Descubrís.** Diez preguntas en [DISCOVERY.md](DISCOVERY.md). Si no sabés quién es el dueño, el diseño no inventa un dueño.
2. **Escaneás el manifiesto.** `python -m migration_eval platform-migrations scan` lee un YAML o JSON y lo normaliza. Si hay un id duplicado o una referencia colgada, no hay manifiesto válido.
3. **Armás el grafo.** Un dataset depende de sus upstream. Un job depende de lo que lee y de los jobs que lista. Un modelo depende de sus datasets y de sus jobs. La flecha quiere decir "esto se migra antes".
4. **Si hay un ciclo, el plan se frena.** Esos nodos quedan bloqueados. El comando `plan` sale con código 1. No te inventa un orden.
5. **Si no hay ciclo, salen olas.** Kahn agrupa lo que ya no depende de nada. Dentro de cada ola los ids van ordenados. El camino crítico es el camino más largo según el campo `effort` (un peso relativo, no un calendario).
6. **Medís el radio de impacto.** `blast` lista lo que está aguas abajo. Sirve para decir "si este dataset sale mal, estas otras piezas se enteran".
7. **Comparás salidas.** `parity` mira esquema, cantidad de filas, sumas y medias, PSI y KS. El veredicto es `PASS`, `FAIL` o `NEED_HUMAN`. No junta fila contra fila por una clave. Eso queda fuera.
8. **Simulás el registro.** `migrate` copia versiones, stages y aliases a un registro en memoria. La fuente no se toca. La segunda corrida no cambia nada. `rollback` vuelve el destino al snapshot anterior.
9. **Pasás el gate.** Un YAML de controles. `READY` solo si lo obligatorio está en `pass` (o `waived` con aprobador), la paridad no está en `FAIL`, hay plan de rollback y no hay riesgos altos abiertos. `NEED_HUMAN` es una decisión que todavía no tomó nadie.
10. **Escribís el reporte.** `demo` hace todo lo anterior con los fixtures de Aerolito Data (un equipo de analítica ficticio) y deja un Markdown y un HTML. También deja un trace JSONL.

Los evals no piden "llamó a tal función en tal orden". Miran invariantes: la fuente no cambia, el costo simulado queda bajo el tope, no hay una acción externa sin aprobación, un ciclo no se planifica como si nada, la migración es idempotente, el fixture roto no da `PASS`, el rollback restaura, y el cassette no abre la red.

## Glosario

| Palabra | Qué quiere decir acá |
| --- | --- |
| Manifiesto | El inventario: datasets, jobs, modelos, dueños, dependencias. |
| Ola | Un grupo de piezas que ya pueden moverse porque sus dependencias salieron antes. |
| Camino crítico | El camino de mayor `effort` en el DAG. |
| Blast radius | Lo que queda aguas abajo de un nodo. |
| Paridad | La comparación entre salida vieja y salida nueva. |
| PSI | Population Stability Index. Un número de deriva entre dos distribuciones. Lo calcula este repo con bins de ancho fijo. |
| KS | Estadístico de Kolmogorov-Smirnov a dos muestras. También local, sin SciPy. |
| Gate | La política en código sobre el checklist. |
| Cassette | Un JSON con pedidos y respuestas grabadas. El replay no usa la red. |
| Invariante | Una condición que tiene que seguir siendo cierta, pase lo que pase el orden interno. |
| Simulado | Un número que sale de una fórmula con inputs de juguete. No es una factura. |

## Límites, en serio

- No copia datos y no habla con un catálogo, un tracker ni un registro de verdad. `MLMIG_PROVIDER=real` corta antes de abrir un socket.
- No demuestra que un modelo predice bien. La paridad es de tablas, no de calidad de negocio.
- El `effort` no es una estimación de proyecto. Es un peso para ordenar un camino.
- El costo de correr en paralelo es una fórmula ilustrativa. Mirá [COST.md](COST.md).
- Aerolito Data es ficción. Si lo usás con un cliente, cambiá nombres, umbrales y dueños. [ADAPT_TO_A_REAL_CLIENT.md](ADAPT_TO_A_REAL_CLIENT.md).

Si te preguntan "¿esto ya migró una plataforma?", la respuesta es no. Muestra un playbook y unas herramientas que corren sobre fixtures.
