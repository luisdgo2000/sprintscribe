# Changelog

## 0.1.0 · 2026-10-14

Primera versión.

- Skill portable `sprintscribe` (formato Agent Skills): reglas de interpretación, motor de reconciliación, redacción de tareas, documentación por proyecto y modos de Azure Boards.
- CLI determinista `sprintscribe.py` con los comandos `context`, `validate`, `ops-plan`, `render`, `merge`, `export` y `check-expectations`.
- Esquemas del estado (`meeting-state.schema.json`) y de la configuración.
- Agente orquestador para GitHub Copilot y prompt `/procesar-reunion`.
- Instalador para el usuario y para un workspace.
- 12 casos de prueba con estados de referencia y una suite `unittest`.
- Pendiente: el adaptador del Excel y del uploader Python del equipo, que espera la versión real del programa.
