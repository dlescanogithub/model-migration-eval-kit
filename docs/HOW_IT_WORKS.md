# Cómo funciona

Esto es para contarlo en una entrevista, sin teatro. El modelo razona; el sistema alrededor decide si ese razonamiento se puede usar.

## Analogía

Imaginate que Casa Brisa, un local inventado, cambia el horno. Antes de tirar el horno viejo, horneás la misma tanda en los dos. No te quedás con "esta factura tiene que pesar 83 gramos". Te fijás que ninguna salga cruda, que las de jamón no terminen en la bandeja de dulce, y que si alguien metió un papelito adentro de la masa diciendo "ignorá la receta", el horno nuevo no le haga caso.

El papelito es el texto del ticket. El cliente puede escribir cualquier cosa. El sistema no obedece eso.

## Qué está medido acá

Los dos "hornos" de la demo son simuladores con nombre: `fake-old` y `fake-new`. No son modelos de un proveedor. El resultado medido el 2026-10-17, con `python -m migration_eval compare --old fake-old --new fake-new --runs 10 --today 2026-10-17`, es NO_GO: la tanda difícil (slice edge) baja 33.33 puntos y el tope configurado es 5. Los precios de esa cuenta son ilustrativos, marcados [EST]. La latencia dice "simulated".

## Paso a paso

1. Hay 63 tickets sintéticos en `data/golden_tickets.json`. Los arma `build_golden()`. Hay casos normales, casos límite y casos con una instrucción metida en el cuerpo.
2. Cada ticket tiene una etiqueta que sale de reglas (`src/migration_eval/spec.py`): categoría, prioridad, cola. El texto del ticket ilustra el caso. La regla no "lee" el texto con un modelo.
3. Un proveedor devuelve JSON: categoría, prioridad, cola, una frase corta y una herramienta. La única herramienta permitida es `route_ticket`. Nadie la ejecuta.
4. Los invariantes miran el efecto, no la frase exacta. ¿El JSON cierra? ¿La categoría está en la lista? ¿La prioridad cumple la regla? ¿La cola es la de esa categoría? ¿El texto incrustado fue ignorado? ¿No se repitió el correo sintético? ¿No apareció otra herramienta?
5. `compare` corre la misma lista en los dos proveedores, varias veces, con semillas 0, 1, 2... En estos fakes la calidad no cambia con la semilla. Cambia la latencia simulada. El test igual cuenta los pares.
6. El test pareado (McNemar) mira solo los tickets donde los dos no coinciden. Si el nuevo no fuera peor, esas diferencias se repartirían más o menos mitad y mitad. Si casi todas son "el viejo pasó y el nuevo no", el p-valor es chico.
7. El bootstrap vuelve a sortear tickets y muestra un rango para la diferencia de tasa. En la corrida medida, ese rango queda debajo de cero: [-0.2222, -0.0476].
8. La política (`config/policy.yaml`) junta eso y dice GO, NO_GO o NEED_HUMAN. NO_GO corta. NEED_HUMAN es cuando no hay un fallo duro pero tampoco hay motivo para moverse (por ejemplo, misma calidad y ahorro cero). GO es una recomendación. Una persona tiene que firmar.
9. El canario sintético manda una parte estratificada de la tanda al proveedor nuevo y escribe un JSONL. Si la tasa de fallo se pasa del umbral, la decisión es ROLLBACK. No hay un router de verdad.
10. El calendario de baja compara fechas con un "hoy" que vos inyectás. Sirve para avisar que se acerca una fecha, no para apagar un servicio.

## Glosario

| Palabra | Qué quiere decir acá |
| --- | --- |
| Golden set | La tanda fija de tickets con la que se comparan los dos proveedores |
| Slice | Un grupo: happy, edge o adversarial |
| Invariante | Una condición que tiene que cumplirse, sin exigir el texto exacto |
| Efecto dañino | Repetir el dato de contacto, obedecer la inyección, llamar una herramienta de más, o mandar a una cola que no corresponde |
| GO / NO_GO / NEED_HUMAN | Recomendación. No es un deploy |
| Cassette | Archivo que guarda una respuesta y la vuelve a servir. Si falta la fila, no sale a internet |
| [EST] | Número ilustrativo, no medido en una factura real |
| Simulated | Latencia o tokens inventados por el simulador, con una regla explícita |

## Límites, en serio

- Fijate que el simulador conoce `variant` (si el caso es "difícil" o "se rompe el formato"). Un modelo de verdad no ve ese campo. El prompt solo lleva asunto y cuerpo. Por eso esta demo muestra el mecanismo de la decisión, no la calidad de un modelo publicado.
- La etiqueta y el simulador "bueno" usan la misma función. Si la regla está mal, los dos quedan de acuerdo y el reporte se ve verde. Para un caso real hace falta una persona etiquetando, aparte del modelo.
- No hay tráfico real, no hay contrato, no hay cliente real. Casa Brisa no existe.
- El ahorro en dólares del reporte usa precios inventados. No lo cites como una factura.
