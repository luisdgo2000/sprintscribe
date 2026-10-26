# SprintScribe

![Versión](https://img.shields.io/badge/versi%C3%B3n-0.1.0-blue)
![Estado](https://img.shields.io/badge/estado-primera%20versi%C3%B3n-orange)
![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![Pruebas](https://img.shields.io/badge/pruebas-42%20OK-brightgreen)
![Licencia](https://img.shields.io/badge/licencia-propietaria-lightgrey)

> **En una frase:** SprintScribe lee la transcripción de una reunión de refinamiento, *sprint
> planning* o seguimiento y entrega, listo para revisar, (1) las **tareas** para Azure Boards, bien
> escritas y con responsable, y (2) la **documentación de cada proyecto**: objetivo del sprint, hoja
> de ruta, acuerdos y registro de cambios de decisión. Entiende lo que *finalmente* se decidió
> —aunque en el minuto 12 se haya cancelado algo dicho en el minuto 0— y **no sube nada a Azure
> Boards sin que tú lo autorices**.

**Cómo leer este documento.** Si solo quieres entender qué es y para qué sirve, lee las secciones 1 a
5. Si quieres ver un resultado real, ve a la 7. Si vas a instalarlo y usarlo, ve a la 8, la 9 y la
10. La referencia técnica (comandos, configuración, modos de Azure Boards) está en las secciones 10
a 13. Las palabras técnicas se explican en el [glosario](#18-glosario).

## Tabla de contenido

1. [¿Qué es SprintScribe?](#1-qué-es-sprintscribe)
2. [El problema que resuelve](#2-el-problema-que-resuelve)
3. [¿Para quién es?](#3-para-quién-es)
4. [Qué entrega](#4-qué-entrega)
5. [Qué hace y qué no hace](#5-qué-hace-y-qué-no-hace)
6. [Cómo funciona](#6-cómo-funciona)
7. [Ejemplo de principio a fin](#7-ejemplo-de-principio-a-fin)
8. [Requisitos](#8-requisitos)
9. [Instalación](#9-instalación)
10. [Configuración](#10-configuración)
11. [Cómo usarlo](#11-cómo-usarlo)
12. [Salidas y estructura de carpetas](#12-salidas-y-estructura-de-carpetas)
13. [Modos Draft y Sync, y Azure Boards](#13-modos-draft-y-sync-y-azure-boards)
14. [Pruebas y calidad](#14-pruebas-y-calidad)
15. [Estado y pendientes](#15-estado-y-pendientes)
16. [Preguntas frecuentes](#16-preguntas-frecuentes)
17. [Solución de problemas](#17-solución-de-problemas)
18. [Glosario](#18-glosario)
19. [Estructura del repositorio](#19-estructura-del-repositorio)
20. [Versionado, autoría y licencia](#20-versionado-autoría-y-licencia)

---

## 1. ¿Qué es SprintScribe?

Después de una reunión de equipo alguien tiene que releer la conversación, decidir qué tareas
quedaron realmente acordadas, escribirlas bien (con responsable, esfuerzo y criterio de
aceptación), cargarlas en Azure Boards y dejar documentado el objetivo y los acuerdos. SprintScribe
hace ese trabajo por ti a partir de la **transcripción** de la reunión.

Piensa en un **secretario o secretaria de reuniones muy atento**: escucha la reunión completa antes
de escribir nada, se da cuenta de que algo que se dijo al principio se corrigió al final, separa lo
que *se acordó* de lo que solo *se comentó* y deja constancia de cada cambio de decisión. Además,
tiene la disciplina de un auditor: antes de dar nada por bueno, un programa lo verifica.

SprintScribe se compone de **tres piezas** que se complementan:

| Pieza | Qué es | Dónde está | ¿Usa IA? |
|---|---|---|---|
| **La skill** (el conocimiento) | Reglas escritas: cómo interpretar una conversación, cómo reconciliar decisiones que cambian, cómo redactar una buena tarea, cómo armar los documentos, cómo tratar Azure Boards | `skills/sprintscribe/` (`SKILL.md`, `references/`, `assets/`) | Sí: la lee el asistente |
| **El agente orquestador** (el director de orquesta) | Un agente de GitHub Copilot que ejecuta el flujo completo en orden y aplica las compuertas de seguridad | `adapters/copilot/agents/sprintscribe.agent.md` | Sí |
| **La CLI** (el verificador) | Un programa Python que valida el trabajo del modelo, planifica las operaciones contra Azure Boards, genera los documentos y lleva el historial | `skills/sprintscribe/scripts/sprintscribe.py` | No: con la misma entrada siempre da la misma salida |

**El modelo solo escribe un archivo:** `meeting-state.json`, un JSON con un esquema estricto que
describe el estado final de la reunión. Todo lo demás —validar, deduplicar, renderizar los
documentos, llevar el historial— lo hace código reproducible y probado. Por eso las tareas, los
acuerdos y la hoja de ruta no pueden contradecirse entre sí: los tres salen del mismo archivo.

> **No es un resumidor.** Un resumen cuenta lo que se dijo. SprintScribe reconstruye **lo que se
> decidió**: si en el minuto 12 el PO cancela una tarea mencionada en el minuto 0 y la reemplaza por
> otra, la tarea original no se sube, la nueva sí, y el cambio queda trazado. Hace lo mismo entre
> reuniones.

## 2. El problema que resuelve

| Sin SprintScribe | Con SprintScribe |
|---|---|
| Alguien relee la transcripción y arma las tareas a mano | El agente lee la reunión **completa** y propone todas las tareas |
| Una tarea se cancela o cambia a mitad de la reunión y la versión vieja se sube igual | **Prevalece la corrección posterior explícita**; la tarea descartada queda en el historial y no se sube |
| Las tareas salen con títulos vagos ("revisar tema") y sin criterio de aceptación | Cada tarea tiene un título accionable, una descripción autosuficiente y **exactamente un** criterio de aceptación verificable (la CLI rechaza lo genérico) |
| Se asigna responsable por costumbre o se inventa | El responsable sale de lo dicho en la reunión; si nadie lo tomó queda **vacío y se pregunta** |
| Una idea ("¿y si…?") se convierte en tarea sin que nadie la aprobara | **Una idea no es un compromiso**: las propuestas se retienen y no se suben |
| Se crean duplicados en Azure Boards | Compara contra un *snapshot* de Boards y, si la tarea ya existe, propone actualizar en lugar de crear |
| La documentación del proyecto no se escribe, o contradice a las tareas | Cuatro documentos por proyecto generados desde un único estado, coherentes entre sí |
| Entre una reunión y la siguiente se pierde el hilo | Un **historial acumulado por proyecto** conserva IDs y estados de una reunión a la siguiente |
| Un script sube cosas a Boards sin que nadie lo revise | **Draft por defecto**: nada se escribe en Azure Boards sin tu autorización explícita en el chat |

## 3. ¿Para quién es?

| Rol | Qué obtiene |
|---|---|
| **Product Owner / líder de producto** | Las decisiones de la reunión convertidas en trabajo ejecutable, con el rastro de qué cambió y por qué |
| **Facilitador o Scrum Master** | Documentación por proyecto sin escribir actas a mano |
| **Quien ejecuta las tareas** | Tareas autosuficientes: se entienden sin releer la reunión, con un criterio de aceptación claro |
| **Gerencia** | Objetivo del sprint y hoja de ruta por proyecto, separando lo acordado de lo recomendado |
| **Equipo de TI que lo instala** | Una skill portable, una CLI sin dependencias externas y un instalador por usuario o por workspace |

## 4. Qué entrega

Por cada reunión y por cada proyecto que se haya tratado en ella:

| Entregable | Archivo | Qué contiene |
|---|---|---|
| **Tareas para Azure Boards** (el primer entregable) | `01-azure-boards-tasks.md` | Resumen, tareas listas, tareas que todavía no deben subirse, tareas descartadas o sustituidas (se conservan como historial) y el plan de operaciones |
| **Objetivo del sprint y hoja de ruta** | `02-sprint-objective-and-roadmap.md` | El objetivo principal, resultado esperado, necesidad de negocio, entregables, alcance y exclusiones; y una hoja de ruta ordenada por dependencias con duraciones inferidas, separando lo **acordado** de lo **recomendado** |
| **Acuerdos, decisiones y pendientes** | `03-agreements-and-decisions.md` | Decisiones confirmadas, cambios respecto de acuerdos anteriores, responsabilidades, compromisos y dependencias, bloqueos y riesgos, pendientes de validación del PO, acciones externas, dudas abiertas y contradicciones |
| **Registro de reconciliación** | `04-reconciliation-log.md` | Qué decisión de la conversación provocó el estado final de cada tarea (sustituida, modificada, reasignada, diferida…) |
| **Estado de la reunión** | `meeting-state.json` | La fuente única de la que salen los cuatro documentos anteriores |
| **Historial del proyecto** | `_state/project-state.json` | El *ledger*: estado acumulado de las tareas del proyecto entre reuniones |
| **Tareas para el Excel o el uploader** | `tasks.csv` (comando `export`) | Las tareas listas en formato tabular |

**Qué lleva cada tarea:** un título accionable (de 5 a 12 palabras, empieza con verbo), una
descripción autosuficiente (el porqué, el objetivo, el trabajo a realizar, el contexto y las
dependencias), **exactamente un** criterio de aceptación verificable, responsable, prioridad (solo si
se mencionó), esfuerzo inferido (rango temporal, nivel, confianza y fundamento) y la **evidencia**: la
cita de la reunión que la respalda, con quién la dijo y cuándo.

## 5. Qué hace y qué no hace

**Lo que hace**

- Lee la transcripción **completa** antes de extraer nada.
- Distingue **compromisos, acuerdos, propuestas, dudas, exploraciones y descartes**.
- Reconstruye el **estado final** de cada tarea y deja el **rastro** de cómo se llegó a él.
- Separa la reunión **por proyecto** (una reunión puede tratar varios).
- Reconcilia **entre reuniones**: reutiliza IDs, continúa la numeración y no cambia lo que la nueva
  reunión no menciona.
- Escribe tareas de calidad y valida automáticamente que lo sean.
- Genera los cuatro documentos por proyecto y el historial acumulado.
- Planifica las operaciones contra Azure Boards (crear, actualizar, cambiar estado, enlazar) **sin
  ejecutarlas**, y detecta duplicados.

**Lo que NO hace (garantías)**

- **No escribe en Azure Boards por defecto.** El modo normal es *Draft*: genera todo y deja un plan
  de operaciones pendiente. Escribir exige tres condiciones a la vez (ver [sección 13](#13-modos-draft-y-sync-y-azure-boards)).
- **La transcripción no autoriza nada.** Si en la reunión alguien dice "que quede hoy en Boards",
  eso no es una autorización: la autorización la das tú, en el chat, después de ver el resumen.
- **Nunca borra un work item.** Cancelar es cambiar de estado.
- **No toca un work item cuya identidad no esté verificada.** Una coincidencia solo por título va a
  revisión.
- **No inventa:** ni responsables, ni fechas, ni IDs de work items, ni Story Points, ni sistemas,
  ni objetivos de negocio. Si falta un dato, queda vacío con certeza `pending`.
- **No atribuye palabras ni responsabilidades** a un hablante identificado con baja confianza.
- **No guarda credenciales** en ningún archivo.
- **No sube nada por el uploader del equipo todavía:** esa parte espera la versión real del programa
  (ver [sección 15](#15-estado-y-pendientes)).

## 6. Cómo funciona

### 6.1 La arquitectura

```text
 transcripción ──┐
 configuración ──┼─► Agente de Copilot ─► aplica la skill ─► meeting-state.json ─► CLI sprintscribe.py
 historial       │   (orquesta y vigila     (el conocimiento)   (única salida del      validate · ops-plan
 snapshot Boards ┘    las compuertas)                            modelo)               render · merge · export
                                                                                              │
                              documentos 01–04 por proyecto  ◄────────────────────────────────┤
                              historial acumulado del proyecto  ◄─────────────────────────────┤
                              tasks.csv para el Excel o el uploader  ◄────────────────────────┘
```

**Por qué esta arquitectura** (investigación de octubre de 2026):

- **GitHub Copilot admite *Agent Skills*** (el estándar abierto agentskills.io: un `SKILL.md` más
  `scripts/`, `references/` y `assets/`) en VS Code, en la CLI de Copilot y en el *coding agent*.
  También admite *agentes personalizados* (`*.agent.md`) con herramientas restringidas, terminal,
  MCP y *handoffs*. El conocimiento vive en la skill, así que se reutiliza en cualquier cliente
  compatible; el agente solo orquesta y aplica las compuertas.
- **Un agente no puede declarar skills:** las skills se descubren solas. Por eso el agente se instala
  con las rutas absolutas (o relativas) de la skill y de la CLI ya resueltas.
- **La lógica verificable no depende del modelo.** Validar, deduplicar, renderizar y llevar el
  historial lo hace un script, de forma reproducible y probada.
- **Azure Boards se toca solo con herramientas reales**: el Azure DevOps MCP Server oficial
  (`microsoft/azure-devops-mcp`), en solo lectura por defecto, o el uploader Python del equipo
  (pendiente de configurar). Sin canal no hay escritura: el modo es Draft.
- **Databricks Genie Code** también admite Agent Skills; la misma carpeta `skills/sprintscribe`
  sirve allí en modo Draft. Esta entrega está enfocada en GitHub Copilot.

### 6.2 El flujo en ocho fases

El agente sigue estas fases **en orden** y muestra su avance con una lista de tareas. No escribe tareas
definitivas antes de terminar la fase 3.

| Fase | Nombre | Qué pasa, en palabras simples | Comando de la CLI |
|---|---|---|---|
| 1 | **Inspeccionar** | Averigua la configuración efectiva (PO, equipo, proyectos), dónde se guardan los documentos, qué historial hay de reuniones previas y qué IDs siguen libres. Declara qué conexiones existen de verdad | `context` |
| 2 | **Comprender** | Lee **toda** la transcripción: participantes y roles, proyectos, necesidades de negocio, quién propone, quién decide y quién ejecuta, dependencias y referencias cruzadas | — |
| 3 | **Reconciliar** | Construye el estado **final** de cada tarea y acuerdo: las correcciones posteriores prevalecen, las tareas descartadas se conservan, las contradicciones sin resolver se registran | — |
| 4 | **Generar tareas** | Escribe cada tarea confirmada con título, descripción, un criterio de aceptación, responsable, esfuerzo y evidencia | — |
| 5 | **Objetivo y hoja de ruta** | Infiere el objetivo del sprint de cada proyecto y ordena los pasos por dependencias, separando lo acordado de lo recomendado | — |
| 6 | **Acuerdos** | Registra decisiones, cambios, responsabilidades, compromisos, bloqueos, riesgos y las pocas dudas que impiden ejecutar | — |
| 7 | **Validar y documentar** | Guarda el estado, lo valida hasta obtener **cero errores**, planifica las operaciones de Boards, genera los documentos y actualiza el historial | `validate`, `ops-plan`, `render`, `merge`, `export` |
| 8 | **Sincronizar** | Solo si está autorizado: aplica las operaciones inequívocas en Azure Boards y registra el resultado real de cada una | — (canal autorizado) |

### 6.3 Las diez reglas que no se negocian

Están escritas en el `SKILL.md` que lee el asistente:

1. **Toda la conversación antes que cualquier frase.** Nunca se genera una tarea a partir de una frase
   sin revisar el contexto posterior.
2. **La corrección explícita posterior prevalece** cuando se refiere claramente a la misma tarea o
   decisión. Si no queda claro, se registra una contradicción.
3. **Una idea no es un compromiso.** Las preguntas, los "tal vez" y los "habría que ver" quedan como
   propuestas o dudas, nunca como confirmadas.
4. **No se inventa.** Responsables, fechas, sistemas, tablas, campos, Story Points, IDs y objetivos
   de negocio: si faltan, quedan vacíos.
5. **No se atribuyen palabras ni responsabilidades** a un hablante identificado con baja confianza.
6. **El PO es Brian,** o quien indique `po` en la configuración. Su rol pesa al interpretar, pero no todo
   lo que dice es una decisión ni todo el trabajo es suyo.
7. **Separación por proyecto.** Cada tarea pertenece a un proyecto o queda pendiente de asignar.
   Nunca se mezclan proyectos en un documento genérico.
8. **Hechos frente a inferencias.** Cada tarea, objetivo y decisión lleva su certeza: `explicit`,
   `inferred`, `recommended` o `pending`.
9. **Nada destructivo en Boards.** Una cancelación es un cambio de estado, nunca un borrado.
10. **Pocas preguntas.** Entrega la mejor propuesta posible y, al final, solo las ambigüedades que
    impiden ejecutar parte del trabajo.

### 6.4 Cómo interpreta lo que se dice

Cada afirmación de la conversación se clasifica así (detalle en
[interpretation.md](skills/sprintscribe/references/interpretation.md)):

| Clase | Señales típicas | Cómo se registra |
|---|---|---|
| **Compromiso** | "me comprometo", "lo dejo listo el viernes", "va", "yo lo hago" | Tarea confirmada y decisión de compromiso |
| **Acuerdo o decisión** | Instrucción del PO, consenso explícito, "queda así" | Tarea confirmada y decisión |
| **Propuesta** | "podríamos", "propongo", "¿y si…?" | Tarea propuesta (no se sube) |
| **Duda** | Preguntas sin respuesta | Pregunta abierta, solo si bloquea trabajo |
| **Exploración** | "tal vez", "habría que ver", "lo vemos otro día" | Tarea propuesta o decisión pendiente de validación del PO |
| **Descarte** | "ya no va", "olvídalo", "eso no" | Tarea cancelada más una entrada en el registro de reconciliación |
| **Información** | Contexto, estado actual | Se usa en descripciones; no genera elementos |

Tres campos distintos en cada tarea y decisión: **quién propuso** (`proposed_by`), **quién decidió**
(`decided_by`) y **quién ejecutará** (`owner`). Que el PO explique una tarea no lo convierte en su
responsable. Una tarea tiene **un solo responsable**, porque Azure Boards acepta una única identidad
en *Assigned To*.

Los **errores de reconocimiento de voz** son normales ("data leik" por "Data Lake", "Brayan" por
"Brian"): se corrigen cuando un alias de la configuración o el contexto lo respalda, y no se inventan
nombres desconocidos.

### 6.5 Los estados de una tarea

| Estado | Significado | ¿Va a Boards? |
|---|---|---|
| `proposed` | Idea o propuesta sin confirmar | No (se retiene) |
| `confirmed` | Acordada | Sí |
| `modified` | Acordada y cambiada después en la conversación; el contenido ya es el vigente | Sí |
| `blocked` | Acordada, pero con un bloqueo identificado | Sí, con el bloqueo indicado |
| `deferred` | Pospuesta | No; si ya existe, se propone cambiarle el estado |
| `needs_clarification` | No se puede ejecutar sin una respuesta | No |
| `cancelled` | Descartada o sustituida | No; si ya existe, se propone un cambio de estado |
| `completed` | Hay evidencia de que el trabajo terminó | Si ya existe, se propone cerrarla |

### 6.6 Cómo reconcilia las decisiones que cambian

El algoritmo (detalle en [reconciliation.md](skills/sprintscribe/references/reconciliation.md)):
primero hace un **inventario** de cada mención de trabajo con su marca de tiempo; agrupa las
menciones que hablan del mismo objetivo y mismo entregable; las ordena cronológicamente y aplica las
transiciones; el **último cambio explícito** que se refiere claramente a una tarea determina su
estado y su contenido vigentes; y finalmente verifica que ninguna tarea cancelada aparezca en la
hoja de ruta ni como dependencia de una tarea activa.

| Situación | Señal | Resultado |
|---|---|---|
| **Nueva** | Trabajo no mencionado antes | Tarea nueva |
| **Modificación** | Mismo objetivo, cambia el cómo, el cuándo o el alcance ("que sea cada hora") | La misma tarea, ahora `modified`, con el contenido vigente |
| **Reasignación** | Mismo trabajo, otra persona | La misma tarea con nuevo responsable |
| **División** | Un trabajo pasa a ser dos o más entregables | Las nuevas tareas indican de cuál nacieron |
| **Combinación** | Dos trabajos pasan a ser uno | Las absorbidas quedan canceladas y apuntan a la resultante |
| **Sustitución** | "En lugar de X, hagamos Y" | X cancelada con "sustituida por Y"; Y indica que sustituye a X |
| **Diferimiento** | "Pasa al siguiente sprint" | Tarea diferida |
| **Finalización** | "Ya quedó", con evidencia | Tarea completada |

Ante dos instrucciones contradictorias sin resolución, **no elige un ganador**: registra una
contradicción y deja la tarea en `needs_clarification`.

**Entre reuniones.** Con el historial del proyecto (lo muestra `context`): se reutiliza el ID de una
tarea ya existente, se aplican las transiciones sobre su último estado conocido, solo se incluyen en
el estado nuevo las tareas que la reunión menciona o afecta (`merge` conserva el resto sin cambios) y
**la ausencia de información no es una decisión**: una tarea previa que no se menciona no cambia.

### 6.7 Qué comprueba `validate`

`validate` comprueba el esquema y las reglas de negocio y termina con código `1` si hay errores. Entre
otras cosas **rechaza**:

- IDs duplicados, referencias a tareas, proyectos o decisiones inexistentes, y prefijos de ID que no
  coinciden con la clave del proyecto.
- **Títulos genéricos** o de menos de 3 palabras ("revisar tema", "hacer ajustes").
- Tareas listas sin descripción, **sin criterio de aceptación o con más de uno** (listas, varias
  líneas, varios escenarios), o sin estimación de esfuerzo.
- Esfuerzo en **Story Points sin convención** del equipo, o un rango sin unidad temporal.
- Una tarea que **depende de una descartada**, o inconsistencias en la sustitución (la sustituida no
  está cancelada, no se indican mutuamente) y tareas descartadas sin explicación en el registro de
  reconciliación.
- Tareas confirmadas pese a una **contradicción bloqueante** sin resolver.
- Proyectos con tareas listas pero sin objetivo de sprint; un objetivo que repite el título de una
  tarea; entregables que corresponden a tareas descartadas; hoja de ruta con pasos de igual orden, con
  tareas descartadas o con dependencias a pasos inexistentes o posteriores.
- Operaciones de Boards marcadas como aplicadas **sin la respuesta real de la herramienta** o en
  modo Draft.

Además emite **avisos** (no bloquean): descripción muy breve, responsable fuera del equipo,
responsable con certeza pendiente, títulos casi iguales entre tareas, demasiadas preguntas abiertas o
una hoja de ruta ausente.

## 7. Ejemplo de principio a fin

Las salidas de esta sección son **reales**: se obtuvieron ejecutando la CLI sobre el ejemplo que trae
este repositorio, con la configuración de prueba [`tests/fixtures/config.json`](tests/fixtures/config.json)
(tres proyectos, un equipo de seis personas). Se abrevian las rutas largas.

### 7.1 La reunión

Transcripción: [`skills/sprintscribe/assets/examples/example-transcript.md`](skills/sprintscribe/assets/examples/example-transcript.md)

```text
# Refinamiento Portal de Clientes · 2026-10-09

[00:00] Brian: Para este sprint del portal necesitamos que Ana desarrolle la recuperación de contraseña
        por correo, que Carlos migre el formulario de registro a la nueva librería de componentes, y
        que Ana también se encargue de la auditoría de inicios de sesión.
[00:35] Ana: Ok, las dos mías las hago en ese orden.
[03:10] María: Ayer soporte reportó clientes con dos cuentas. Se registraron una vez con mayúsculas en
        el correo y otra en minúsculas.
[03:40] Brian: Eso es grave, los pedidos quedan repartidos entre cuentas.
[12:05] Brian: Carlos, la migración del formulario de registro ya no la vamos a hacer. En su lugar
        necesitamos una tarea para resolver el problema de las cuentas duplicadas que acabamos de comentar.
[12:30] Carlos: Va. Normalizo el correo al registrarse y reviso cómo detectar las cuentas que ya están duplicadas.
[12:50] Brian: Perfecto, la migración la retomamos cuando haya espacio.
```

(En el archivo original cada intervención ocupa una sola línea; aquí se partieron para que quepan.)

Fíjate en lo que ocurre: en el minuto 0 se mencionan tres tareas, y en el minuto 12 el PO **cancela
una y la sustituye por otra** a partir de un problema comentado en el minuto 3. Un resumen listaría
las tres originales. SprintScribe no.

### 7.2 El trabajo del agente

El agente (guiado por la skill) lee la reunión completa y escribe `meeting-state.json`. Ese archivo es
lo único que produce el modelo. El repositorio incluye el resultado de referencia
([`example-meeting-state.json`](skills/sprintscribe/assets/examples/example-meeting-state.json)), así
que puedes recorrer **la parte determinista** sin IA:

```bash
CLI=skills/sprintscribe/scripts/sprintscribe.py
ESTADO=skills/sprintscribe/assets/examples/example-meeting-state.json
```

**1. Validar** (cero errores o no se sigue):

```bash
python3 $CLI --config tests/fixtures/config.json validate $ESTADO
```

```text
OK · 1 proyectos · 4 tareas (3 listas, 1 descartadas) · 3 decisiones · sin responsable: —
```

**2. Planificar las operaciones contra Azure Boards** (sin escribir nada):

```bash
python3 $CLI --config tests/fixtures/config.json ops-plan $ESTADO --dry-run
```

```text
Crear         PCL-T1     -        pending       Tarea nueva confirmada (sin snapshot de Boards: verificar duplicados al sincronizar)
Omitir        PCL-T2     -        pending       No hay work item asociado; no hay nada que sincronizar
Crear         PCL-T3     -        pending       Tarea nueva confirmada (sin snapshot de Boards: verificar duplicados al sincronizar)
Enlazar       PCL-T3     -        pending       Dependencia de PCL-T3 sobre PCL-T1
Crear         PCL-T4     -        pending       Tarea nueva confirmada (sin snapshot de Boards: verificar duplicados al sincronizar)
Sin snapshot de Azure Boards: la deduplicacion contra Boards queda pendiente.
```

Observa que **PCL-T2 (la migración cancelada) no se crea**: "no hay nada que sincronizar".

**3. Generar los documentos, actualizar el historial y exportar:**

```bash
python3 $CLI --config tests/fixtures/config.json render $ESTADO --out salida
python3 $CLI --config tests/fixtures/config.json merge  $ESTADO --docs-root salida
python3 $CLI --config tests/fixtures/config.json export $ESTADO --format csv --out salida/tasks.csv
```

```text
Escrito: salida/portal-clientes/2026-10-09
Escrito: salida/tasks.csv (3 tareas)
```

### 7.3 Lo que se obtiene

**`01-azure-boards-tasks.md`** (extracto):

```markdown
**Resumen:** Cancelada o descartada: 1 · Confirmada: 3

| ID | Título | Responsable | Esfuerzo | Estado |
|---|---|---|---|---|
| PCL-T1 | Implementar recuperación de contraseña por correo | Ana | 2-3 d | Confirmada |
| PCL-T3 | Registrar auditoría de inicios de sesión del portal | Ana | 1-2 d | Confirmada |
| PCL-T4 | Evitar cuentas duplicadas normalizando el correo en el registro | Carlos | 2-3 d | Confirmada |

### PCL-T4 · Evitar cuentas duplicadas normalizando el correo en el registro

Responsable: Carlos (inferido con respaldo contextual) · Propuesta por / decidida por: Brian / Brian

**Descripción**
Soporte reportó clientes con dos cuentas porque se registraron con el mismo correo escrito con
mayúsculas y minúsculas, lo que reparte sus pedidos entre cuentas. Se normaliza el correo al
registrarse para impedir nuevas duplicadas y se identifican las cuentas que ya están duplicadas.
Sustituye a la migración del formulario de registro (PCL-T2).

**Criterio de aceptación**
Registrar un correo que ya existe con distinta combinación de mayúsculas es rechazado y existe un
listado de las cuentas ya duplicadas por esta causa.

**Esfuerzo inferido:** 2-3 d · esfuerzo medio · confianza baja. Normalizar es acotado; identificar las
duplicadas depende de la calidad de los datos actuales.

**Sustento en la reunión:** [12:05] Brian: “En su lugar necesitamos una tarea para resolver el problema
de las cuentas duplicadas” · [12:30] Carlos: “Normalizo el correo al registrarse y reviso cómo detectar…”

## Descartadas o sustituidas (se conservan como historial)
- **PCL-T2** · Migrar el formulario de registro a la nueva librería de componentes · Cancelada o
  descartada → sustituida por PCL-T4. Motivo: Brian canceló la migración para priorizar las cuentas duplicadas.
```

Fíjate en tres cosas: la descripción de PCL-T4 **reconstruye el problema** que se comentó en el
minuto 3 aunque la instrucción llegó en el minuto 12; el responsable (Carlos) está marcado como
*inferido* porque la instrucción se dirigía a él pero no la aceptó por su nombre; y la tarea
sustituida **no desaparece**: queda en el historial con su motivo.

**`02-sprint-objective-and-roadmap.md`** (extracto):

```markdown
## Objetivo principal
Lograr un acceso confiable al Portal de Clientes, mediante la recuperación de contraseña, la
auditoría de inicios de sesión y la prevención de cuentas duplicadas, con el fin de que cada cliente
tenga una sola cuenta segura con sus pedidos.

## Hoja de ruta
| # | Paso | Tipo | Responsable | Tareas | Depende de | Duración inferida |
|---|---|---|---|---|---|---|
| 1 | Prevenir cuentas duplicadas | Acordado | Carlos | PCL-T4 | — | 2-4 d |
| 2 | Recuperación de contraseña | Acordado | Ana | PCL-T1 | — | 2-3 d |
| 3 | Auditoría de inicios de sesión | Acordado | Ana | PCL-T3 | 2 | 1-2 d |
| 4 | Plan de fusión de cuentas ya duplicadas | *Recomendado* | Carlos | — | 1 | 1-2 d |
```

El paso 4 está marcado como **recomendado**: lo sugiere SprintScribe porque Carlos mencionó revisar
las cuentas duplicadas pero nadie acordó cómo fusionarlas. Un paso recomendado **nunca es un
compromiso**; el documento de acuerdos lo deja como pendiente de validación del PO.

**`04-reconciliation-log.md`:**

```markdown
| # | Acción | Tarea | De → A | Motivo | Decisión |
|---|---|---|---|---|---|
| R1 | Sustituida | PCL-T2 · Migrar el formulario de registro a la nueva librería de componentes | confirmada → cancelada o descartada | Brian canceló la migración para priorizar las cuentas duplicadas. | D1 |
| R2 | Añadida | PCL-T4 · Evitar cuentas duplicadas normalizando el correo en el registro | — → confirmada | Nueva tarea que sustituye a PCL-T2 para resolver las cuentas duplicadas. | D1 |
```

**`tasks.csv`** (columnas): `id, project_id, project_name, title, description, acceptance_criterion,
work_item_type, owner, priority, effort_range, effort_level, effort_confidence, use_case, epic,
feature, story, sprint, depends_on, status, work_item_id`. Solo salen las tareas **listas** (aquí,
3 de 4; `--all` incluye las no listas). Los campos de jerarquía (`use_case`, `epic`, `feature`,
`story`) y `sprint` se llenan como pistas de texto cuando la reunión los nombra.

**El historial** (`merge` + `context`): el proyecto queda con `next_task_id_number: 5`, las tareas
abiertas `PCL-T1`, `PCL-T3` y `PCL-T4`, y `PCL-T2` en la lista de cerradas. La próxima reunión
continuará la numeración desde `PCL-T5`.

### 7.4 Una segunda reunión: sin duplicados

Una semana después, la reunión de seguimiento dice (caso de prueba 11, extracto):

```text
[00:00] Brian: La recuperación de contraseña ya está en Boards, la 4512. Ana sigue con eso.
[00:20] Brian: Carlos, agrega el captcha al formulario de inicio de sesión; hubo intentos de fuerza bruta.
[01:00] Brian: Lo de migrar el formulario de registro ya no va, como dijimos.
[01:20] Brian: Ana, después registra las métricas de errores del login en el tablero de monitoreo.
```

Con un *snapshot* de los work items existentes en Boards (que el agente obtiene en solo lectura),
`ops-plan` decide qué hacer **sin crear duplicados**:

```text
Sin cambios   PCL-T1     #4512    pending       El work item ya refleja la tarea
Revisar       PCL-T2     -        needs_review  Tarea cancelada o descartada que podria existir en Boards por similitud de titulo; confirmar identidad antes de cambiar su estado
Actualizar    PCL-T5     #4530    needs_review  Ya existe en Boards (similitud 0.92): no se crea duplicado; confirmar la identidad antes de actualizar
Crear         PCL-T6     -        pending       Tarea nueva confirmada
Enlazar       PCL-T6     -        pending       Dependencia de PCL-T6 sobre PCL-T1
```

El work item 4512 ya refleja lo que se dijo (**sin cambios**); la tarea del captcha ya existe en
Boards con un título casi idéntico (el 4530, similitud 0,92) y se manda a **revisión** en vez de
duplicarse; para la migración cancelada hay un work item parecido (el 4513), pero nadie dio su ID en
la reunión, así que **no se toca** mientras su identidad no esté verificada; y solo la tarea
realmente nueva (las métricas del login) se propone **crear**.

## 8. Requisitos

| Requisito | Detalle | ¿Obligatorio? |
|---|---|---|
| **Python 3.9 o superior** | La CLI usa solo la biblioteca estándar: no hace falta instalar paquetes | Sí |
| **VS Code con GitHub Copilot en modo agente** (o la CLI de Copilot) | Para usar el agente. Necesita permiso para **ejecutar comandos en la terminal** | Sí, para el flujo con agente |
| **Azure DevOps MCP Server** | Para leer Azure Boards (deduplicar, localizar work items). Requiere que la organización habilite la política *MCP servers in Copilot* y que la organización de Azure DevOps esté respaldada por **Microsoft Entra ID** (las organizaciones con cuentas Microsoft personales no se soportan en el servidor remoto) | Opcional |
| **Git** | Recomendado para versionar la carpeta `documentacion/` | Opcional |

La CLI funciona sola, sin Copilot: sirve para validar, renderizar y exportar un `meeting-state.json`
que hayas obtenido de cualquier forma.

## 9. Instalación

Hay dos modalidades que se pueden combinar. Primero obtén este repositorio:

```bash
git clone https://github.com/luisdgo2000/sprintscribe.git
cd sprintscribe
```

### 9.1 Por workspace (recomendada para equipos)

Se instala dentro del repositorio donde el equipo guarda su documentación, y se versiona con él. Las
rutas son relativas, así que funciona en cualquier equipo que clone ese repositorio.

```bash
python3 install.py --scope workspace --target /ruta/al/repo-de-documentacion --with-mcp --dry-run
```

`--dry-run` **solo muestra lo que haría**. Salida real:

```text
[simulacion] SprintScribe v0.1.0 · scope workspace
 - Instalar skill -> /ruta/al/repo-de-documentacion/.github/skills/sprintscribe
 - Instalar agente -> /ruta/al/repo-de-documentacion/.github/agents/sprintscribe.agent.md (CLI: python3 .github/skills/sprintscribe/scripts/sprintscribe.py)
 - Instalar prompt -> /ruta/al/repo-de-documentacion/.github/prompts/procesar-reunion.prompt.md
 - Crear configuracion -> /ruta/al/repo-de-documentacion/.sprintscribe/config.json (editala con tu equipo, proyectos y Boards)
 - Agregar MCP de Azure DevOps (solo lectura) -> /ruta/al/repo-de-documentacion/.vscode/mcp.json
```

Si te parece bien, ejecuta el mismo comando **sin** `--dry-run`. Instala `.github/skills/`,
`.github/agents/`, `.github/prompts/`, `.sprintscribe/config.json` y, si lo pediste con `--with-mcp`,
`.vscode/mcp.json` en solo lectura.

> `.sprintscribe/config.json` contiene los nombres (y opcionalmente correos) de tu equipo, nunca
> credenciales. Decide si lo versionas con el repositorio.

### 9.2 Por usuario

Disponible en todos tus workspaces de este equipo:

```bash
python3 install.py --scope user
```

Instala:

- `~/.copilot/skills/sprintscribe/`;
- `~/.copilot/agents/sprintscribe.agent.md`, con la ruta absoluta de la CLI y del Python de este
  equipo;
- `~/.sprintscribe/config.json`, solo si no existe.

La instalación por usuario **no instala el prompt** `/procesar-reunion`, porque VS Code guarda esos
prompts en el perfil del usuario: en ese caso invoca el agente directamente.

### 9.3 Opciones y comportamiento del instalador

| Opción | Para qué sirve |
|---|---|
| `--scope user` / `--scope workspace` | Dónde instalar (obligatoria) |
| `--target <ruta>` | Repositorio destino (con `--scope workspace`) |
| `--with-mcp` | Agrega un `.vscode/mcp.json` de ejemplo con el Azure DevOps MCP en solo lectura |
| `--python <comando>` | Fija el intérprete que usará el agente; por ejemplo `py -3` en Windows |
| `--dry-run` | Muestra las acciones sin escribir nada |
| `--force` | Sobrescribe archivos que no instaló SprintScribe |

- **Reinstalar** actualiza la skill y el agente, y **nunca** sobrescribe tu configuración.
- **Archivos ajenos:** no reemplaza archivos que no instaló SprintScribe (salvo con `--force`).

### 9.4 Después de instalar

1. Edita el `config.json` que creó el instalador (ver [sección 10](#10-configuración)): como mínimo tu
   equipo (`roster`), tu Product Owner (`po`) y tus proyectos (`projects`).
2. Abre Copilot Chat en **modo agente** y elige el agente **sprintscribe** en el selector.
   En VS Code, si el agente no aparece, revisa la [solución de problemas](#17-solución-de-problemas).

## 10. Configuración

La CLI combina estas capas, de **menor a mayor prioridad**:

1. Los valores por defecto.
2. `~/.sprintscribe/config.json` (o `$SPRINTSCRIBE_HOME/config.json`).
3. `.sprintscribe/config.json`: el primero que encuentre subiendo desde la carpeta actual.

`--config <archivo>` reemplaza todas las capas.

**Nunca se guardan credenciales en la configuración.** Los tokens viven en variables de entorno o en
el inicio de sesión del cliente MCP.

### 10.1 Referencia de claves

| Clave | Tipo / valores | Por defecto | Para qué sirve |
|---|---|---|---|
| `config_version` | `"1.0"` | `"1.0"` | Versión del formato de la configuración |
| `language` | texto | `"es"` | Idioma de los documentos |
| `docs_root` | ruta | `"./documentacion"` | Dónde se escriben los documentos. Relativa al archivo de configuración o absoluta; admite `~` |
| `inbox_dir` | ruta | `"_inbox"` | Dónde el agente escribe el `meeting-state.json` de trabajo. Relativa a `docs_root` |
| `po.name`, `po.aliases` | texto, lista | `"Brian"`, `[]` | El Product Owner y sus alias, **incluidos los errores de transcripción** ("Brayan", "Bryan"). **Cámbialo por el PO de tu equipo** |
| `roster[]` | lista de personas | `[]` | Cada persona: `name`, `aliases`, `role`, `upn` (correo de Azure DevOps, opcional) y `team` |
| `projects[]` | lista de proyectos | `[]` | Cada proyecto: `id` (nombre de carpeta), `key` (prefijo de IDs, p. ej. `PCL`), `name`, `aliases`, `description`, `area_path` y `docs` (rutas de documentación existente) |
| `effort_convention.mode` | `ranges` · `hours` · `story_points` | `ranges` | `ranges` infiere rangos temporales (recomendado). `story_points` **solo** si el equipo tiene esa convención documentada |
| `effort_convention.native_field` | texto o `null` | `null` | Campo de esfuerzo de Boards, solo si su significado está identificado |
| `boards.mode` | `draft` · `sync` | `draft` | Draft no escribe en Boards; Sync puede hacerlo (con autorización) |
| `boards.channel` | `none` · `mcp` · `uploader` | `none` | Canal de escritura autorizado cuando `mode = sync` |
| `boards.org`, `.project`, `.team`, `.process` | texto o `null` | `null` | Datos de tu Azure DevOps. `process` (Agile, Scrum, heredado…) en `null` se descubre por metadata |
| `boards.work_item_types` | mapa | `{}` | Tipo lógico → tipo real, p. ej. `{"task": "Task", "story": "User Story"}` |
| `boards.state_mapping` | mapa | `{}` | Estado lógico → estado real de **tu** proceso, p. ej. `{"cancelled": "Removed"}`. Si falta un estado, la operación queda en revisión |
| `boards.dedup` | `same_threshold`, `review_threshold`, `margin` | `0.9`, `0.72`, `0.05` | Umbrales de similitud para detectar duplicados (ver [sección 13](#13-modos-draft-y-sync-y-azure-boards)) |
| `boards.auto_apply` | lista | `[]` | Operaciones inequívocas que el agente puede aplicar en Sync sin pedir confirmación por cada una |
| `uploader.status` | `pending` · `configured` · `disabled` | `pending` | Estado de la integración con el programa Python + Excel del equipo (ver [sección 15](#15-estado-y-pendientes)) |

### 10.2 Primera configuración, paso a paso

Parte del ejemplo [`config/sprintscribe.config.example.json`](config/sprintscribe.config.example.json):

1. **Cambia el PO.** En `po`, pon el nombre de tu Product Owner y sus alias de transcripción.
2. **Llena el equipo** en `roster`: nombre, alias frecuentes mal transcritos, rol y, si vas a sincronizar
   con Boards, el correo de Azure DevOps en `upn`.
3. **Declara tus proyectos** en `projects`: un `id` en minúsculas con guiones (será el nombre de la
   carpeta), una `key` corta en mayúsculas (será el prefijo de los IDs, `PCL-T1`…), el nombre y los
   **alias** con los que la gente nombra al proyecto en las reuniones (incluidos los errores de
   transcripción).
4. **Déjalo en Draft** (`boards.mode = "draft"`) hasta que hayas revisado varias salidas.
5. Cuando vayas a sincronizar, completa `boards.work_item_types` y `boards.state_mapping` con los
   nombres reales de **tu** proceso de Azure Boards.

## 11. Cómo usarlo

### 11.1 Qué necesita SprintScribe

| Insumo | ¿Obligatorio? | Para qué |
|---|---|---|
| **La transcripción** de la reunión | Sí | Es la materia prima. Puede ser un archivo que nombras, un archivo abierto o texto pegado en el chat |
| **La configuración** (equipo y proyectos) | Sí | Para resolver quién es quién y a qué proyecto pertenece cada cosa |
| La documentación de los proyectos (`projects[].docs`) | No | Para resolver referencias y enriquecer descripciones |
| Un *snapshot* de Azure Boards | No | Para detectar duplicados y localizar work items existentes (el agente lo obtiene por MCP en solo lectura, o lo entregas tú exportado) |
| El historial de reuniones previas | Se usa si existe | Lo lee solo, desde `documentacion/<proyecto>/_state/` |

**Formato de la transcripción.** Los casos de prueba usan Markdown con una intervención por línea,
`[mm:ss] Nombre: frase`; es el formato recomendado porque deja a cada frase con su hablante y su marca
de tiempo (que se cita como evidencia). Otro texto plano con hablantes (por ejemplo, una transcripción
de Microsoft Teams copiada o descargada y guardada como texto) debería funcionar porque el agente
interpreta texto libre, pero **esos formatos no están cubiertos por las pruebas** de este repositorio.
Un archivo `.docx` hay que convertirlo antes a texto.

### 11.2 Con el agente (lo habitual)

En Copilot Chat elige el agente **sprintscribe** y escribe, por ejemplo:

> Procesa la reunión de `reuniones/2026-10-09-refinamiento.md`

O usa el prompt `/procesar-reunion` (disponible en la instalación por workspace), que pide la ruta de
la transcripción y notas opcionales, y trabaja siempre en modo Draft.

El agente recorre las fases (inspeccionar, comprender, reconciliar, escribir el estado, validar,
plan de operaciones, render, merge y export) y **responde primero con la tabla de tareas**, después
con los cambios, las rutas de los documentos, el estado de Boards ("Draft: nada se escribió en Azure
Boards" o el resultado real de cada operación) y, como máximo, de tres a cinco ambigüedades que
bloquean trabajo, cada una dirigida a una persona.

El agente ofrece dos **atajos** (*handoffs*) que no se envían solos:

- **Comparar con Azure Boards:** consulta en solo lectura los work items de los proyectos de la última
  reunión, guarda el snapshot y vuelve a ejecutar `ops-plan` con él.
- **Sincronizar con Azure Boards:** pide autorizar la sincronización de las operaciones pendientes
  inequívocas del último plan, mostrando antes el resumen.

### 11.3 Con la CLI directamente

```bash
python3 skills/sprintscribe/scripts/sprintscribe.py --help
python3 skills/sprintscribe/scripts/sprintscribe.py --version
```

| Comando | Para qué sirve | Opciones |
|---|---|---|
| `context` | Muestra la configuración efectiva, los historiales previos y los IDs libres | — |
| `validate <estado>` | Valida el esquema y las reglas de negocio; termina con código `1` si hay errores | `--json` |
| `ops-plan <estado>` | Planifica crear, actualizar, cambiar estado, enlazar o revisar, **sin escribir en Boards** | `--snapshot <archivo>`, `--dry-run` (no guarda el plan en el estado) |
| `render <estado>` | Genera los documentos 01 a 04 por proyecto | `--out <carpeta>` (por defecto `docs_root`), `--force` (renderiza aunque haya errores; solo para depurar) |
| `merge <estado>` | Actualiza el historial acumulado de cada proyecto | `--docs-root <carpeta>`, `--project <id>` |
| `export <estado>` | Exporta las tareas listas para el Excel o el uploader | `--format json\|csv`, `--out <archivo>`, `--all` (incluye las no listas) |
| `check-expectations <estado> <expected.json>` | Califica una salida contra un caso de prueba (para medir al modelo) | — |

Opción global: `--config <archivo>`. Secuencia típica sobre un estado ya escrito:

```bash
python3 skills/sprintscribe/scripts/sprintscribe.py context
python3 skills/sprintscribe/scripts/sprintscribe.py validate documentacion/_inbox/<reunion>/meeting-state.json
python3 skills/sprintscribe/scripts/sprintscribe.py ops-plan documentacion/_inbox/<reunion>/meeting-state.json --snapshot boards.json
python3 skills/sprintscribe/scripts/sprintscribe.py render   documentacion/_inbox/<reunion>/meeting-state.json
python3 skills/sprintscribe/scripts/sprintscribe.py merge    documentacion/_inbox/<reunion>/meeting-state.json
python3 skills/sprintscribe/scripts/sprintscribe.py export   documentacion/_inbox/<reunion>/meeting-state.json --format csv --out tasks.csv
```

### 11.4 Qué es el `meeting-state.json`

Es el estado completo de la reunión, la **única salida del modelo**. Sigue el esquema
[`meeting-state.schema.json`](skills/sprintscribe/assets/schema/meeting-state.schema.json). Sus bloques
principales:

| Bloque | Contenido |
|---|---|
| `meeting` | Identificador, fecha, tipo (por ejemplo, refinamiento), sprint, título, fuente, participantes (con su `identity_confidence`: `high`, `medium` o `low`) |
| `projects[]` | Cada proyecto tratado: cómo se resolvió, objetivo del sprint y hoja de ruta |
| `tasks[]` | Cada tarea con su estado, responsable y su certeza, descripción, criterio de aceptación, esfuerzo, evidencia, historial y relaciones |
| `decisions[]` | Decisiones, cambios, responsabilidades, compromisos, bloqueos, riesgos y acciones externas |
| `contradictions[]` | Afirmaciones incompatibles sin resolver |
| `open_questions[]` | Solo las dudas que impiden ejecutar trabajo |
| `reconciliation_log[]` | El rastro de cada cambio de decisión |
| `ops_plan[]` | Las operaciones planificadas contra Azure Boards (lo agrega `ops-plan`) |

## 12. Salidas y estructura de carpetas

```text
documentacion/
  _inbox/<id-de-la-reunión>/meeting-state.json     estado completo (lo escribe el agente)
  <proyecto>/<fecha>/01-azure-boards-tasks.md       tareas listas, no listas, descartadas y plan de operaciones
  <proyecto>/<fecha>/02-sprint-objective-and-roadmap.md
  <proyecto>/<fecha>/03-agreements-and-decisions.md
  <proyecto>/<fecha>/04-reconciliation-log.md
  <proyecto>/<fecha>/meeting-state.json             estado filtrado del proyecto
  <proyecto>/_state/project-state.json              historial acumulado entre reuniones
  _pendiente-de-asignar/<fecha>/                    tareas cuyo proyecto no se pudo resolver
```

**Reglas de nombres**

- **IDs de tarea:** `<CLAVE>-T<n>`, por ejemplo `PCL-T4`. La clave viene de `projects[].key`. Las tareas
  sin proyecto usan `PEND-T<n>`.
- **Otros IDs:** `D<n>` para decisiones, `R<n>` para reconciliación, `Q<n>` para preguntas y `C<n>`
  para contradicciones.
- **Identificador de la reunión (`meeting.id`):** `<aaaa-mm-dd>-<tipo>-<proyecto-o-tema>`, en
  minúsculas y con guiones.
- **Sin sobrescritura:** la documentación de una reunión nunca sobrescribe la de otra. Si la carpeta
  ya existe se usa el sufijo `-v2`, `-v3`… Volver a renderizar la **misma** reunión actualiza su
  carpeta.
- **Tareas sin proyecto:** si el proyecto no se pudo resolver, la tarea lleva `PENDING`, se agrega una
  pregunta abierta con los proyectos candidatos y `render` la deja en `_pendiente-de-asignar/`.
- **Una tarea compartida entre proyectos** se crea **una sola vez**, en el proyecto principal, y los
  demás se listan como relacionados.

> La carpeta `documentacion/` y `.sprintscribe/` están en el `.gitignore` **de este repositorio** (que
> es el producto), porque contienen salidas reales y configuración local. En el repositorio de
> documentación de tu equipo sí conviene versionar `documentacion/`: con varias personas procesando
> reuniones del mismo proyecto en paralelo, Git evita pisarse los historiales.

## 13. Modos Draft y Sync, y Azure Boards

### 13.1 Los dos modos

| Modo | Condición | Resultado |
|---|---|---|
| **Draft** (por defecto) | No hay canal, o `boards.mode = "draft"`, o no hay autorización | Tareas, documentos y plan de operaciones **pendiente**. **Nada se escribe en Boards** |
| **Sync** | `boards.mode = "sync"`, un canal disponible **y** la confirmación explícita en el chat | Aplica solo las operaciones inequívocas; las ambiguas quedan en revisión; se registra el resultado real de cada una |

Para escribir en Azure Boards deben cumplirse **las tres a la vez**:

1. `context` muestra `boards.mode = "sync"`.
2. Existe el canal configurado (`mcp`, con las herramientas `azure-devops` disponibles).
3. Tú lo pediste **explícitamente en el chat, después de ver el resumen del plan**.

**Garantías del plan de operaciones:**

- **Nunca borra:** cancelar es cambiar de estado, según `state_mapping`.
- **No toca un work item cuya identidad no esté verificada:** una coincidencia por título va a revisión.
- **No crea duplicados:** si la tarea ya existe en el snapshot, propone actualizarla o no hacer nada.
- `validate` rechaza cualquier operación marcada como aplicada en modo Draft o sin la respuesta real
  de la herramienta. **Nunca se reporta como hecha una operación que no se ejecutó.**

### 13.2 Qué propone `ops-plan`

| Situación | Operación |
|---|---|
| Tarea lista sin work item ni candidatas | `create` (pendiente) más `link` por cada dependencia |
| Tarea lista con ID verificado | `update` si hay cambios en título o responsable; si no, `noop` (sin cambios) |
| Tarea lista con una única candidata muy similar | `update` o `noop` en **revisión**: no se crea un duplicado |
| Varias candidatas o una similitud intermedia | `needs_review` con las candidatas |
| Tarea cancelada o completada con ID verificado | `change_state` al estado de `boards.state_mapping`. **Nunca borrar** |
| Tarea cancelada sin ID, pero con candidata | `needs_review`: no se toca un work item por una coincidencia |
| Tarea cancelada que nunca llegó a Boards | `skip` (omitir) |
| Tarea propuesta o pendiente de aclaración | `hold` (retener) |
| Estado destino no configurado en `state_mapping` | `needs_review` |

**Identidad de un work item.** Es *verificada* solo cuando la reunión o el usuario dan el ID, o cuando
lo confirmó una consulta por ID. Una coincidencia por título es solo una *candidata*. Los umbrales de
similitud están en `boards.dedup`: `same_threshold` (0,90 por defecto), `review_threshold` (0,72) y
`margin` (0,05: la distancia mínima entre la mejor candidata y la segunda).

**Mapeo de estados.** Los estados de SprintScribe (`cancelled`, `completed`, `deferred`, `blocked`) son
del análisis de la reunión. Solo se trasladan a Boards por medio de `boards.state_mapping`; un valor
`null` significa "sin equivalente acordado" y la operación queda en revisión.

### 13.3 Canales de escritura

- **`mcp`:** el Azure DevOps MCP Server oficial (`microsoft/azure-devops-mcp`). Para el servidor remoto,
  el ejemplo [`adapters/copilot/mcp.example.json`](adapters/copilot/mcp.example.json) apunta a
  `https://mcp.dev.azure.com/<organización>`, pide el nombre de la organización al iniciar, limita las
  herramientas con `X-MCP-Tools` y arranca en **solo lectura** con `X-MCP-Readonly: true`. Quita ese
  encabezado únicamente si el equipo autoriza Sync por MCP (`boards.mode = "sync"` y
  `boards.channel = "mcp"`). Alternativa local (Node 20+): `npx -y @azure-devops/mcp <org> -d core work work-items search`.
- **`uploader`:** el programa Python y el Excel del equipo. **Pendiente de configurar** (ver sección 15).
- **`none`:** no hay canal. Solo es posible el modo Draft.

## 14. Pruebas y calidad

```bash
python3 -m unittest discover -s tests -v
```

**42 pruebas** que pasan con **Python 3.9 y con Python 3.12** (verificado en octubre de 2026). Cubren:

- Los **12 casos de calidad** (tabla siguiente): cada estado de referencia pasa `validate` y cumple sus
  expectativas.
- Los **rechazos de `validate`**: tarea cancelada en la hoja de ruta o reactivada, varios criterios de
  aceptación, Story Points sin convención, títulos genéricos, contradicciones, operaciones simuladas.
- La **deduplicación** contra Boards.
- El **render determinista** y sin sobrescritura.
- El **historial** entre reuniones.
- La **configuración por capas**.
- El **empaquetado**: la especificación de Agent Skills y la versión.

| # | Caso | Qué verifica |
|---|---|---|
| 01 | Un proyecto, tareas explícitas | Responsables y tareas completas |
| 02 | Varios proyectos | Separación por proyecto, acción externa, contradicción no bloqueante |
| 03 | Modificación al final | La corrección tardía prevalece |
| 04 | Cancelar y sustituir | El ejemplo obligatorio de las tareas 1–4 |
| 05 | Cambio de responsable | Reasignación trazada |
| 06 | Menciones similares | Dos "validar" con objetivos distintos |
| 07 | Sin responsable | No se inventa el owner y se pregunta |
| 08 | Compromisos frente a posibilidades | Las ideas no se suben |
| 09 | Referencias ambiguas y errores de voz | Alias corregido; "lo otro" queda pendiente |
| 10 | Segunda reunión | Diferida, completada y nueva; la tarea no mencionada se conserva |
| 11 | Ya existe en Boards | Sin duplicados; la cancelada sin ID va a revisión |
| 12 | Sin integración | Draft, plan pendiente, nada reportado como sincronizado |

**Estas pruebas miden la capa determinista, no al modelo.** Para evaluar **si el modelo interpreta bien**
las transcripciones, sigue [tests/EVALUATION.md](tests/EVALUATION.md): se instala SprintScribe en un
workspace de prueba, se le pide al agente que procese cada transcripción y se califica su
`meeting-state.json` con `check-expectations` contra el `expected.json` del caso (termina con código
`0` solo si se cumplen todas las expectativas).

## 15. Estado y pendientes

### 15.1 Estado

**v0.1.0, primera versión.** La skill, la CLI, el agente de Copilot, el instalador y las 42 pruebas
están completos. Falta la conexión con el Excel y el uploader del equipo, y probar el flujo con
Azure DevOps real.

### 15.2 Excel y uploader Python del equipo (pendiente)

La idea es que, en Sync, el agente llene el Excel del equipo y opere el programa que sube las tareas.
Hoy es un *stub* (`uploader.status: "pending"`): mientras siga así, el agente se detiene después de
`export` y avisa que el CSV queda listo. Cuando se configure, el flujo (por **nombre de acción**, con
los comandos exactos en la configuración) será:

1. `refresh_metadata` — actualizar en el Excel la pizarra y el sprint más reciente (opción 3 del programa real).
2. **Llenar el Excel** con las tareas exportadas, eligiendo caso de uso, épica, feature, story, esfuerzo
   y sprint **de los catálogos** del Excel.
3. `simulate` — simular la subida e informar si todo está correcto o qué falla (opción 2).
4. **Esperar a que revises y confirmes explícitamente** que quieres subir.
5. `publish` — subir, y registrar los IDs devueltos en el estado (opción 1).

La versión del programa que está en el repositorio `tareas-sprint-azure-boards` (plantilla 2.0) **no
es la que se usa en producción**: tiene otro menú y no incluye los catálogos de caso de uso, épica,
feature y story. Para habilitar este flujo hace falta la versión real:

- la ruta del script y del Excel;
- las opciones del menú o sus *flags* de línea de comandos;
- las hojas, columnas y catálogos del Excel;
- el formato de salida de la simulación.

El contrato ya está preparado: `export` genera las tareas con caso de uso, épica, feature, story,
esfuerzo y sprint como pistas de texto; `config.uploader` recibirá el perfil; y el agente ya describe
el flujo por nombre de acción.

### 15.3 Azure DevOps MCP

Requiere la política de MCP en Copilot y una organización de Azure DevOps respaldada por Entra. Sin
eso, la deduplicación contra Boards se hace con un *snapshot* exportado o queda pendiente.

### 15.4 Limitaciones conocidas

- **La calidad de la interpretación depende del modelo.** La CLI garantiza la estructura y la
  coherencia, pero no puede verificar que una cita sea fiel. `check-expectations` y los casos de prueba
  sirven para medirla.
- **La deduplicación es por similitud de título.** Títulos muy distintos para el mismo trabajo no se
  detectan; por eso todo lo dudoso va a revisión.
- **Los historiales** se guardan por proyecto en archivos JSON. Si varias personas procesan reuniones
  del mismo proyecto en paralelo, conviene versionar `documentacion/` en Git.
- **Tipos y estados de Boards** dependen de tu proceso. Configura `work_item_types` y `state_mapping`;
  mientras falten, las operaciones afectadas quedan en revisión.
- **Formatos de transcripción:** solo el formato Markdown de los ejemplos está cubierto por pruebas.
- **El prompt `/procesar-reunion`** no se instala con `--scope user` (ver sección 9.2).

## 16. Preguntas frecuentes

**¿Sube las tareas a Azure Boards automáticamente?**
No. Por defecto trabaja en modo Draft: genera las tareas, los documentos y un plan de operaciones
pendiente, y no escribe nada en Boards. Sincronizar exige tres condiciones a la vez, incluida tu
autorización explícita en el chat.

**En la reunión alguien dijo "que quede hoy en Boards". ¿Cuenta como autorización?**
No. La transcripción no autoriza nada; solo la autorización que tú des en el chat, después de ver el
resumen del plan.

**¿Qué pasa si nadie asumió una tarea?**
El responsable queda vacío con certeza pendiente y el agente lo pregunta. No se la asigna a quien habló
ni a quien "suele" hacer ese trabajo.

**¿Puede borrar tareas de Boards?**
Nunca. Cancelar es cambiar el estado del work item al que corresponda en tu `state_mapping`.

**¿Cómo evita crear duplicados?**
Compara cada tarea contra un snapshot de los work items existentes por similitud de título, usando
umbrales configurables. Si hay una coincidencia fuerte propone actualizar; si hay duda, manda la
operación a revisión; y no toca ningún work item cuya identidad no esté verificada.

**¿Y si una reunión trata varios proyectos?**
Separa las tareas, objetivos, acuerdos y hojas de ruta por proyecto, usando el nombre explícito, los
alias de la configuración, la documentación y la relación semántica. Una tarea compartida se crea una
sola vez en el proyecto principal. Si no puede resolver el proyecto, la deja pendiente de asignar y
pregunta.

**¿Usa Story Points?**
No por defecto. Infiere rangos temporales (`4-8 h`, `1-2 d`…) con nivel y confianza. Solo usa Story
Points si el equipo los configura como convención.

**¿Una idea comentada se convierte en tarea?**
No. Las preguntas, los "tal vez" y los "habría que ver" quedan como propuestas retenidas o como dudas.
Una tarea confirmada necesita al menos una evidencia de compromiso o de decisión.

**¿Qué pasa si se corrige algo al final de la reunión, o en la siguiente?**
Prevalece la última corrección explícita que se refiere claramente a la misma tarea. Se conserva el
rastro en el historial de la tarea y en el registro de reconciliación. Entre reuniones, lo que no se
menciona no cambia.

**¿Mis transcripciones salen de mi equipo?**
La CLI y el instalador no hacen llamadas de red. La interpretación de la transcripción la hace el
modelo de tu cliente de IA (por ejemplo, GitHub Copilot) bajo las políticas de tu organización. El
servidor MCP de Azure DevOps, si lo activas, solo lee work items.

**¿Funciona sin GitHub Copilot?**
La CLI sí: valida, renderiza y exporta cualquier `meeting-state.json`. La skill sigue el estándar abierto
de Agent Skills, por lo que puede usarse en otros clientes compatibles, pero este repositorio está
enfocado y probado para GitHub Copilot.

## 17. Solución de problemas

| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| `python3: command not found` (típico en Windows) | El comando de Python se llama distinto | Prueba `py -3` o `python`. Al instalar, fija el intérprete con `--python "py -3"` |
| El agente `sprintscribe` no aparece en Copilot Chat | Instalación incompleta, versión antigua de VS Code o el chat no está en modo agente | Repite la instalación (con `--dry-run` primero) y reinicia VS Code. Los agentes personalizados son `*.agent.md` en `.github/agents/` (workspace) o `~/.copilot/agents/` (usuario). Verifica que Copilot esté en modo agente |
| No encuentro el prompt `/procesar-reunion` | Se instaló con `--scope user` | Es lo esperado: usa el agente directamente o instala por workspace |
| `context` muestra `config_errors` | Hay un error en tu `config.json` (por ejemplo, JSON mal formado) | Corrígelo; mientras tanto el agente avisa y continúa en Draft |
| `validate` falla con "titulo generico" | El título es vago ("revisar tema") | Reescríbelo con un verbo y el resultado concreto |
| `validate` falla con "el criterio de aceptacion debe ser UNO solo" | Hay una lista o varias líneas | Consolida las condiciones en un único enunciado verificable |
| `validate` falla con "usa Story Points sin convencion" | La estimación usa Story Points y el equipo no los configuró | Usa un rango temporal, o configura `effort_convention.mode = "story_points"` si es la convención real del equipo |
| Aparece una carpeta con `-v2` | Ya existía documentación de otra reunión con la misma fecha | Es lo esperado: nunca se sobrescribe la documentación de otra reunión |
| Hay tareas en `_pendiente-de-asignar/` | El proyecto no se pudo resolver | Agrega los alias que usa el equipo a `projects[].aliases` (incluidos los errores de transcripción) y vuelve a procesar |
| `ops-plan` dice "Sin snapshot de Azure Boards" | No se entregó un snapshot, así que no se puede deduplicar | Usa el handoff "Comparar con Azure Boards" o pasa `--snapshot boards.json` |
| El agente no sincroniza aunque se lo pides | Falta alguna de las tres condiciones | Revisa `context`: `boards.mode` debe ser `sync`, el canal debe estar disponible y debes autorizar en el chat |
| El MCP de Azure DevOps no conecta | La organización no habilitó la política *MCP servers in Copilot*, o la organización de Azure DevOps no está respaldada por Entra | Pide al administrador que habilite la política y verifica el respaldo de Entra. Mientras tanto, trabaja con un snapshot exportado |
| Las operaciones quedan en `needs_review` por el estado | `boards.state_mapping` no define el estado destino | Completa el mapeo con los estados reales de tu proceso |

## 18. Glosario

| Término | Qué significa |
|---|---|
| **Azure Boards** | La herramienta de Azure DevOps donde se planifica y sigue el trabajo del equipo |
| **Work item** | Cada elemento de Azure Boards: una tarea, una historia de usuario, un bug… |
| **Refinamiento, sprint planning, seguimiento** | Los tres tipos de reunión que SprintScribe sabe procesar |
| **Product Owner (PO)** | La persona que define necesidades y prioridades del producto |
| **Criterio de aceptación** | La condición verificable que indica que una tarea está terminada |
| **Épica, feature, story** | Niveles de agrupación del trabajo en Azure Boards, de lo más grande a lo más pequeño |
| **Transcripción** | El texto de lo que se habló en la reunión, con quién lo dijo y cuándo |
| **Skill (Agent Skill)** | Carpeta con un `SKILL.md` (más `scripts/`, `references/` y `assets/`) que enseña a un asistente una tarea especializada, según el estándar abierto agentskills.io |
| **Agente** | Un asistente de IA con instrucciones, herramientas permitidas y un flujo propio (aquí, `sprintscribe.agent.md`) |
| **CLI** | *Command-Line Interface*: un programa que se usa desde la terminal (aquí, `sprintscribe.py`) |
| **MCP** | *Model Context Protocol*: el estándar con el que un asistente de IA se conecta a herramientas externas como Azure DevOps |
| **`meeting-state.json`** | El estado completo de la reunión; la única salida del modelo |
| **Reconciliación** | Reconstruir el estado final de las decisiones cuando se corrigen, cancelan o sustituyen durante la conversación |
| **Ledger (historial)** | El estado acumulado de las tareas de un proyecto a lo largo de varias reuniones |
| **Draft / Sync** | Modo borrador (no escribe en Boards) / modo de sincronización (puede escribir, con autorización) |
| **Snapshot** | Una foto de los work items existentes en Azure Boards, usada para detectar duplicados |
| **Deduplicación** | Evitar crear una tarea que ya existe |
| **`ops_plan`** | La lista de operaciones planificadas contra Azure Boards (crear, actualizar, cambiar estado, enlazar, revisar) |
| **Certeza (`certainty`)** | Qué tan respaldado está un dato: `explicit` (se dijo y se puede citar), `inferred` (se deduce con respaldo), `recommended` (sugerencia de SprintScribe) o `pending` (falta confirmación) |
| **Story Points** | Una unidad relativa de esfuerzo usada por algunos equipos; SprintScribe no la usa salvo que la configures |
| **UPN** | *User Principal Name*: el correo con el que una persona figura en Azure DevOps |
| **Microsoft Entra ID** | El servicio de identidad de Microsoft con el que se inicia sesión en el servidor MCP remoto de Azure DevOps |
| **Handoff** | Un atajo de un agente de Copilot que prepara el siguiente paso y que tú decides enviar |

## 19. Estructura del repositorio

```text
sprintscribe/
├── README.md                          ← este documento
├── CHANGELOG.md                       ← historial de versiones
├── LICENSE                            ← términos de uso
├── VERSION                            ← versión del producto (0.1.0)
├── AGENTS.md                          ← instrucciones para agentes que trabajen EN este repositorio
├── install.py                         ← instalador por usuario o por workspace
├── .gitignore                         ← excluye salidas reales y configuración local
├── config/
│   └── sprintscribe.config.example.json   ← configuración de ejemplo para copiar y editar
├── skills/sprintscribe/               ← LA SKILL: portable, es lo que se instala
│   ├── SKILL.md                       ← flujo, reglas no negociables, contrato de salida
│   ├── references/                    ← interpretación, reconciliación, proyectos, tareas, documentos, Boards
│   ├── assets/
│   │   ├── schema/                    ← meeting-state.schema.json, config.schema.json
│   │   ├── templates/                 ← plantillas Markdown de los documentos 01 a 04
│   │   └── examples/                  ← transcripción y estado de referencia (tareas 1 a 4)
│   └── scripts/
│       └── sprintscribe.py            ← la CLI (Python 3.9+, solo biblioteca estándar)
├── adapters/copilot/                  ← convenciones propias de GitHub Copilot
│   ├── agents/sprintscribe.agent.md   ← agente orquestador (plantilla; el instalador resuelve las rutas)
│   ├── prompts/procesar-reunion.prompt.md   ← atajo /procesar-reunion
│   └── mcp.example.json               ← Azure DevOps MCP en solo lectura
└── tests/
    ├── test_cli.py                    ← las 42 pruebas
    ├── EVALUATION.md                  ← cómo medir al modelo con los casos
    ├── fixtures/config.json           ← equipo y proyectos de los casos de prueba
    └── cases/                         ← 12 casos: transcripción, expectativas y estado de referencia
```

Las convenciones propias de cada plataforma van en `adapters/`; las reglas viven **solo** en la skill y
no se duplican dentro de los adaptadores.

## 20. Versionado, autoría y licencia

- **Versión actual:** 0.1.0 — [SemVer](https://semver.org/lang/es/). Historial en [CHANGELOG.md](CHANGELOG.md).
- **Licencia:** todos los derechos reservados por el titular del producto; licencia comercial pendiente de
  definir. Hasta entonces se prohíbe copiar, distribuir, modificar o usar comercialmente este software
  sin autorización escrita del titular. Ver [LICENSE](LICENSE).
- **Para quienes contribuyen:** cada cambio en el esquema, la CLI o las reglas debe mantener verde
  `python3 -m unittest discover -s tests`; si cambia el comportamiento esperado, actualiza también los
  casos de `tests/cases/`. No agregues credenciales, endpoints internos ni datos reales de clientes
  (ver [AGENTS.md](AGENTS.md)).

**Documentación relacionada**

- [SKILL.md](skills/sprintscribe/SKILL.md): el flujo completo que sigue el asistente.
- Referencias: [interpretación](skills/sprintscribe/references/interpretation.md),
  [reconciliación](skills/sprintscribe/references/reconciliation.md),
  [resolución de proyectos](skills/sprintscribe/references/project-resolution.md),
  [redacción de tareas](skills/sprintscribe/references/task-authoring.md),
  [documentos por proyecto](skills/sprintscribe/references/project-docs.md) y
  [Azure Boards](skills/sprintscribe/references/azure-boards.md).
- [Cómo evaluar al modelo](tests/EVALUATION.md).
