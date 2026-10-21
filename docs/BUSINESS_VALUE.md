# Value Realization Plan: adopción de `model-migration-eval-kit`

> **Aviso importante**
> - **Cliente ficticio.** "Fintech mediana" es una empresa **inventada** para este ejercicio. No representa a ningún cliente ni empleador real.
> - **Inspirado en el framework AWS Business Value Realization (BVR)**: plan de realización de valor, KPIs con umbral por etapa ("pit stops") y confirmación del cliente. **No es una plantilla oficial de AWS** (la plantilla oficial del VRP no es pública) y **no tengo la AWS BVR Competency**, que se otorga a empresas partner de AWS, no a personas.
> - Etiquetas: **[REPO]** = número que sale del repo (medido o configurado ahí, con su fuente). **[SINTÉTICO]** = supuesto de negocio inventado para el ejercicio. **[REPO-EST]** = cifra que el propio repo marca como estimación ilustrativa.
> - Repo: https://github.com/dlescanogithub/model-migration-eval-kit (commit `85b52b3`, 19/10/2026). Reproduje `compare --old fake-old --new fake-new --runs 10 --today 2026-10-17` y los 85 tests en local el 21/10/2026: dieron los mismos números que el reporte commiteado.

---

## 0. Qué hace realmente el kit (base técnica, [REPO])

- Corre **un mismo golden set de 63 tickets sintéticos** (28 happy, 21 edge, 14 adversarial) [REPO] contra un proveedor "viejo" y uno "nuevo". Puntúa **invariantes**: schema, categoría, prioridad, cola permitida, resistencia a inyección, no repetir datos de contacto y exactamente una tool `route_ticket`. No compara texto exacto.
- Aplica una **política go/no-go** configurable (`config/policy.yaml`) [REPO]:
  - caída máxima por slice: 5 pp;
  - el slice adversarial no puede empeorar;
  - formato ≤0,05 y tool failures ≤0,01;
  - p95 ≤1000 ms;
  - McNemar con α=0,05;
  - ahorro <0,20 → NEED_HUMAN.
- Devuelve **GO / NO_GO / NEED_HUMAN** y un borrador de ADR. **Un humano aprueba**: la herramienta no aprueba ni rutea tráfico.
- Demo medida [REPO]: el slice edge baja de 1,0000 a 0,6667 (−33,33 pp, n=21) → **NO_GO**, aunque el costo simulado por corrida cae de USD 0,069515 a 0,014914 (ratio de ahorro 0,7855, precios [REPO-EST]). McNemar: 8 tickets peores y 0 mejores, p=0,00390625.
  - El NO_GO está **guionado a propósito** en `fake-new` para mostrar que el gate funciona. No es una comparación entre modelos reales.
- Perfiles de control [REPO]: `fake-new-close` → GO; `fake-new-flat` → NEED_HUMAN; `fake-new-degraded` → NO_GO (14 tickets dañinos).
- Corrida live [REPO]: es un **self-compare** (el mismo modelo de los dos lados), no una migración. Costo real ≈ USD 0,053 por corrida contra ≈ USD 0,100 estimado por el repo, que no descuenta los tokens cacheados.
- Lo que el repo **no** hace [REPO]: shadow ni canary sobre tráfico real, labels humanos, revisión de contratos.

---

## 1. Desafío de negocio [SINTÉTICO]

La fintech mediana ficticia clasifica con un LLM unos **30.000 tickets de soporte por mes** [SINTÉTICO] (categoría, prioridad, cola). Hay dos presiones:

1. El proveedor anuncia el **retiro del modelo actual** con fecha de corte.
2. Aparece un modelo **más barato**.

Hoy cada cambio de modelo se decide con pruebas manuales ad hoc: ~2 personas × 1 semana ≈ **80 h por evaluación** [SINTÉTICO], sin métricas por segmento y sin rollback ensayado. Esperan **~4 cambios de modelo por año** [SINTÉTICO]. El año anterior, un cambio "por precio" mandó tickets de cobros fallidos a la cola equivocada (**1 incidente**, costo estimado **USD 10.000** [SINTÉTICO]).

## 2. Objetivos y sponsor [SINTÉTICO]

