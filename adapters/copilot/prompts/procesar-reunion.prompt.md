---
name: procesar-reunion
description: 'Procesa una transcripción de reunión con SprintScribe (tareas para Azure Boards y documentación por proyecto).'
agent: sprintscribe
argument-hint: 'Ruta de la transcripción'
---

Procesa la reunión de `${input:transcript:ruta de la transcripción}` con el flujo completo de SprintScribe, en modo Draft.

Contexto adicional del usuario (opcional): ${input:notas:notas, proyecto o reunión previa}
