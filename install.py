#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
install.py - Instala SprintScribe para GitHub Copilot.

    python3 install.py --scope user                    # este equipo, todos los workspaces
    python3 install.py --scope workspace --target RUTA # un repositorio del equipo
    python3 install.py --scope user --dry-run          # muestra lo que haria

Scope "user":
    ~/.copilot/skills/sprintscribe/         la skill (formato Agent Skills)
    ~/.copilot/agents/sprintscribe.agent.md el agente orquestador
    ~/.sprintscribe/config.json             configuracion (solo si no existe)

Scope "workspace":
    <repo>/.github/skills/sprintscribe/
    <repo>/.github/agents/sprintscribe.agent.md
    <repo>/.github/prompts/procesar-reunion.prompt.md
    <repo>/.sprintscribe/config.json        (solo si no existe)
    <repo>/.vscode/mcp.json                 (solo con --with-mcp y si no existe)

Nunca sobrescribe una configuracion existente ni archivos que no haya instalado
SprintScribe (salvo --force). Una reinstalacion actualiza la skill y el agente.
Solo biblioteca estandar.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SKILL_SRC = ROOT / "skills" / "sprintscribe"
AGENT_SRC = ROOT / "adapters" / "copilot" / "agents" / "sprintscribe.agent.md"
PROMPT_SRC = ROOT / "adapters" / "copilot" / "prompts" / "procesar-reunion.prompt.md"
MCP_SRC = ROOT / "adapters" / "copilot" / "mcp.example.json"
CONFIG_SRC = ROOT / "config" / "sprintscribe.config.example.json"
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()

MARKER_FILE = ".sprintscribe-install.json"
AGENT_MARKER = "<!-- sprintscribe:installed"


def default_python():
    """El python3 del PATH (estable entre actualizaciones); si no hay, el interprete actual."""
    if os.name != "nt":
        found = shutil.which("python3")
        if found:
            return Path(found).as_posix()
    return Path(sys.executable).as_posix()


def home():
    return Path(os.path.expanduser("~"))


def plan(scope, target, python_cmd):
    if scope == "user":
        copilot = home() / ".copilot"
        skill_dst = copilot / "skills" / "sprintscribe"
        skill_ref = skill_dst.as_posix()
        cli = '"%s" "%s/scripts/sprintscribe.py"' % (python_cmd, skill_ref)
        return {
            "skill": skill_dst,
            "agent": copilot / "agents" / "sprintscribe.agent.md",
            "prompt": None,
            "config": Path(os.environ.get("SPRINTSCRIBE_HOME") or home() / ".sprintscribe") / "config.json",
            "mcp": None,
            "skill_ref": skill_ref,
            "cli": cli,
        }
    t = Path(target).resolve()
    skill_ref = ".github/skills/sprintscribe"
    return {
        "skill": t / ".github" / "skills" / "sprintscribe",
        "agent": t / ".github" / "agents" / "sprintscribe.agent.md",
        "prompt": t / ".github" / "prompts" / "procesar-reunion.prompt.md",
        "config": t / ".sprintscribe" / "config.json",
        "mcp": t / ".vscode" / "mcp.json",
        "skill_ref": skill_ref,
        "cli": "%s %s/scripts/sprintscribe.py" % (python_cmd, skill_ref),
    }


def render_agent(cli, skill_ref):
    text = AGENT_SRC.read_text(encoding="utf-8")
    text = text.replace("{{SPRINTSCRIBE_CLI}}", cli).replace("{{SKILL_DIR}}", skill_ref)
    return text.rstrip() + "\n\n%s v%s -->\n" % (AGENT_MARKER, VERSION)


def is_ours_dir(path):
    return (path / MARKER_FILE).is_file()


def is_ours_file(path):
    try:
        return AGENT_MARKER in path.read_text(encoding="utf-8")
    except OSError:
        return False


