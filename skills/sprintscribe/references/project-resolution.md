# Identificación y separación por proyecto

Una reunión puede tratar varios proyectos, iniciativas o productos de datos. Antes de documentar, resuelve a qué proyecto pertenece cada tarea y cada acuerdo.

## Orden de resolución

1. **Nombre explícito** mencionado en la reunión ("en el Data Lake de Ventas…").
2. **Alias** de `projects[].aliases` en la configuración y alias que ya figuran en los ledgers. Esto incluye las variantes por errores de transcripción.
3. **Documentación existente** (`projects[].docs`) y **work items relacionados**, por área o por padre, cuando estén disponibles.
4. **Relación semántica** entre necesidades, entregables y responsables. Ejemplo: "el certificado de firma" pertenece a Facturación Electrónica aunque en esa frase no se nombre el proyecto.

Registra en `projects[].resolution_basis` cómo lo identificaste.

## Reglas

- **La proximidad no es pertenencia.** No asignes una tarea a un proyecto solo porque se mencionó cerca de su nombre. La conversación salta de tema; verifica que el objetivo de la tarea corresponda al proyecto.
- **Tareas compartidas:**
  - si un trabajo aplica a varios proyectos, crea **una** tarea en el proyecto principal, es decir, donde se ejecuta o el que la origina;
  - lista los demás en `related_projects`;
  - no la dupliques.
- **Sin resolución posible:**
  - usa `project_id: "PENDING"` con ID `PEND-T<n>`;
  - agrega una `open_question` que diga qué proyectos son candidatos;
  - `render` las deja en `_pendiente-de-asignar/`.
- **Proyecto nuevo,** que no figura en la configuración:
  - créalo en `projects[]` con `status: "pending_confirmation"`;
  - propón un `id` (slug) y una `key` corta;
  - pide confirmación en las ambigüedades finales.
- **Cada proyecto tiene lo suyo:** objetivos, tareas, acuerdos, estimaciones y hoja de ruta. Nunca un documento genérico de toda la reunión.
- **Decisiones transversales:** una decisión que afecta a todos los proyectos va con `project_id: null` y aparece en cada proyecto marcada como "transversal".
