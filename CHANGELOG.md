# Changelog

Cambios notables de SprintScribe. Formato basado en
[Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y versionado
[SemVer](https://semver.org/lang/es/).

## [0.1.0] — 2026-10-14

Primera versión.

### Añadido
- Skill portable `sprintscribe` (formato Agent Skills): reglas de interpretación, motor de reconciliación, redacción de tareas, documentación por proyecto y modos de Azure Boards.
- CLI determinista `sprintscribe.py` con los comandos `context`, `validate`, `ops-plan`, `render`, `merge`, `export` y `check-expectations`.
- Esquemas del estado (`meeting-state.schema.json`) y de la configuración.
- Agente orquestador para GitHub Copilot y prompt `/procesar-reunion`.
- Instalador para el usuario y para un workspace.
- 12 casos de prueba con estados de referencia y una suite `unittest` de 42 pruebas (Python 3.9 y 3.12).

### Documentación
- README completo y comprensible para cualquier lector: qué es, para quién, cómo funciona, ejemplo de principio a fin con salidas reales, instalación, referencia de configuración y de comandos, modos Draft y Sync, preguntas frecuentes, solución de problemas y glosario.

### Pendiente
- El adaptador del Excel y del uploader Python del equipo, que espera la versión real del programa.

[0.1.0]: https://github.com/luisdgo2000/sprintscribe/releases/tag/v0.1.0
