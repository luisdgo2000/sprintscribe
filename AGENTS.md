# SprintScribe · instrucciones para agentes

Este repositorio es el **producto** SprintScribe, no un espacio de trabajo de reuniones.

- La skill está en `skills/sprintscribe/SKILL.md`. Es la única fuente de las reglas de interpretación y del formato.
- La lógica determinista está en `skills/sprintscribe/scripts/sprintscribe.py` (Python 3.9+, solo biblioteca estándar).
- Las convenciones propias de cada plataforma van en `adapters/`. No dupliques las reglas de la skill dentro de los adaptadores.
- Cada cambio en el esquema, la CLI o las reglas debe mantener verde `python3 -m unittest discover -s tests`. Si el comportamiento esperado cambia, actualiza también los casos de `tests/cases/`.
- No agregues credenciales, endpoints internos ni datos reales de clientes.