def main(argv=None):
    ap = argparse.ArgumentParser(description="Instala SprintScribe para GitHub Copilot.")
    ap.add_argument("--scope", choices=("user", "workspace"), required=True)
    ap.add_argument("--target", help="repositorio destino (scope workspace)")
    ap.add_argument("--python", dest="python_cmd",
                    help="comando de Python que usara el agente (por defecto: el actual en scope user, "
                         "'python3' en scope workspace)")
    ap.add_argument("--with-mcp", action="store_true", help="agrega .vscode/mcp.json de ejemplo (solo lectura)")
    ap.add_argument("--force", action="store_true", help="sobrescribe archivos que no instalo SprintScribe")
    ap.add_argument("--dry-run", action="store_true", help="muestra las acciones sin escribir")
    args = ap.parse_args(argv)

    if args.scope == "workspace" and not args.target:
        ap.error("--target es obligatorio con --scope workspace")
    if args.scope == "workspace" and not Path(args.target).is_dir():
        ap.error("el destino no existe: %s" % args.target)
    python_cmd = args.python_cmd or (default_python() if args.scope == "user" else "python3")
    p = plan(args.scope, args.target, python_cmd)
    actions = []

    def act(desc, fn):
        actions.append(desc)
        if not args.dry_run:
            fn()

    # skill
    dst = p["skill"]
    if dst.exists() and not is_ours_dir(dst) and not args.force:
        print("ALTO: %s existe y no fue instalado por SprintScribe. Usa --force si quieres reemplazarlo." % dst)
        return 1

    def copy_skill():
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(SKILL_SRC, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"))
        (dst / MARKER_FILE).write_text(json.dumps({
            "version": VERSION, "installed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "source": str(ROOT), "scope": args.scope}, indent=2) + "\n", encoding="utf-8")

    act("%s skill -> %s" % ("Actualizar" if dst.exists() else "Instalar", dst), copy_skill)

    # agent
    agent = p["agent"]
    if agent.exists() and not is_ours_file(agent) and not args.force:
        print("ALTO: %s existe y no fue instalado por SprintScribe. Usa --force si quieres reemplazarlo." % agent)
        return 1
    agent_text = render_agent(p["cli"], p["skill_ref"])

    def write_agent():
        agent.parent.mkdir(parents=True, exist_ok=True)
        with open(agent, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(agent_text)

    act("%s agente -> %s (CLI: %s)" % ("Actualizar" if agent.exists() else "Instalar", agent, p["cli"]), write_agent)

    # prompt
    if p["prompt"]:
        prompt = p["prompt"]
        if prompt.exists() and not args.force and prompt.read_text(encoding="utf-8") != PROMPT_SRC.read_text(encoding="utf-8"):
            actions.append("Conservar prompt existente (distinto): %s" % prompt)
        else:
            def write_prompt():
                prompt.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(PROMPT_SRC, prompt)
            act("Instalar prompt -> %s" % prompt, write_prompt)

    # config
    cfg = p["config"]
    if cfg.exists():
        actions.append("Conservar configuracion existente: %s" % cfg)
    else:
        def write_config():
            cfg.parent.mkdir(parents=True, exist_ok=True)
            data = json.loads(CONFIG_SRC.read_text(encoding="utf-8"))
            if args.scope == "user":
                data["docs_root"] = (home() / "SprintScribe" / "documentacion").as_posix()
            cfg.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        act("Crear configuracion -> %s (editala con tu equipo, proyectos y Boards)" % cfg, write_config)

    # mcp
    if p["mcp"] and args.with_mcp:
        mcp = p["mcp"]
        if mcp.exists():
            actions.append("Conservar %s existente: agrega a mano el servidor de adapters/copilot/mcp.example.json" % mcp)
        else:
            def write_mcp():
                mcp.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(MCP_SRC, mcp)
            act("Agregar MCP de Azure DevOps (solo lectura) -> %s" % mcp, write_mcp)

    print(("[simulacion] " if args.dry_run else "") + "SprintScribe v%s · scope %s" % (VERSION, args.scope))
    for a in actions:
        print(" - " + a)
    if not args.dry_run:
        print("\nSiguiente paso: edita la configuracion y abre Copilot Chat en modo agente -> agente 'sprintscribe'.")
        if args.scope == "user":
            print("Comprueba con:  %s context" % p["cli"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