- **Sponsor ejecutivo:** CTO de la fintech ficticia. **Dueño del GO:** Head of Support. **Dueño de la fecha de corte:** Finanzas. Es la misma división de roles que propone el repo [REPO].
- O1. Decidir cada migración de modelo **en horas o pocos días, no en semanas**, con evidencia reproducible.
- O2. **Cero regresiones silenciosas** en los tickets difíciles y en los adversariales.
- O3. Capturar el ahorro de modelos más baratos **solo cuando el gate da GO** y un humano lo aprueba.
- O4. Llegar a cada fecha de corte con la migración ya decidida y el rollback ensayado.

## 3. KPIs del plan

| KPI | Categoría (BVR / Cloud Value Framework) | Baseline | Objetivo | Cómo se mide | Etapa |
|---|---|---|---|---|---|
| Horas-persona por evaluación de migración | Productividad | 80 h [SINTÉTICO] | ≤16 h [SINTÉTICO] | Registro de horas por migración, desde el pedido hasta el ADR firmado | 1. Activación |
| Tiempo de decisión (pedido → ADR firmado) | Agilidad de negocio | 10 días hábiles [SINTÉTICO] | ≤2 días hábiles [SINTÉTICO] | Fechas del ticket interno vs. la fecha del ADR (`adr.py` genera el borrador) [REPO] | 1. Activación |
| Golden set etiquetado por personas | Resiliencia operativa | 63 tickets sintéticos con labels generados por la spec [REPO]; 0 con labels humanos [SINTÉTICO] | ≥300 tickets con labels humanos, ≥20% edge/adversarial [SINTÉTICO] | Conteo y distribución por slice en el golden set | 1. Activación |
| Caída máxima por slice en una migración aprobada | Resiliencia operativa | Sin medición por slice [SINTÉTICO] | ≤5 pp en todos los slices; 0 pp en adversarial [REPO: `policy.yaml`] | `report.json`: tabla de slices y gates | 2. Escala |
| Tickets dañinos (inyección obedecida, eco de datos, acción peligrosa) | Resiliencia / riesgo | Sin medición [SINTÉTICO] | 0, y nunca mayor que el modelo actual [REPO: política "must not increase"] | Conteo `harmful` del reporte | 2. Escala |
| % de cambios de modelo que pasan por el gate antes de producción | Adopción | 0% [SINTÉTICO] | 100% [SINTÉTICO] | Cambios en la config de ruteo vs. reportes del kit en CI | 2. Escala |
| Rollback ensayado antes de cada canary | Resiliencia operativa | 0 de 4 [SINTÉTICO] | 4 de 4 [SINTÉTICO] | Audit JSONL del canary (`canary.py`) [REPO]. Ojo: el canary del repo es sintético | 2. Escala |
| Costo de modelo por 1.000 tickets | Ahorro de costos | USD 133 [SINTÉTICO] (USD 4.000/mes ÷ 30.000) | −40% (≈USD 80), **solo con GO** [SINTÉTICO] | Factura del proveedor con cache incluido; no la estimación del repo, que sobreestima [REPO] | 3. Retención de valor |
| Incidentes de mal ruteo atribuibles a un cambio de modelo | Resiliencia operativa | 1 por año [SINTÉTICO] | 0 por año [SINTÉTICO] | Post-mortems de soporte | 3. Retención de valor |
| Migraciones cerradas antes de la fecha de corte | Agilidad / continuidad | Sin control [SINTÉTICO] | 100%, con aviso ≥14 días antes [REPO: `warn_within_days: 14`] | `deprecation-check` con la fecha del día [REPO] | 3. Retención de valor |

> Nota: el repo mide pass rate por slice, harmful, formato, tool failures, latencia simulada y costo simulado. **No** mide horas-persona, tiempo de decisión, incidentes ni costo real de producción. Esos KPIs de negocio los tendría que medir el cliente.

## 4. Etapas ("pit stops") con criterios de salida [SINTÉTICO, estructura inspirada en BVR]

1. **Activación** (semanas 1–3)
   - Trabajo: adaptar `spec.py` a las categorías y colas de la fintech, armar el golden set con labels humanos y correr el primer `compare` offline con el modelo actual vs. el candidato.
   - *Salida:* golden set ≥300 tickets; primer reporte leído y ADR firmado por el Head of Support; evaluación ≤16 h.
2. **Uso a escala** (meses 2–3)
   - Trabajo: el gate corre en CI ante cada modelo candidato; canary con rollback ensayado.
   - Hay que **construir** el shadow y el canary sobre tráfico real: en el repo son solo diseño [REPO].
   - *Salida:* 100% de los cambios pasan por el gate; 0 tickets dañinos; caída ≤5 pp por slice.
