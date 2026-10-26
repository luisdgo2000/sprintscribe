#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sprintscribe.py - Capa determinista de SprintScribe.

El modelo interpreta la reunion y escribe UN archivo: meeting-state.json.
Todo lo demas sale de aqui, sin criterio propio ni llamadas externas:

    context              estado previo, IDs libres y configuracion efectiva
    validate             esquema + reglas de negocio (exit 1 si hay errores)
    ops-plan             plan de operaciones contra Azure Boards (no escribe en Boards)
    render               documentos 01-04 por proyecto a partir del estado
    merge                actualiza el ledger acumulado de cada proyecto
    export               tareas listas, en JSON o CSV, para el adaptador de Excel
    check-expectations   califica un estado contra los casos de prueba

Solo biblioteca estandar. Compatible con Python 3.9+.
"""

from __future__ import annotations

import argparse
import csv
import difflib
import io
import json
import os
import re
import string
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

__version__ = "0.1.0"

SKILL_DIR = Path(__file__).resolve().parent.parent
SCHEMA_DIR = SKILL_DIR / "assets" / "schema"
TEMPLATE_DIR = SKILL_DIR / "assets" / "templates"

PENDING_PROJECT = "PENDING"
PENDING_KEY = "PEND"
PENDING_FOLDER = "_pendiente-de-asignar"

READY = ("confirmed", "modified", "blocked")
NOT_READY = ("proposed", "needs_clarification", "deferred")
CLOSED = ("cancelled",)
DONE = ("completed",)

STATUS_ES = {
    "proposed": "Propuesta",
    "confirmed": "Confirmada",
    "modified": "Modificada",
    "cancelled": "Cancelada o descartada",
    "blocked": "Bloqueada",
    "deferred": "Diferida",
    "needs_clarification": "Pendiente de aclaración",
    "completed": "Completada",
}
CERTAINTY_ES = {
    "explicit": "confirmado explícitamente",
    "inferred": "inferido con respaldo contextual",
    "recommended": "recomendado por SprintScribe",
    "pending": "pendiente de confirmación",
}
LEVEL_ES = {"low": "bajo", "medium": "medio", "high": "alto"}
LEVEL_ES_F = {"low": "baja", "medium": "media", "high": "alta"}
DECISION_STATUS_ES = {"confirmed": "confirmada", "pending": "pendiente", "discarded": "descartada",
                      "superseded": "reemplazada"}
ACTION_ES = {
    "added": "Añadida",
    "modified": "Modificada",
    "superseded": "Sustituida",
    "cancelled": "Cancelada",
    "reassigned": "Reasignada",
    "split": "Dividida",
    "merged": "Combinada",
    "deferred": "Diferida",
    "blocked": "Bloqueada",
    "completed": "Completada",
    "reopened": "Reabierta",
    "project_changed": "Cambio de proyecto",
}
OP_ES = {
    "create": "Crear",
    "update": "Actualizar",
    "change_state": "Cambiar estado",
    "link": "Enlazar",
    "noop": "Sin cambios",
    "hold": "Retener",
    "skip": "Omitir",
    "needs_review": "Revisar",
}

DEFAULT_CONFIG = {
    "config_version": "1.0",
    "language": "es",
    "docs_root": "./documentacion",
    "inbox_dir": "_inbox",
    "po": {"name": "Brian", "aliases": []},
    "roster": [],
    "projects": [],
    "effort_convention": {"mode": "ranges", "native_field": None},
    "boards": {
        "mode": "draft",
        "channel": "none",
        "process": None,
        "work_item_types": {},
        "state_mapping": {},
        "dedup": {"same_threshold": 0.9, "review_threshold": 0.72, "margin": 0.05},
        "auto_apply": [],
    },
    "uploader": {"status": "pending"},
}

GENERIC_TITLES = (
    r"^(revisar|ver|trabajar en|hacer|ajustar|mejorar|analizar|seguimiento( de)?|"
    r"atender|resolver|tratar|validar)( (el|la|los|las|un|una|lo))? "
    r"(tema|temas|cosa|cosas|ajuste|ajustes|mejora|mejoras|pendiente|pendientes|eso|esto|"
    r"problema|asunto|detalle|detalles)$"
)
TIME_UNIT = re.compile(
    r"\d.*\b(h|hs|hr|hrs|hora|horas|d|dia|dias|jornada|jornadas|semana|semanas|sem|sprint|sprints)\b"
)
STORY_POINTS = re.compile(r"\b(sp|story ?points?|puntos de historia|pts?)\b")
LIST_MARKER = re.compile(r"(?m)^\s*(?:[-*\u2022]|\d+[.)]|[a-z][.)])\s+")
STOPWORDS = set(
    "a al con de del el en la las lo los para por que se un una y o e u su sus "
    "the of to and for in on".split()
)


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def load_json(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def dump_json(data, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    os.replace(tmp, path)


def write_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def normalize(text):
    text = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-z0-9 ]+", " ", text.lower())
    return re.sub(r"\s+", " ", text).strip()


def tokens(text):
    return [t for t in normalize(text).split() if t not in STOPWORDS]


def similarity(a, b):
    """Parecido entre dos titulos, 0..1. Max entre secuencia y Dice de tokens."""
    na, nb = " ".join(tokens(a)), " ".join(tokens(b))
    if not na or not nb:
        return 0.0
    seq = difflib.SequenceMatcher(None, na, nb).ratio()
    ta, tb = set(na.split()), set(nb.split())
    dice = 2 * len(ta & tb) / (len(ta) + len(tb))
    return round(max(seq, dice), 3)


def slug(text):
    s = normalize(text).replace(" ", "-")
    return re.sub(r"-+", "-", s).strip("-") or "sin-nombre"


def deep_merge(base, over):
    out = dict(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def md_escape_cell(text):
    return str(text if text not in (None, "") else "—").replace("|", "\\|").replace("\n", " ")


def or_dash(value):
    if value in (None, "", []):
        return "—"
    if isinstance(value, (list, tuple)):
        return ", ".join(str(v) for v in value)
    return str(value)


def bullets(items, empty="Ninguno identificado."):
    items = [i for i in (items or []) if i not in (None, "")]
    if not items:
        return "_" + empty + "_"
    return "\n".join("- " + str(i) for i in items)


# ---------------------------------------------------------------------------
# Validador de JSON Schema (subconjunto draft-07 suficiente para nuestros esquemas)
# ---------------------------------------------------------------------------
_TYPES = {
    "object": dict,
    "array": list,
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "null": type(None),
}


def _type_ok(value, typ):
    names = typ if isinstance(typ, list) else [typ]
    for name in names:
        py = _TYPES[name]
        if name in ("integer", "number") and isinstance(value, bool):
            continue
        if isinstance(value, py):
            return True
    return False


def schema_errors(value, schema, root=None, path="$"):
    root = root if root is not None else schema
    errs = []
    if "$ref" in schema:
        ref = schema["$ref"]
        target = root
        for part in ref.lstrip("#/").split("/"):
            target = target[part]
        return schema_errors(value, target, root, path)
    if "type" in schema and not _type_ok(value, schema["type"]):
        return ["%s: se esperaba %s" % (path, schema["type"])]
    if "enum" in schema and value not in schema["enum"]:
        errs.append("%s: '%s' no es uno de %s" % (path, value, schema["enum"]))
    if isinstance(value, str):
        if "minLength" in schema and len(value.strip()) < schema["minLength"]:
            errs.append("%s: texto vacio" % path)
        if "pattern" in schema and not re.search(schema["pattern"], value):
            errs.append("%s: '%s' no cumple el patron %s" % (path, value, schema["pattern"]))
    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            errs.append("%s: se requieren al menos %d elementos" % (path, schema["minItems"]))
        if "items" in schema:
            for i, item in enumerate(value):
                errs.extend(schema_errors(item, schema["items"], root, "%s[%d]" % (path, i)))
    if isinstance(value, dict):
        props = schema.get("properties", {})
        for req in schema.get("required", []):
            if req not in value:
                errs.append("%s: falta el campo obligatorio '%s'" % (path, req))
        addl = schema.get("additionalProperties", True)
        for k, v in value.items():
            if k in props:
                errs.extend(schema_errors(v, props[k], root, "%s.%s" % (path, k)))
            elif addl is False:
                errs.append("%s: campo no permitido '%s'" % (path, k))
            elif isinstance(addl, dict):
                errs.extend(schema_errors(v, addl, root, "%s.%s" % (path, k)))
    return errs


# ---------------------------------------------------------------------------
# Configuracion
# ---------------------------------------------------------------------------
def user_config_path():
    base = os.environ.get("SPRINTSCRIBE_HOME") or os.path.join(os.path.expanduser("~"), ".sprintscribe")
    return Path(base) / "config.json"


def find_workspace_config(start):
    cur = Path(start).resolve()
    for d in [cur] + list(cur.parents):
        cand = d / ".sprintscribe" / "config.json"
        if cand.is_file():
            return cand
    return None


def load_config(explicit=None, cwd=None):
    """Devuelve (config_efectiva, [rutas_usadas]).

    Orden: defaults < usuario (~/.sprintscribe) < workspace (.sprintscribe/ hacia arriba)
    < --config explicito. docs_root se resuelve relativo al archivo que lo define.
    """
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))
    used = []
    anchor = Path(cwd or os.getcwd())
    layers = []
    if explicit:
        layers = [Path(explicit)]
    else:
        up = user_config_path()
        if up.is_file():
            layers.append(up)
        ws = find_workspace_config(cwd or os.getcwd())
        if ws and ws.resolve() != up.resolve():
            layers.append(ws)
    for layer in layers:
        data = load_json(layer)
        if "docs_root" in data:
            data["docs_root"] = str(_resolve_from(layer, data["docs_root"]))
        cfg = deep_merge(cfg, data)
        used.append(str(layer))
    cfg["docs_root"] = os.path.expanduser(cfg["docs_root"])
    if not Path(cfg["docs_root"]).is_absolute():
        cfg["docs_root"] = str((anchor / cfg["docs_root"]).resolve())
    return cfg, used


def _resolve_from(config_file, value):
    p = Path(os.path.expanduser(str(value)))
    if p.is_absolute():
        return p
    base = Path(config_file).resolve().parent
    if base.name == ".sprintscribe":
        base = base.parent
    return (base / p).resolve()


def config_errors(cfg):
    schema = load_json(SCHEMA_DIR / "config.schema.json")
    return schema_errors({k: v for k, v in cfg.items()}, schema)


# ---------------------------------------------------------------------------
# Lectura del estado
# ---------------------------------------------------------------------------
class State:
    def __init__(self, data):
        self.data = data
        self.meeting = data.get("meeting", {})
        self.projects = data.get("projects", [])
        self.tasks = data.get("tasks", [])
        self.decisions = data.get("decisions", [])
        self.contradictions = data.get("contradictions", [])
        self.open_questions = data.get("open_questions", [])
        self.log = data.get("reconciliation_log", [])
        self.ops = data.get("ops_plan", [])
        self.project_by_id = {p["id"]: p for p in self.projects if "id" in p}
        self.task_by_id = {t["id"]: t for t in self.tasks if "id" in t}

    def project_name(self, pid):
        if pid == PENDING_PROJECT:
            return "Pendiente de asignar"
        p = self.project_by_id.get(pid)
        return p["name"] if p else pid

    def tasks_of(self, pid, include_related=True):
        out = []
        for t in self.tasks:
            if t.get("project_id") == pid:
                out.append(t)
            elif include_related and pid in (t.get("related_projects") or []):
                out.append(t)
        return out


def rel(task, key):
    return (task.get("relations") or {}).get(key)


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------
def validate_state(data, cfg=None):
    """Devuelve (errores, advertencias). Errores = el estado no se puede entregar."""
    cfg = cfg or DEFAULT_CONFIG
    errors, warnings = [], []
    schema = load_json(SCHEMA_DIR / "meeting-state.schema.json")
    errors.extend(schema_errors(data, schema))
    if errors:
        return errors, warnings

    st = State(data)
    E, W = errors.append, warnings.append

    def unique(items, key, label):
        seen = set()
        for it in items:
            v = it.get(key)
            if v in seen:
                E("%s duplicado: %s" % (label, v))
            seen.add(v)

    unique(st.projects, "id", "Proyecto")
    unique(st.projects, "key", "Clave de proyecto")
    unique(st.tasks, "id", "ID de tarea")
    unique(st.decisions, "id", "ID de decision")
    unique(st.log, "id", "ID de reconciliacion")
    unique(st.open_questions, "id", "ID de pregunta")
    unique(st.contradictions, "id", "ID de contradiccion")

    task_ids = set(st.task_by_id)
    decision_ids = {d["id"] for d in st.decisions}
    project_ids = set(st.project_by_id)
    sp_allowed = (cfg.get("effort_convention") or {}).get("mode") == "story_points"

    known_people = set()
    for p in st.meeting.get("participants", []):
        known_people.add(normalize(p["name"]))
        for lab in p.get("speaker_labels", []):
            known_people.add(normalize(lab))
    for r in cfg.get("roster", []):
        known_people.add(normalize(r["name"]))
        for a in r.get("aliases", []):
            known_people.add(normalize(a))

    def check_ref(ref, where):
        if ref and ref not in task_ids:
            E("%s referencia una tarea inexistente: %s" % (where, ref))

    # --- tareas -----------------------------------------------------------
    for t in st.tasks:
        tid, status, pid = t["id"], t["status"], t["project_id"]
        where = "Tarea %s" % tid
        prefix = tid.split("-T")[0]

        if pid == PENDING_PROJECT:
            if prefix != PENDING_KEY:
                E("%s: una tarea sin proyecto debe usar el prefijo %s-" % (where, PENDING_KEY))
        elif pid not in project_ids:
            E("%s: el proyecto '%s' no existe (usa PENDING si no se puede resolver)" % (where, pid))
        elif st.project_by_id[pid]["key"] != prefix:
            E("%s: el prefijo no coincide con la clave del proyecto (%s)" % (where, st.project_by_id[pid]["key"]))
        for rp in t.get("related_projects", []) or []:
            if rp not in project_ids:
                E("%s: proyecto relacionado inexistente '%s'" % (where, rp))

        title_n = normalize(t["title"])
        if re.match(GENERIC_TITLES, title_n) or len(title_n.split()) < 3:
            E("%s: titulo generico o demasiado corto: '%s'" % (where, t["title"]))

        for dep in t.get("depends_on", []) or []:
            check_ref(dep, where + " (depends_on)")
            dep_t = st.task_by_id.get(dep)
            if dep_t and status in READY and dep_t["status"] in CLOSED:
                E("%s depende de %s, que esta descartada" % (where, dep))
        for key in ("superseded_by", "split_from", "merged_into"):
            check_ref(rel(t, key), "%s (%s)" % (where, key))
        for s in rel(t, "supersedes") or []:
            check_ref(s, where + " (supersedes)")
            other = st.task_by_id.get(s)
            if other and rel(other, "superseded_by") != tid:
                E("%s sustituye a %s, pero %s no indica superseded_by = %s" % (where, s, s, tid))
        sb = rel(t, "superseded_by")
        if sb:
            if status not in CLOSED:
                E("%s fue sustituida por %s pero su estado es '%s' (debe ser cancelled)" % (where, sb, status))
            other = st.task_by_id.get(sb)
            if other and tid not in (rel(other, "supersedes") or []):
                E("%s indica superseded_by = %s, pero %s no la lista en supersedes" % (where, sb, sb))
        if rel(t, "merged_into") and status not in CLOSED:
            E("%s se combino en otra tarea pero sigue con estado '%s'" % (where, status))

        if status in CLOSED:
            if not any(e["task_ref"] == tid and e["action"] in ("cancelled", "superseded", "merged")
                       for e in st.log):
                E("%s esta descartada pero no tiene entrada en reconciliation_log que lo explique" % where)

        if status in READY:
            desc = (t.get("description") or "").strip()
            ac = (t.get("acceptance_criterion") or "").strip()
            if not desc:
                E("%s: falta la descripcion" % where)
            elif len(desc) < 80:
                W("%s: la descripcion es muy breve (%d caracteres); debe bastar para ejecutar sin leer la reunion" % (where, len(desc)))
            if not ac:
                E("%s: falta el criterio de aceptacion" % where)
            else:
                if LIST_MARKER.search(ac) or len([l for l in ac.splitlines() if l.strip()]) > 1:
                    E("%s: el criterio de aceptacion debe ser UNO solo, sin listas ni varias lineas" % where)
                if len(re.findall(r"\b(dado que|given)\b", normalize(ac))) > 1:
                    E("%s: el criterio de aceptacion contiene varios escenarios" % where)
            eff = t.get("effort")
            if not eff:
                E("%s: falta la estimacion de esfuerzo" % where)
            else:
                rng = normalize(eff["range"])
                if STORY_POINTS.search(rng) and not sp_allowed:
                    E("%s: el esfuerzo usa Story Points sin convencion del equipo; usa un rango temporal" % where)
                elif not TIME_UNIT.search(rng) and not sp_allowed:
                    E("%s: el rango de esfuerzo '%s' no tiene unidad temporal (h, d, semanas)" % (where, eff["range"]))

        owner = t.get("owner")
        if owner and normalize(owner) not in known_people and t.get("owner_certainty") == "explicit":
            W("%s: responsable '%s' no aparece entre participantes ni en el roster" % (where, owner))
        if owner and t.get("owner_certainty") == "pending":
            W("%s: tiene responsable pero owner_certainty = pending" % where)

        if status == "needs_clarification":
            referenced = any(tid in (q.get("blocks") or []) for q in st.open_questions) or \
                any(tid in (c.get("task_refs") or []) for c in st.contradictions)
            if not referenced:
                W("%s: pendiente de aclaracion, pero ninguna pregunta abierta o contradiccion la referencia" % where)

    # tareas activas muy parecidas en el mismo proyecto
    active = [t for t in st.tasks if t["status"] in READY]
    for i, a in enumerate(active):
        for b in active[i + 1:]:
            if a["project_id"] == b["project_id"] and similarity(a["title"], b["title"]) >= 0.9:
                W("Tareas %s y %s tienen titulos casi iguales; confirma que no son la misma" % (a["id"], b["id"]))

    # --- contradicciones -------------------------------------------------
    for c in st.contradictions:
        for ref in c.get("task_refs", []) or []:
            check_ref(ref, "Contradiccion %s" % c["id"])
            t = st.task_by_id.get(ref)
            if t and not c.get("resolution") and c.get("blocking", True) and t["status"] in ("confirmed", "modified"):
                E("Tarea %s esta confirmada pese a la contradiccion bloqueante sin resolver %s" % (ref, c["id"]))

    # --- proyectos, objetivo y hoja de ruta -------------------------------
    for p in st.projects:
        pid = p["id"]
        ptasks = st.tasks_of(pid)
        ready = [t for t in ptasks if t["status"] in READY]
        closed_titles = {normalize(t["title"]) for t in ptasks if t["status"] in CLOSED}
        obj = p.get("sprint_objective")
        if ready and not obj:
            E("Proyecto %s: tiene tareas listas pero no tiene objetivo de sprint" % pid)
        if obj:
            if normalize(obj["statement"]) in {normalize(t["title"]) for t in ptasks}:
                E("Proyecto %s: el objetivo repite el titulo de una tarea; debe explicar el proposito comun" % pid)
            for d in obj.get("deliverables", []) or []:
                if normalize(d) in closed_titles:
                    E("Proyecto %s: el entregable '%s' corresponde a una tarea descartada" % (pid, d))
            if obj["certainty"] == "pending" and not obj.get("candidates"):
                W("Proyecto %s: objetivo pendiente sin objetivos candidatos" % pid)
        roadmap = p.get("roadmap") or []
        if ready and not roadmap:
            W("Proyecto %s: no tiene hoja de ruta" % pid)
        orders = [s["order"] for s in roadmap]
        if len(orders) != len(set(orders)):
            E("Proyecto %s: hay pasos de hoja de ruta con el mismo orden" % pid)
        for s in roadmap:
            sw = "Proyecto %s, paso %s" % (pid, s["order"])
            for ref in s.get("task_refs", []) or []:
                check_ref(ref, sw)
                t = st.task_by_id.get(ref)
                if t and t["status"] in CLOSED:
                    E("%s incluye la tarea descartada %s" % (sw, ref))
            for dep in s.get("depends_on", []) or []:
                if dep not in orders:
                    E("%s depende de un paso inexistente (%s)" % (sw, dep))
                elif dep >= s["order"]:
                    E("%s depende del paso %s, que va despues: ordena por dependencias" % (sw, dep))
            if not TIME_UNIT.search(normalize(s["duration"]["range"])):
                W("%s: la duracion '%s' no tiene unidad temporal" % (sw, s["duration"]["range"]))

    # --- decisiones, preguntas, log ---------------------------------------
    for d in st.decisions:
        for ref in d.get("task_refs", []) or []:
            check_ref(ref, "Decision %s" % d["id"])
        if d.get("supersedes") and d["supersedes"] not in decision_ids:
            E("Decision %s sustituye a una decision inexistente: %s" % (d["id"], d["supersedes"]))
        if d.get("project_id") and d["project_id"] not in project_ids and d["project_id"] != PENDING_PROJECT:
            E("Decision %s: proyecto inexistente '%s'" % (d["id"], d["project_id"]))
    for q in st.open_questions:
        for ref in q.get("blocks", []) or []:
            check_ref(ref, "Pregunta %s" % q["id"])
    if len(st.open_questions) > 7:
        W("Hay %d preguntas abiertas; deja solo las que impiden ejecutar el trabajo" % len(st.open_questions))
    for e in st.log:
        check_ref(e["task_ref"], "Reconciliacion %s" % e["id"])
        if e.get("cause_decision") and e["cause_decision"] not in decision_ids:
            E("Reconciliacion %s: decision causante inexistente %s" % (e["id"], e["cause_decision"]))

    # --- operaciones externas ---------------------------------------------
    mode = (cfg.get("boards") or {}).get("mode", "draft")
    for i, op in enumerate(st.ops):
        check_ref(op["task_ref"], "Operacion %d" % i)
        if op["status"] in ("applied", "failed") and not op.get("result"):
            E("Operacion %d (%s %s) dice '%s' sin el resultado real de la herramienta" % (i, op["op"], op["task_ref"], op["status"]))
        if op["status"] == "applied" and mode != "sync":
            E("Operacion %d marcada como aplicada en modo %s: no se puede reportar una sincronizacion sin integracion" % (i, mode))

    return errors, warnings


# ---------------------------------------------------------------------------
# ops-plan
# ---------------------------------------------------------------------------
def load_snapshot(path):
    if not path:
        return None
    data = load_json(path)
    items = data.get("work_items", []) if isinstance(data, dict) else data
    return [i for i in items if isinstance(i, dict) and "id" in i]


def _person_match(name, assigned, cfg):
    if not name or not assigned:
        return name == assigned or (not name and not assigned)
    a = normalize(assigned)
    if normalize(name) in a:
        return True
    for r in cfg.get("roster", []):
        if normalize(r["name"]) == normalize(name):
            for v in [r.get("upn")] + list(r.get("aliases", [])):
                if v and normalize(v) in a:
                    return True
    return False


def build_ops_plan(data, snapshot, cfg):
    st = State(data)
    boards = cfg.get("boards") or {}
    mapping = boards.get("state_mapping") or {}
    dedup = boards.get("dedup") or {}
    same_t = dedup.get("same_threshold", 0.9)
    review_t = dedup.get("review_threshold", 0.72)
    margin = dedup.get("margin", 0.05)
    by_id = {int(w["id"]): w for w in (snapshot or [])}
    ops = []

    def add(op, t, status, reason, **kw):
        entry = {"op": op, "task_ref": t["id"], "status": status, "reason": reason}
        entry.update({k: v for k, v in kw.items() if v is not None})
        ops.append(entry)

    def candidates_for(t):
        if snapshot is None:
            return []
        scored = []
        for w in snapshot:
            if w.get("project_id") and t["project_id"] not in (w["project_id"], PENDING_PROJECT):
                continue
            scored.append((similarity(t["title"], w.get("title", "")), w))
        scored.sort(key=lambda x: -x[0])
        return scored

    def state_change(t, wid, logical):
        target = mapping.get(logical)
        if not target:
            add("change_state", t, "needs_review",
                "El estado destino para '%s' no esta configurado en boards.state_mapping" % logical,
                work_item_id=wid)
        elif snapshot is not None and wid not in by_id:
            add("change_state", t, "needs_review",
                "El work item %s no aparece en el snapshot; verificar identidad antes de tocarlo" % wid,
                work_item_id=wid, target_state=target)
        elif snapshot is not None and by_id[wid].get("state") == target:
            add("noop", t, "pending", "El work item ya esta en '%s'" % target, work_item_id=wid)
        else:
            add("change_state", t, "pending",
                "Tarea %s en la reunion; nunca se elimina, solo cambia de estado" % STATUS_ES[logical].lower(),
                work_item_id=wid, target_state=target)

    def field_diff(t, w):
        diff = {}
        if normalize(w.get("title")) != normalize(t["title"]):
            diff["System.Title"] = t["title"]
        if t.get("owner") and not _person_match(t["owner"], w.get("assigned_to"), cfg):
            diff["System.AssignedTo"] = t["owner"]
        return diff

    for t in st.tasks:
        status = t["status"]
        wid = (t.get("boards") or {}).get("work_item_id")
        scored = [] if wid else candidates_for(t)
        best = scored[0] if scored else (0.0, None)
        second = scored[1][0] if len(scored) > 1 else 0.0
        top = [{"work_item_id": w["id"], "title": w.get("title"), "score": s} for s, w in scored[:3] if s >= review_t]

        if status in CLOSED or status in DONE:
            logical = "cancelled" if status in CLOSED else "completed"
            if wid:
                state_change(t, wid, logical)
            elif best[0] >= review_t:
                add("needs_review", t, "needs_review",
                    "Tarea %s que podria existir en Boards por similitud de titulo; confirmar identidad antes de cambiar su estado" % STATUS_ES[status].lower(),
                    candidates=top)
            else:
                add("skip", t, "pending", "No hay work item asociado; no hay nada que sincronizar")
            continue

        if status in NOT_READY:
            if wid and status == "deferred":
                state_change(t, wid, "deferred")
            else:
                add("hold", t, "pending", "Estado '%s': no se sube hasta que se confirme" % STATUS_ES[status])
            continue

        # READY
        if wid:
            if snapshot is not None and wid not in by_id:
                add("needs_review", t, "needs_review",
                    "El work item %s no aparece en el snapshot de Boards" % wid, work_item_id=wid)
                continue
            if snapshot is not None:
                diff = field_diff(t, by_id[wid])
                if diff:
                    add("update", t, "pending", "Cambios confirmados en la reunion", work_item_id=wid, fields=diff)
                else:
                    add("noop", t, "pending", "El work item ya refleja la tarea", work_item_id=wid)
            elif status == "modified":
                add("update", t, "pending", "Tarea modificada en la reunion; aplicar los campos vigentes",
                    work_item_id=wid,
                    fields={"System.Title": t["title"], "System.AssignedTo": t.get("owner")})
            else:
                add("noop", t, "pending", "Ya vinculada al work item %s (sin snapshot para comparar)" % wid,
                    work_item_id=wid)
            if status == "blocked" and mapping.get("blocked"):
                state_change(t, wid, "blocked")
            continue

        if best[1] is not None and best[0] >= same_t and best[0] - second >= margin:
            w = best[1]
            diff = field_diff(t, w)
            if diff:
                add("update", t, "needs_review",
                    "Ya existe en Boards (similitud %.2f): no se crea duplicado; confirmar la identidad antes de actualizar" % best[0],
                    work_item_id=int(w["id"]), fields=diff, candidates=top)
            else:
                add("noop", t, "pending",
                    "Ya existe en Boards (similitud %.2f) y coincide; no se crea duplicado" % best[0],
                    work_item_id=int(w["id"]))
            continue
        if best[0] >= review_t:
            add("needs_review", t, "needs_review",
                "Posible duplicado en Boards (similitud %.2f); decidir si es el mismo trabajo" % best[0],
                candidates=top)
            continue

        fields = {
            "System.Title": t["title"],
            "System.AssignedTo": t.get("owner"),
            "work_item_type": (boards.get("work_item_types") or {}).get(t.get("work_item_type") or "task"),
        }
        add("create", t, "pending",
            "Tarea nueva confirmada" + ("" if snapshot is not None else " (sin snapshot de Boards: verificar duplicados al sincronizar)"),
            fields={k: v for k, v in fields.items() if v})
        for dep in t.get("depends_on", []) or []:
            add("link", t, "pending", "Dependencia de %s sobre %s" % (t["id"], dep),
                fields={"link_type": "dependency", "target_task": dep})
    return ops


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------
def tmpl(name):
    return string.Template((TEMPLATE_DIR / name).read_text(encoding="utf-8"))


def meeting_label(st):
    m = st.meeting
    parts = [m.get("title") or m["id"]]
    if m.get("date"):
        parts.append(m["date"])
    parts.append({"refinement": "refinamiento", "planning": "sprint planning", "follow_up": "seguimiento",
                  "review": "revisión", "other": "reunión"}[m["type"]])
    return " · ".join(parts)


def fmt_evidence(evs):
    out = []
    for e in evs or []:
        who = e.get("speaker")
        ts = e.get("timestamp")
        head = " ".join(x for x in [("[%s]" % ts) if ts else "", ("%s:" % who) if who else ""] if x)
        out.append(("%s “%s”" % (head, e["quote"])).strip())
    return " · ".join(out) if out else "—"


def fmt_effort(eff):
    if not eff:
        return "—"
    s = "%s · esfuerzo %s · confianza %s. %s" % (
        eff["range"], LEVEL_ES[eff["level"]], LEVEL_ES_F[eff["confidence"]], eff["rationale"])
    if eff.get("native_value") is not None:
        s += " (valor nativo: %s)" % eff["native_value"]
    return s


def fmt_person(name, certainty=None):
    if not name:
        return "Sin responsable explícito (pendiente de confirmar)"
    if certainty and certainty != "explicit":
        return "%s (%s)" % (name, CERTAINTY_ES[certainty])
    return name


def render_task(st, t):
    hh = t.get("hierarchy_hint") or {}
    hierarchy = " › ".join("%s: %s" % (lbl, hh[k]) for k, lbl in
                           (("use_case", "Caso de uso"), ("epic", "Épica"), ("feature", "Feature"), ("story", "Story"))
                           if hh.get(k)) or "—"
    b = t.get("boards") or {}
    boards = "#%s (%s)" % (b["work_item_id"], b.get("state") or "estado desconocido") if b.get("work_item_id") else "No existe o no verificado"
    rel_lines = []
    r = t.get("relations") or {}
    if r.get("supersedes"):
        rel_lines.append("Sustituye a: " + ", ".join(r["supersedes"]))
    if r.get("superseded_by"):
        rel_lines.append("Sustituida por: " + r["superseded_by"])
    if r.get("split_from"):
        rel_lines.append("Dividida de: " + r["split_from"])
    if r.get("merged_into"):
        rel_lines.append("Combinada en: " + r["merged_into"])
    if t.get("related_projects"):
        rel_lines.append("También afecta a: " + ", ".join(st.project_name(p) for p in t["related_projects"]))
    if t.get("blocked_by"):
        rel_lines.append("Bloqueo: " + t["blocked_by"])
    pr = t.get("priority")
    priority = "—" if pr in (None, "") else ("%s (%s)" % (pr, CERTAINTY_ES[t["priority_certainty"]]) if t.get("priority_certainty") not in (None, "explicit") else str(pr))
    return tmpl("task.md.tmpl").substitute(
        id=t["id"],
        title=t["title"],
        status=STATUS_ES[t["status"]],
        certainty=CERTAINTY_ES[t["certainty"]],
        project=st.project_name(t["project_id"]),
        owner=fmt_person(t.get("owner"), t.get("owner_certainty")),
        priority=priority,
        work_item_type=t.get("work_item_type") or "task",
        hierarchy=hierarchy,
        depends_on=or_dash(t.get("depends_on")),
        boards=boards,
        proposed_by=t.get("proposed_by") or "—",
        decided_by=t.get("decided_by") or "—",
        description=(t.get("description") or "_Sin descripción._").strip(),
        acceptance_criterion=(t.get("acceptance_criterion") or "_Pendiente: la tarea aún no está lista._").strip(),
        effort=fmt_effort(t.get("effort")),
        evidence=fmt_evidence(t.get("evidence")),
        relations=("\n" + "\n".join("- " + x for x in rel_lines) + "\n") if rel_lines else "",
    ).strip() + "\n"


def render_tasks_doc(st, pid, tasks, ops, cfg):
    ready = [t for t in tasks if t["status"] in READY]
    pending = [t for t in tasks if t["status"] in NOT_READY]
    closed = [t for t in tasks if t["status"] in CLOSED + DONE]
    rows = ["| ID | Título | Responsable | Esfuerzo | Estado |", "|---|---|---|---|---|"]
    for t in ready:
        rows.append("| %s | %s | %s | %s | %s |" % (
            t["id"], md_escape_cell(t["title"]), md_escape_cell(t.get("owner") or "Pendiente"),
            md_escape_cell((t.get("effort") or {}).get("range")), STATUS_ES[t["status"]]))
    counts = {}
    for t in tasks:
        counts[t["status"]] = counts.get(t["status"], 0) + 1
    count_line = " · ".join("%s: %d" % (STATUS_ES[k], v) for k, v in sorted(counts.items()))
    summary = "**Resumen:** %s\n\n%s" % (count_line or "sin tareas", "\n".join(rows) if ready else "_No hay tareas listas para Boards._")

    def short(t):
        extra = ""
        if rel(t, "superseded_by"):
            extra = " → sustituida por %s" % rel(t, "superseded_by")
        reason = next((e["reason"] for e in st.log if e["task_ref"] == t["id"] and e["action"] in ("cancelled", "superseded", "merged", "deferred", "completed")), "")
        return "- **%s** · %s · _%s_%s%s" % (t["id"], t["title"], STATUS_ES[t["status"]], extra,
                                            (". Motivo: " + reason) if reason else "")

    def not_ready_item(t):
        why = next((q["question"] for q in st.open_questions if t["id"] in (q.get("blocks") or [])), None)
        return "- **%s** · %s · _%s_%s. Sustento: %s" % (
            t["id"], t["title"], STATUS_ES[t["status"]], (". Falta: " + why) if why else "", fmt_evidence(t.get("evidence")))

    mode = (cfg.get("boards") or {}).get("mode", "draft")
    if ops:
        lines = ["| Operación | Tarea | Work item | Estado destino | Situación | Motivo |", "|---|---|---|---|---|---|"]
        for op in ops:
            lines.append("| %s | %s | %s | %s | %s | %s |" % (
                OP_ES[op["op"]], op["task_ref"], ("#%s" % op["work_item_id"]) if op.get("work_item_id") else "—",
                md_escape_cell(op.get("target_state")), op["status"], md_escape_cell(op["reason"])))
        applied = [o for o in ops if o["status"] == "applied"]
        note = ("Se aplicaron %d operaciones en Azure Boards; el resultado de cada una está en `meeting-state.json`." % len(applied)) if applied \
            else "**Nada se escribió en Azure Boards.** Este es el plan de operaciones pendiente (modo %s)." % mode
        ops_block = note + "\n\n" + "\n".join(lines)
    else:
        ops_block = "_Plan de operaciones no generado. Ejecuta `sprintscribe.py ops-plan`._"

    return tmpl("01-azure-boards-tasks.md.tmpl").substitute(
        project_name=st.project_name(pid),
        meeting_label=meeting_label(st),
        sprint=st.meeting.get("sprint") or "no identificado",
        boards_mode=mode,
        version=__version__,
        summary_table=summary,
        ready_tasks="\n---\n\n".join(render_task(st, t) for t in ready) or "_Ninguna._",
        not_ready_tasks="\n".join(not_ready_item(t) for t in pending) or "_Ninguna._",
        cancelled_tasks="\n".join(short(t) for t in closed) or "_Ninguna._",
        ops_block=ops_block,
    )


def render_objective_doc(st, p):
    obj = p.get("sprint_objective") or {}
    cands = obj.get("candidates") or []
    cand_block = ""
    if cands:
        cand_block = "\n**Objetivos candidatos** (la reunión no permite fijar uno solo)\n\n" + \
            "\n".join("- %s — _Respaldo:_ %s" % (c["statement"], c["support"]) for c in cands) + "\n"
    roadmap = sorted(p.get("roadmap") or [], key=lambda s: s["order"])
    rows = ["| # | Paso | Tipo | Responsable | Tareas | Depende de | Duración inferida |", "|---|---|---|---|---|---|---|"]
    details = []
    for s in roadmap:
        kind = "Acordado" if s["kind"] == "agreed" else "*Recomendado*"
        rows.append("| %s | %s | %s | %s | %s | %s | %s |" % (
            s["order"], md_escape_cell(s["step"]), kind, md_escape_cell(s.get("owner") or "Por definir"),
            md_escape_cell(or_dash(s.get("task_refs"))), md_escape_cell(or_dash(s.get("depends_on"))),
            md_escape_cell(s["duration"]["range"])))
        conf = s["duration"].get("confidence")
        details.append("**%s. %s** (%s)\n\n- Propósito: %s\n- Fundamento de la duración: %s%s\n- Riesgos, bloqueos o decisiones pendientes: %s" % (
            s["order"], s["step"], kind, s["purpose"], s["duration"]["basis"],
            (" (confianza %s)" % LEVEL_ES_F[conf]) if conf else "",
            or_dash(s.get("risks"))))
    return tmpl("02-sprint-objective-and-roadmap.md.tmpl").substitute(
        project_name=p["name"],
        meeting_label=meeting_label(st),
        period=obj.get("period") or st.meeting.get("sprint") or "no identificado",
        version=__version__,
        objective=obj.get("statement") or "_No hay tareas confirmadas que permitan inferir un objetivo._",
        expected_result=md_escape_cell(obj.get("expected_result")),
        business_need=md_escape_cell(obj.get("business_need")),
        owners=md_escape_cell(or_dash(obj.get("owners"))),
        participants=md_escape_cell(or_dash(obj.get("participants"))),
        objective_certainty=CERTAINTY_ES.get(obj.get("certainty"), "—"),
        deliverables=bullets(obj.get("deliverables")),
        scope=bullets(obj.get("scope"), "No se delimitó explícitamente."),
        exclusions=bullets(obj.get("exclusions"), "No se mencionaron exclusiones."),
        candidates=cand_block,
        roadmap_table="\n".join(rows) if roadmap else "_Sin hoja de ruta._",
        roadmap_details="\n\n".join(details),
    )


def render_decisions_doc(st, pid, decisions, questions, contradictions):
    def item(d):
        bits = ["**%s** · %s" % (d["id"], d["text"])]
        meta = []
        if d.get("decided_by"):
            meta.append("Decide: %s" % d["decided_by"])
        if d.get("executed_by"):
            meta.append("Ejecuta: %s" % d["executed_by"])
        meta.append("Estado: %s" % DECISION_STATUS_ES[d["status"]])
        if d.get("certainty") and d["certainty"] != "explicit":
            meta.append(CERTAINTY_ES[d["certainty"]])
        if d.get("task_refs"):
            meta.append("Tareas: %s" % ", ".join(d["task_refs"]))
        if d.get("supersedes"):
            meta.append("Reemplaza a: %s" % d["supersedes"])
        if not d.get("project_id"):
            meta.append("transversal")
        out = "- " + bits[0] + "  \n  " + " · ".join(meta)
        if d.get("context"):
            out += "  \n  _Contexto e impacto:_ " + d["context"]
        return out

    def section(pred, empty):
        items = [item(d) for d in decisions if pred(d)]
        return "\n".join(items) if items else "_%s_" % empty

    oq = [("- **%s** · %s%s%s" % (q["id"], q["question"],
                                   (" · Bloquea: " + ", ".join(q["blocks"])) if q.get("blocks") else "",
                                   (" · Preguntar a: " + q["ask"]) if q.get("ask") else "")) for q in questions]
    oq += [item(d) for d in decisions if d["kind"] == "open_question"]
    cs = ["- **%s** · %s%s%s\n%s" % (c["id"], c["text"],
                                    "" if c.get("blocking", True) else " · _no bloqueante_",
                                    (" · Tareas: " + ", ".join(c["task_refs"])) if c.get("task_refs") else "",
                                    "\n".join("  - " + fmt_evidence([e]) for e in c["statements"]))
          for c in contradictions if not c.get("resolution")]
    return tmpl("03-agreements-and-decisions.md.tmpl").substitute(
        project_name=st.project_name(pid),
        meeting_label=meeting_label(st),
        version=__version__,
        confirmed=section(lambda d: d["kind"] == "decision" and d["status"] == "confirmed", "Ninguna."),
        changes=section(lambda d: d["kind"] == "change" or d.get("supersedes") or d["status"] in ("discarded", "superseded"), "Sin cambios respecto a acuerdos anteriores."),
        responsibilities=section(lambda d: d["kind"] == "responsibility", "Sin asignaciones explícitas adicionales a las de las tareas."),
        commitments=section(lambda d: d["kind"] in ("commitment", "dependency"), "Ninguno."),
        risks=section(lambda d: d["kind"] in ("blocker", "risk"), "Ninguno identificado."),
        po_validation=section(lambda d: d["kind"] == "po_validation", "Ninguno."),
        external=section(lambda d: d["kind"] == "external_action", "Ninguna."),
        open_questions="\n".join(oq) if oq else "_Ninguna._",
        contradictions="\n".join(cs) if cs else "_Ninguna._",
    )


def render_log_doc(st, pid, tasks, log):
    rows = ["| # | Acción | Tarea | De → A | Motivo | Decisión |", "|---|---|---|---|---|---|"]
    for e in log:
        t = st.task_by_id.get(e["task_ref"], {})
        change = ""
        if e.get("from") or e.get("to"):
            tr = lambda v: STATUS_ES.get(v, v).lower() if v else "—"
            change = "%s → %s" % (tr(e.get("from")), tr(e.get("to")))
        rows.append("| %s | %s | %s · %s | %s | %s | %s |" % (
            e["id"], ACTION_ES[e["action"]], e["task_ref"], md_escape_cell(t.get("title")),
            md_escape_cell(change), md_escape_cell(e["reason"]), md_escape_cell(e.get("cause_decision"))))
    hist = []
    for t in tasks:
        for h in t.get("history") or []:
            hist.append("- **%s** · %s%s%s" % (t["id"], h["change"], (" — " + h["reason"]) if h.get("reason") else "",
                                               (" (reunión %s)" % h["meeting_id"]) if h.get("meeting_id") else ""))
    return tmpl("04-reconciliation-log.md.tmpl").substitute(
        project_name=st.project_name(pid),
        meeting_label=meeting_label(st),
        version=__version__,
        log_table="\n".join(rows) if log else "_Sin cambios: todas las tareas se registraron tal como se propusieron._",
        history=("## Historial de cambios por tarea\n\n" + "\n".join(hist)) if hist else "",
    )


def filter_state(data, pid):
    st = State(data)
    tasks = st.tasks_of(pid)
    ids = {t["id"] for t in tasks}
    out = {
        "schema_version": data["schema_version"],
        "meeting": data["meeting"],
        "projects": [p for p in st.projects if p["id"] == pid],
        "tasks": tasks,
        "decisions": [d for d in st.decisions if d.get("project_id") in (pid, None)
                      or set(d.get("task_refs") or []) & ids],
        "contradictions": [c for c in st.contradictions if not c.get("task_refs") or set(c["task_refs"]) & ids],
        "open_questions": [q for q in st.open_questions if q.get("project_id") in (pid, None)
                           or set(q.get("blocks") or []) & ids],
        "reconciliation_log": [e for e in st.log if e["task_ref"] in ids],
        "ops_plan": [o for o in st.ops if o["task_ref"] in ids],
    }
    if data.get("notes"):
        out["notes"] = data["notes"]
    return out


def meeting_folder_name(meeting):
    if meeting.get("date"):
        return meeting["date"]
    if meeting.get("sprint"):
        return slug(meeting["sprint"])
    return meeting["id"]


def resolve_output_dir(base, meeting_id):
    """No sobrescribe documentacion de otra reunion: agrega -v2, -v3..."""
    n = 1
    while True:
        cand = base if n == 1 else base.with_name("%s-v%d" % (base.name, n))
        state_file = cand / "meeting-state.json"
        if not cand.exists() or not any(cand.iterdir()):
            return cand
        if state_file.is_file():
            try:
                if load_json(state_file).get("meeting", {}).get("id") == meeting_id:
                    return cand
            except (ValueError, OSError):
                pass
        n += 1


def render_all(data, out_root, cfg):
    st = State(data)
    out_root = Path(out_root)
    written = []
    groups = [p["id"] for p in st.projects]
    if any(t["project_id"] == PENDING_PROJECT for t in st.tasks):
        groups.append(PENDING_PROJECT)
    for pid in groups:
        sub = filter_state(data, pid)
        fst = State(sub)
        folder = PENDING_FOLDER if pid == PENDING_PROJECT else pid
        target = resolve_output_dir(out_root / folder / meeting_folder_name(st.meeting), st.meeting["id"])
        files = {
            "01-azure-boards-tasks.md": render_tasks_doc(fst, pid, fst.tasks, fst.ops, cfg),
            "03-agreements-and-decisions.md": render_decisions_doc(fst, pid, fst.decisions, fst.open_questions, fst.contradictions),
            "04-reconciliation-log.md": render_log_doc(fst, pid, fst.tasks, fst.log),
        }
        if pid != PENDING_PROJECT:
            files["02-sprint-objective-and-roadmap.md"] = render_objective_doc(fst, fst.projects[0])
        for name, text in sorted(files.items()):
            write_text(target / name, text)
        dump_json(sub, target / "meeting-state.json")
        written.append(str(target))
    return written


# ---------------------------------------------------------------------------
# merge (ledger acumulado por proyecto)
# ---------------------------------------------------------------------------
TRACKED = (("status", "estado"), ("owner", "responsable"), ("title", "titulo"),
           ("acceptance_criterion", "criterio de aceptacion"), ("priority", "prioridad"))


def ledger_path(docs_root, pid):
    folder = PENDING_FOLDER if pid == PENDING_PROJECT else pid
    return Path(docs_root) / folder / "_state" / "project-state.json"


def merge_into_ledger(data, docs_root, only=None):
    st = State(data)
    mid = st.meeting["id"]
    report = {}
    groups = [p["id"] for p in st.projects] + ([PENDING_PROJECT] if any(t["project_id"] == PENDING_PROJECT for t in st.tasks) else [])
    for pid in groups:
        if only and pid != only:
            continue
        path = ledger_path(docs_root, pid)
        ledger = load_json(path) if path.is_file() else {
            "ledger_version": "1.0", "project": None, "meetings": [], "tasks": {},
            "decisions": [], "reconciliation_log": [], "updated_at": None}
        if pid != PENDING_PROJECT:
            ledger["project"] = {k: v for k, v in st.project_by_id[pid].items() if k not in ("roadmap", "sprint_objective")}
            ledger["project"]["last_objective"] = st.project_by_id[pid].get("sprint_objective")
        changes, warnings = [], []
        for t in [t for t in st.tasks if t["project_id"] == pid]:
            prev = ledger["tasks"].get(t["id"])
            new = json.loads(json.dumps(t))
            hist = list((prev or {}).get("history") or [])
            for h in t.get("history") or []:
                if h not in hist:
                    hist.append(h)
            if prev is None:
                changes.append({"task": t["id"], "change": "nueva", "status": t["status"]})
                hist.append({"meeting_id": mid, "change": "Registrada con estado %s" % t["status"], "reason": None})
            else:
                if similarity(prev["title"], t["title"]) < 0.45 and prev.get("status") not in CLOSED:
                    warnings.append("%s: el titulo cambio por completo ('%s' -> '%s'); confirma que no es una colision de ID" % (t["id"], prev["title"], t["title"]))
                reason = next((e["reason"] for e in st.log if e["task_ref"] == t["id"]), None)
                for key, label in TRACKED:
                    if prev.get(key) != t.get(key):
                        entry = {"meeting_id": mid, "change": "%s: %s -> %s" % (label, prev.get(key), t.get(key)), "reason": reason}
                        if entry not in hist:
                            hist.append(entry)
                        changes.append({"task": t["id"], "change": label, "from": prev.get(key), "to": t.get(key)})
                if not (new.get("boards") or {}).get("work_item_id") and (prev.get("boards") or {}).get("work_item_id"):
                    new["boards"] = prev["boards"]
            new["history"] = hist
            new["last_meeting"] = mid
            ledger["tasks"][t["id"]] = new
        for d in st.decisions:
            if d.get("project_id") in (pid, None):
                entry = dict(d, meeting_id=mid)
                if not any(x.get("id") == d["id"] and x.get("meeting_id") == mid for x in ledger["decisions"]):
                    ledger["decisions"].append(entry)
        ids = {t["id"] for t in st.tasks if t["project_id"] == pid}
        for e in st.log:
            if e["task_ref"] in ids:
                entry = dict(e, meeting_id=e.get("meeting_id") or mid)
                if not any(x.get("id") == e["id"] and x.get("meeting_id") == entry["meeting_id"] for x in ledger["reconciliation_log"]):
                    ledger["reconciliation_log"].append(entry)
        if not any(m["id"] == mid for m in ledger["meetings"]):
            ledger["meetings"].append({"id": mid, "date": st.meeting.get("date"), "type": st.meeting["type"], "merged_at": now_iso()})
        ledger["updated_at"] = now_iso()
        dump_json(ledger, path)
        report[pid] = {"ledger": str(path), "changes": changes, "warnings": warnings}
    return report


def next_task_number(task_ids):
    nums = [int(i.split("-T")[1]) for i in task_ids if "-T" in i and i.split("-T")[1].isdigit()]
    return (max(nums) if nums else 0) + 1


# ---------------------------------------------------------------------------
# export
# ---------------------------------------------------------------------------
EXPORT_COLUMNS = ("id", "project_id", "project_name", "title", "description", "acceptance_criterion",
                  "work_item_type", "owner", "priority", "effort_range", "effort_level", "effort_confidence",
                  "use_case", "epic", "feature", "story", "sprint", "depends_on", "status", "work_item_id")


def export_rows(data, include_all=False):
    st = State(data)
    rows = []
    for t in st.tasks:
        if not include_all and t["status"] not in READY:
            continue
        hh = t.get("hierarchy_hint") or {}
        eff = t.get("effort") or {}
        rows.append({
            "id": t["id"], "project_id": t["project_id"], "project_name": st.project_name(t["project_id"]),
            "title": t["title"], "description": t.get("description") or "",
            "acceptance_criterion": t.get("acceptance_criterion") or "",
            "work_item_type": t.get("work_item_type") or "task", "owner": t.get("owner") or "",
            "priority": t.get("priority") if t.get("priority") is not None else "",
            "effort_range": eff.get("range", ""), "effort_level": eff.get("level", ""),
            "effort_confidence": eff.get("confidence", ""),
            "use_case": hh.get("use_case") or "", "epic": hh.get("epic") or "",
            "feature": hh.get("feature") or "", "story": hh.get("story") or "",
            "sprint": st.meeting.get("sprint") or "", "depends_on": ";".join(t.get("depends_on") or []),
            "status": t["status"], "work_item_id": (t.get("boards") or {}).get("work_item_id") or "",
        })
    return rows


# ---------------------------------------------------------------------------
# check-expectations
# ---------------------------------------------------------------------------
def _pattern(p):
    """Quita tildes y mayusculas pero conserva la sintaxis de regex."""
    p = unicodedata.normalize("NFKD", p).encode("ascii", "ignore").decode().lower()
    return p.replace(".", " ")


def _matches(task, patterns):
    hay = normalize(task.get("title", "") + " " + (task.get("description") or ""))
    return all(re.search(_pattern(p), hay) for p in patterns)


def check_expectations(data, exp, cfg=None):
    results = []
    errors, _ = validate_state(data, cfg)
    results.append((not errors, "El estado pasa validate" + ("" if not errors else ": " + "; ".join(errors[:5]))))
    if errors:
        return results
    st = State(data)

    for spec in exp.get("tasks", []):
        found = [t for t in st.tasks if _matches(t, spec["match"])]
        label = "Tarea %s" % spec["match"]
        if not found:
            results.append((False, label + ": no se encontro"))
            continue
        ok = True
        msgs = []
        if "status_in" in spec and not any(t["status"] in spec["status_in"] for t in found):
            ok = False
            msgs.append("estado %s, esperado %s" % ([t["status"] for t in found], spec["status_in"]))
        cand = [t for t in found if "status_in" not in spec or t["status"] in spec["status_in"]] or found
        if "owner" in spec and not any(normalize(t.get("owner") or "") == normalize(spec["owner"] or "") for t in cand):
            ok = False
            msgs.append("responsable %s, esperado %s" % ([t.get("owner") for t in cand], spec["owner"]))
        if "project" in spec and not any(t["project_id"] == spec["project"] for t in cand):
            ok = False
            msgs.append("proyecto %s, esperado %s" % ([t["project_id"] for t in cand], spec["project"]))
        if "work_item_id" in spec and not any((t.get("boards") or {}).get("work_item_id") == spec["work_item_id"] for t in cand):
            ok = False
            msgs.append("work item esperado %s" % spec["work_item_id"])
        results.append((ok, label + (": ok" if ok else ": " + "; ".join(msgs))))

    for spec in exp.get("forbidden", []):
        bad = [t for t in st.tasks if _matches(t, spec["match"]) and
               ("status_in" not in spec or t["status"] in spec["status_in"])]
        results.append((not bad, "Prohibido %s %s" % (spec["match"], spec.get("status_in", "")) +
                        (": ok" if not bad else ": aparece en %s" % [t["id"] for t in bad])))

    if "ready_count" in exp:
        n = len([t for t in st.tasks if t["status"] in READY])
        lo, hi = exp["ready_count"].get("min", 0), exp["ready_count"].get("max", 10 ** 6)
        results.append((lo <= n <= hi, "Tareas listas: %d (esperado %s-%s)" % (n, lo, hi)))

    if "projects" in exp:
        got = sorted(st.project_by_id)
        results.append((got == sorted(exp["projects"]), "Proyectos %s (esperado %s)" % (got, sorted(exp["projects"]))))

    if "pending_project_tasks_min" in exp:
        n = len([t for t in st.tasks if t["project_id"] == PENDING_PROJECT])
        results.append((n >= exp["pending_project_tasks_min"], "Tareas con proyecto pendiente: %d" % n))

    for spec in exp.get("reconciliation", []):
        hits = [e for e in st.log if e["action"] == spec["action"] and
                (not spec.get("task_match") or _matches(st.task_by_id.get(e["task_ref"], {}), spec["task_match"]))]
        results.append((bool(hits), "Reconciliacion '%s' %s" % (spec["action"], spec.get("task_match", "")) + (": ok" if hits else ": no registrada")))

    for key, label, coll in (("open_questions_min", "Preguntas abiertas", st.open_questions),
                             ("contradictions_min", "Contradicciones", st.contradictions)):
        if key in exp:
            results.append((len(coll) >= exp[key], "%s: %d (minimo %d)" % (label, len(coll), exp[key])))
    if "open_questions_max" in exp:
        results.append((len(st.open_questions) <= exp["open_questions_max"],
                        "Preguntas abiertas: %d (maximo %d)" % (len(st.open_questions), exp["open_questions_max"])))

    for spec in exp.get("decisions", []):
        hits = [d for d in st.decisions if d["kind"] == spec.get("kind", d["kind"]) and
                all(re.search(_pattern(p), normalize(d["text"])) for p in spec.get("match", []))]
        results.append((bool(hits), "Decision %s %s" % (spec.get("kind", ""), spec.get("match", "")) + (": ok" if hits else ": no encontrada")))

    for spec in exp.get("ops", []):
        hits = [o for o in st.ops if o["op"] == spec["op"] and
                ("work_item_id" not in spec or o.get("work_item_id") == spec["work_item_id"]) and
                ("status" not in spec or o["status"] == spec["status"]) and
                (not spec.get("task_match") or _matches(st.task_by_id.get(o["task_ref"], {}), spec["task_match"]))]
        results.append((bool(hits), "Operacion %s" % spec + (": ok" if hits else ": no encontrada")))
    for spec in exp.get("forbid_ops", []):
        hits = [o for o in st.ops if o["op"] == spec["op"] and
                (not spec.get("task_match") or _matches(st.task_by_id.get(o["task_ref"], {}), spec["task_match"]))]
        results.append((not hits, "Operacion prohibida %s" % spec + (": ok" if not hits else ": aparece")))
    if exp.get("no_applied_ops"):
        applied = [o for o in st.ops if o["status"] == "applied"]
        results.append((not applied, "Ninguna operacion reportada como aplicada" + ("" if not applied else ": %d aplicadas" % len(applied))))
    return results


# ---------------------------------------------------------------------------
# context
# ---------------------------------------------------------------------------
def build_context(cfg, used):
    docs_root = Path(cfg["docs_root"])
    ledgers = {}
    if docs_root.is_dir():
        for path in sorted(docs_root.glob("*/_state/project-state.json")):
            led = load_json(path)
            tasks = led.get("tasks", {})
            pid = path.parent.parent.name
            ledgers[pid] = {
                "ledger": str(path),
                "key": (led.get("project") or {}).get("key"),
                "meetings": [m["id"] for m in led.get("meetings", [])],
                "next_task_id_number": next_task_number(tasks.keys()),
                "open_tasks": [
                    {"id": t["id"], "title": t["title"], "status": t["status"], "owner": t.get("owner"),
                     "work_item_id": (t.get("boards") or {}).get("work_item_id")}
                    for t in tasks.values() if t["status"] not in CLOSED + DONE],
                "closed_task_ids": [t["id"] for t in tasks.values() if t["status"] in CLOSED + DONE],
            }
    boards = cfg.get("boards") or {}
    return {
        "sprintscribe_version": __version__,
        "config_files": used or ["(sin archivo: valores por defecto)"],
        "config_errors": config_errors(cfg),
        "docs_root": str(docs_root),
        "inbox": str(docs_root / cfg.get("inbox_dir", "_inbox")),
        "po": cfg.get("po"),
        "roster": [r["name"] for r in cfg.get("roster", [])],
        "projects": [{"id": p["id"], "key": p["key"], "name": p["name"], "aliases": p.get("aliases", [])}
                     for p in cfg.get("projects", [])],
        "effort_convention": cfg.get("effort_convention"),
        "boards": {"mode": boards.get("mode", "draft"), "channel": boards.get("channel", "none"),
                   "org": boards.get("org"), "project": boards.get("project"), "process": boards.get("process"),
                   "state_mapping": boards.get("state_mapping", {})},
        "uploader": {"status": (cfg.get("uploader") or {}).get("status", "pending")},
        "token_present": any(os.environ.get(v) for v in ("AZURE_DEVOPS_PAT", "AZURE_DEVOPS_EXT_PAT", "SYSTEM_ACCESSTOKEN")),
        "ledgers": ledgers,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _print(text):
    sys.stdout.write(text if text.endswith("\n") else text + "\n")


def cmd_context(args, cfg, used):
    _print(json.dumps(build_context(cfg, used), ensure_ascii=False, indent=2))
    return 0


def cmd_validate(args, cfg, used):
    data = load_json(args.state)
    errors, warnings = validate_state(data, cfg)
    if args.json:
        _print(json.dumps({"ok": not errors, "errors": errors, "warnings": warnings}, ensure_ascii=False, indent=2))
    else:
        for e in errors:
            _print("ERROR  " + e)
        for w in warnings:
            _print("AVISO  " + w)
        st = State(data)
        ready = [t for t in st.tasks if t["status"] in READY]
        no_owner = [t["id"] for t in ready if not t.get("owner")]
        _print("%s · %d proyectos · %d tareas (%d listas, %d descartadas) · %d decisiones · sin responsable: %s" % (
            "OK" if not errors else "FALLA", len(st.projects), len(st.tasks), len(ready),
            len([t for t in st.tasks if t["status"] in CLOSED]), len(st.decisions), or_dash(no_owner)))
    return 1 if errors else 0


def cmd_ops_plan(args, cfg, used):
    data = load_json(args.state)
    errors, _ = validate_state(data, cfg)
    if errors:
        _print("El estado no pasa validate; corrigelo antes de planificar operaciones.")
        return 1
    snapshot = load_snapshot(args.snapshot)
    ops = build_ops_plan(data, snapshot, cfg)
    data["ops_plan"] = ops
    if not args.dry_run:
        dump_json(data, args.state)
    for o in ops:
        _print("%-13s %-10s %-8s %-13s %s" % (OP_ES[o["op"]], o["task_ref"],
                                             ("#%s" % o["work_item_id"]) if o.get("work_item_id") else "-",
                                             o["status"], o["reason"]))
    if snapshot is None:
        _print("Sin snapshot de Azure Boards: la deduplicacion contra Boards queda pendiente.")
    return 0


def cmd_render(args, cfg, used):
    data = load_json(args.state)
    errors, warnings = validate_state(data, cfg)
    if errors and not args.force:
        _print("El estado no pasa validate (%d errores). Corrigelo o usa --force." % len(errors))
        return 1
    out = args.out or cfg["docs_root"]
    for path in render_all(data, out, cfg):
        _print("Escrito: " + path)
    return 0


def cmd_merge(args, cfg, used):
    data = load_json(args.state)
    errors, _ = validate_state(data, cfg)
    if errors:
        _print("El estado no pasa validate; no se actualiza el ledger.")
        return 1
    report = merge_into_ledger(data, args.docs_root or cfg["docs_root"], args.project)
    _print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def cmd_export(args, cfg, used):
    data = load_json(args.state)
    rows = export_rows(data, args.all)
    if args.format == "json":
        text = json.dumps({"meeting": data["meeting"]["id"], "tasks": rows}, ensure_ascii=False, indent=2) + "\n"
    else:
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=EXPORT_COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
        text = buf.getvalue()
    if args.out:
        write_text(args.out, text)
        _print("Escrito: %s (%d tareas)" % (args.out, len(rows)))
    else:
        sys.stdout.write(text)
    return 0


def cmd_check(args, cfg, used):
    data = load_json(args.state)
    exp = load_json(args.expected)
    results = check_expectations(data, exp, cfg)
    for ok, msg in results:
        _print(("PASA   " if ok else "FALLA  ") + msg)
    failed = len([r for r in results if not r[0]])
    _print("%d/%d expectativas cumplidas" % (len(results) - failed, len(results)))
    return 1 if failed else 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="sprintscribe", description="Capa determinista de SprintScribe.")
    ap.add_argument("--config", help="archivo de configuracion explicito (ignora usuario y workspace)")
    ap.add_argument("--version", action="version", version="sprintscribe " + __version__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("context", help="configuracion efectiva, ledgers previos e IDs libres")

    p = sub.add_parser("validate", help="valida un meeting-state.json")
    p.add_argument("state")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("ops-plan", help="planifica operaciones contra Azure Boards (no escribe en Boards)")
    p.add_argument("state")
    p.add_argument("--snapshot", help="JSON con work items existentes (de MCP o del uploader)")
    p.add_argument("--dry-run", action="store_true", help="no guarda ops_plan en el estado")

    p = sub.add_parser("render", help="genera los documentos por proyecto")
    p.add_argument("state")
    p.add_argument("--out", help="raiz de salida (por defecto docs_root)")
    p.add_argument("--force", action="store_true", help="renderiza aunque haya errores (solo para depurar)")

    p = sub.add_parser("merge", help="actualiza el ledger acumulado de cada proyecto")
    p.add_argument("state")
    p.add_argument("--docs-root")
    p.add_argument("--project")

    p = sub.add_parser("export", help="exporta tareas listas para el adaptador de Excel")
    p.add_argument("state")
    p.add_argument("--format", choices=("json", "csv"), default="json")
    p.add_argument("--out")
    p.add_argument("--all", action="store_true", help="incluye tareas no listas")

    p = sub.add_parser("check-expectations", help="califica un estado contra expected.json")
    p.add_argument("state")
    p.add_argument("expected")

    args = ap.parse_args(argv)
    cfg, used = load_config(args.config)
    handler = {
        "context": cmd_context, "validate": cmd_validate, "ops-plan": cmd_ops_plan, "render": cmd_render,
        "merge": cmd_merge, "export": cmd_export, "check-expectations": cmd_check,
    }[args.cmd]
    return handler(args, cfg, used)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