3. **Retención de valor** (meses 4–12)
   - Trabajo: revisión trimestral de KPIs y recalibración del golden set con tickets nuevos.
   - *Salida:* 0 incidentes de mal ruteo; migraciones cerradas antes del corte; ahorro de modelo verificado en la factura.

**Confirmación del cliente:** al cierre de cada etapa, el sponsor (CTO) y Finanzas firman una nota que confirma los valores de KPI con la evidencia adjunta (reportes, ADR, facturas). Esto replica la idea de BVR de que **el cliente atesta los resultados**.

## 5. ROI (año 1) [TODO SINTÉTICO]

**Fórmulas:** ROI = (beneficio − costo) / costo · Payback (meses) = inversión inicial / beneficio neto mensual

**Supuestos de beneficio** [SINTÉTICO]:

| Concepto | Cálculo | USD/año |
|---|---|---:|
| A. Ahorro de modelo (solo si hay GO) | USD 4.000/mes × 12 × 40% | 19.200 |
| B. Horas de evaluación evitadas | (80 − 16) h × 4 migraciones × USD 30/h | 7.680 |
| C. Incidente de mal ruteo evitado | 1 × USD 10.000 | 10.000 |
| **Beneficio total** | | **36.880** |

**Supuestos de costo** [SINTÉTICO]:

| Concepto | Cálculo | USD |
|---|---|---:|
| Adaptación e integración (inversión inicial) | 120 h × USD 45/h | 5.400 |
| Etiquetado humano del golden set (inversión inicial) | 300 tickets × 3 min = 15 h × USD 30/h | 450 |
| Corridas live de evaluación | 4 migraciones × 10 corridas × USD 0,50 | 20 |
| Mantenimiento | 4 h/mes × USD 45 × 12 | 2.160 |
| **Costo total** | | **8.030** |

**Resultados** [SINTÉTICO]:

| Escenario | Beneficio | ROI | Payback |
|---|---:|---:|---:|
| Base (A+B+C) | 36.880 | **(36.880 − 8.030)/8.030 ≈ 359%** | 5.850 / ((36.880 − 2.160 − 20)/12 = 2.892/mes) ≈ **2,0 meses** |
| Conservador: el gate da NO_GO todo el año, sin ahorro de modelo (B+C) | 17.680 | ≈ 120% | ≈ 4,5 meses |
| Mínimo: solo horas evitadas (B) | 7.680 | ≈ −4% | no recupera en el año |

**Lectura honesta:**
- La mayor parte del valor no viene del ahorro de modelo. Viene de **evitar una mala migración** y de **decidir más rápido**. Ese es justamente el argumento del repo: un modelo más barato que falla en los tickets difíciles no es una migración.
- Si no hay incidentes que evitar y el gate nunca da GO, el kit apenas empata su costo en el año 1.
- El ratio de ahorro de 0,7855 del repo **no se usa** como supuesto, porque sale de precios ilustrativos [REPO-EST]. El 40% también es inventado y hay que reemplazarlo por precios públicos, con URL y fecha.

## 6. Riesgos

| Riesgo | Origen | Mitigación |
|---|---|---|
| Los labels del repo salen de la misma spec que los fakes, así que el pass rate prueba la maquinaria y no la calidad del modelo | [REPO] | Golden set con labels humanos (KPI de la etapa 1) |
| n chico por slice: edge n=21 tiene intervalos amplios (bootstrap edge [−0,5238; −0,1429]) | [REPO] | Ampliar el set a ≥300 tickets; revisar los intervalos además de la decisión |
| El costo estimado ignora tokens cacheados (estimado ≈0,100 vs. real ≈0,053 por corrida) | [REPO] | Medir el ahorro contra la factura real |
| Un self-compare (el mismo modelo de los dos lados) no es evidencia de nada | [REPO] | Comparar solo modelos distintos; documentar el ruido de muestreo |
| Shadow y canary reales no están construidos | [REPO] | Presupuestarlos en la etapa 2 |
| Los equipos se saltean el gate cuando hay apuro por la fecha de corte | [SINTÉTICO] | Bloqueo en CI + calendario con aviso a 14 días |
| Los supuestos de negocio (volumen, tarifas, incidentes) son inventados | [SINTÉTICO] | Reemplazarlos en el discovery con datos del cliente |
