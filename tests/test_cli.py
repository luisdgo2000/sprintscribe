#!/usr/bin/env python3
"""Pruebas de la capa determinista de SprintScribe.

    python3 -m unittest discover -s tests -v

Cubren los 12 casos de calidad con sus estados de referencia (golden), los
rechazos que debe hacer validate y el comportamiento de ops-plan, render,
merge, export y la resolucion de configuracion.
"""

import copy
import importlib.util
import json
import os
import re
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "sprintscribe"
CASES = ROOT / "tests" / "cases"
FIXTURE_CONFIG = ROOT / "tests" / "fixtures" / "config.json"

_spec = importlib.util.spec_from_file_location("sprintscribe", SKILL / "scripts" / "sprintscribe.py")
ss = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ss)


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def config():
    cfg, _ = ss.load_config(FIXTURE_CONFIG)
    return cfg


def case_dirs():
    return sorted(d for d in CASES.iterdir() if d.is_dir())


def case(prefix):
    return next(d for d in case_dirs() if d.name.startswith(prefix))


def with_ops(case_dir, cfg):
    state = load(case_dir / "golden-state.json")
    snap = case_dir / "boards-snapshot.json"
    state["ops_plan"] = ss.build_ops_plan(state, ss.load_snapshot(snap) if snap.exists() else None, cfg)
    return state


class GoldenCases(unittest.TestCase):
    def test_twelve_cases_exist(self):
        self.assertEqual(len(case_dirs()), 12)
        for d in case_dirs():
            for f in ("transcript.md", "expected.json", "golden-state.json"):
                self.assertTrue((d / f).is_file(), "%s/%s" % (d.name, f))

    def test_goldens_validate(self):
        cfg = config()
        for d in case_dirs():
            with self.subTest(case=d.name):
                errors, _ = ss.validate_state(load(d / "golden-state.json"), cfg)
                self.assertEqual(errors, [])

    def test_goldens_meet_expectations(self):
        cfg = config()
        for d in case_dirs():
            with self.subTest(case=d.name):
                results = ss.check_expectations(with_ops(d, cfg), load(d / "expected.json"), cfg)
                failed = [m for ok, m in results if not ok]
                self.assertEqual(failed, [])

    def test_skill_example_is_valid(self):
        state = load(SKILL / "assets" / "examples" / "example-meeting-state.json")
        errors, _ = ss.validate_state(state, config())
        self.assertEqual(errors, [])


class ValidateRejects(unittest.TestCase):
    def setUp(self):
        self.cfg = config()
        self.base = load(case("04") / "golden-state.json")

    def errors_after(self, mutate):
        state = copy.deepcopy(self.base)
        mutate(state)
        errors, _ = ss.validate_state(state, self.cfg)
        return errors

    def task(self, state, tid):
        return next(t for t in state["tasks"] if t["id"] == tid)

    def assertRejects(self, mutate, pattern):
        errors = self.errors_after(mutate)
        self.assertTrue(any(re.search(pattern, e) for e in errors), errors)

    def test_cancelled_task_in_roadmap(self):
        self.assertRejects(lambda s: s["projects"][0]["roadmap"][0]["task_refs"].append("PCL-T2"), "descartada")

    def test_cancelled_task_reactivated(self):
        self.assertRejects(lambda s: self.task(s, "PCL-T2").update(status="confirmed"), "sustituida")

    def test_multiple_acceptance_criteria(self):
        self.assertRejects(lambda s: self.task(s, "PCL-T1").update(
            acceptance_criterion="- Se envia el correo\n- Se cambia la contrasena"), "UNO solo")

    def test_missing_acceptance_criterion(self):
        self.assertRejects(lambda s: self.task(s, "PCL-T1").update(acceptance_criterion=None), "criterio")

    def test_unknown_project(self):
        self.assertRejects(lambda s: self.task(s, "PCL-T1").update(project_id="otro"), "PENDING")

    def test_story_points_without_convention(self):
        self.assertRejects(lambda s: self.task(s, "PCL-T1")["effort"].update(range="5 SP"), "Story Points")

    def test_effort_without_time_unit(self):
        self.assertRejects(lambda s: self.task(s, "PCL-T1")["effort"].update(range="mediano"), "unidad temporal")

    def test_generic_title(self):
        self.assertRejects(lambda s: self.task(s, "PCL-T1").update(title="Revisar tema"), "generico")

    def test_superseded_symmetry(self):
        self.assertRejects(lambda s: self.task(s, "PCL-T4")["relations"].update(supersedes=[]), "superseded_by")

    def test_cancelled_without_log(self):
        self.assertRejects(lambda s: s.update(reconciliation_log=[e for e in s["reconciliation_log"] if e["task_ref"] != "PCL-T2"]),
                           "reconciliation_log")

    def test_dependency_on_cancelled(self):
        self.assertRejects(lambda s: self.task(s, "PCL-T3")["depends_on"].append("PCL-T2"), "descartada")

    def test_roadmap_order_must_follow_dependencies(self):
        self.assertRejects(lambda s: s["projects"][0]["roadmap"][0].update(depends_on=[3]), "ordena por dependencias")

    def test_blocking_contradiction_keeps_task_unconfirmed(self):
        def mutate(s):
            s["contradictions"] = [{"id": "C1", "text": "Dos responsables", "task_refs": ["PCL-T1"],
                                    "statements": [{"quote": "Ana"}, {"quote": "Carlos"}], "resolution": None}]
        self.assertRejects(mutate, "contradiccion bloqueante")

    def test_applied_operation_in_draft_mode(self):
        def mutate(s):
            s["ops_plan"] = [{"op": "create", "task_ref": "PCL-T1", "status": "applied", "reason": "x",
                              "result": {"id": 1}}]
        self.assertRejects(mutate, "sin integracion")

    def test_applied_operation_needs_real_result(self):
        def mutate(s):
            s["ops_plan"] = [{"op": "create", "task_ref": "PCL-T1", "status": "failed", "reason": "x"}]
        self.assertRejects(mutate, "resultado real")

    def test_schema_rejects_unknown_status(self):
        self.assertRejects(lambda s: self.task(s, "PCL-T1").update(status="done"), "no es uno de")

    def test_duplicate_ids(self):
        self.assertRejects(lambda s: s["tasks"].append(copy.deepcopy(s["tasks"][0])), "duplicado")


class OpsPlan(unittest.TestCase):
    def setUp(self):
        self.cfg = config()

    def test_existing_items_not_duplicated(self):
        state = with_ops(case("11"), self.cfg)
        creates = [o["task_ref"] for o in state["ops_plan"] if o["op"] == "create"]
        self.assertEqual(creates, ["PCL-T6"])

    def test_cancelled_with_verified_id_changes_state_never_deletes(self):
        state = load(case("04") / "golden-state.json")
        next(t for t in state["tasks"] if t["id"] == "PCL-T2")["boards"] = {"work_item_id": 4513, "match_confidence": "verified"}
        snap = [{"id": 4513, "title": "Migrar el formulario de registro a la nueva librería de componentes", "state": "New"}]
        ops = ss.build_ops_plan(state, snap, self.cfg)
        op = next(o for o in ops if o["task_ref"] == "PCL-T2")
        self.assertEqual((op["op"], op["target_state"], op["status"]), ("change_state", "Removed", "pending"))
        self.assertFalse(any(o["op"] == "delete" for o in ops))

    def test_unmapped_target_state_goes_to_review(self):
        cfg = copy.deepcopy(self.cfg)
        cfg["boards"]["state_mapping"] = {}
        state = load(case("04") / "golden-state.json")
        next(t for t in state["tasks"] if t["id"] == "PCL-T2")["boards"] = {"work_item_id": 4513}
        op = next(o for o in ss.build_ops_plan(state, None, cfg) if o["task_ref"] == "PCL-T2")
        self.assertEqual(op["status"], "needs_review")

    def test_two_close_candidates_go_to_review(self):
        state = load(case("12") / "golden-state.json")
        snap = [{"id": 1, "title": "Reporte mensual de facturas canceladas para contabilidad"},
                {"id": 2, "title": "Generar reporte de facturas canceladas para contabilidad"}]
        op = ss.build_ops_plan(state, snap, self.cfg)[0]
        self.assertEqual(op["op"], "needs_review")
        self.assertEqual(len(op["candidates"]), 2)

    def test_no_snapshot_means_pending_creates_only(self):
        state = with_ops(case("12"), self.cfg)
        self.assertTrue(all(o["status"] == "pending" for o in state["ops_plan"]))
        errors, _ = ss.validate_state(state, self.cfg)
        self.assertEqual(errors, [])


class RenderMergeExport(unittest.TestCase):
    def setUp(self):
        self.cfg = config()
        self.tmp = Path(tempfile.mkdtemp(prefix="sprintscribe-test-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def read_tree(self, root):
        return {str(p.relative_to(root)): p.read_text(encoding="utf-8") for p in sorted(root.rglob("*")) if p.is_file()}

    def test_render_writes_all_documents_per_project(self):
        state = load(case("02") / "golden-state.json")
        written = ss.render_all(state, self.tmp, self.cfg)
        self.assertEqual(len(written), 2)
        for folder in written:
            names = sorted(p.name for p in Path(folder).iterdir())
            self.assertEqual(names, ["01-azure-boards-tasks.md", "02-sprint-objective-and-roadmap.md",
                                     "03-agreements-and-decisions.md", "04-reconciliation-log.md", "meeting-state.json"])
        fel = (self.tmp / "facturacion-electronica" / "2026-10-07" / "01-azure-boards-tasks.md").read_text(encoding="utf-8")
        self.assertIn("FEL-T1", fel)
        self.assertNotIn("DLV-T1", fel, "las tareas de un proyecto no deben aparecer en otro")

    def test_render_is_deterministic(self):
        state = load(case("04") / "golden-state.json")
        a, b = self.tmp / "a", self.tmp / "b"
        ss.render_all(state, a, self.cfg)
        ss.render_all(state, b, self.cfg)
        self.assertEqual(self.read_tree(a), self.read_tree(b))

    def test_render_never_overwrites_another_meeting(self):
        state = load(case("04") / "golden-state.json")
        ss.render_all(state, self.tmp, self.cfg)
        ss.render_all(state, self.tmp, self.cfg)  # misma reunion: reescribe la misma carpeta
        other = copy.deepcopy(state)
        other["meeting"]["id"] = "2026-10-09-otra-reunion"
        written = ss.render_all(other, self.tmp, self.cfg)
        self.assertTrue(written[0].endswith("2026-10-09-v2"))
        self.assertEqual(sorted(p.name for p in (self.tmp / "portal-clientes").iterdir()), ["2026-10-09", "2026-10-09-v2"])

    def test_cancelled_task_kept_as_history_not_as_ready(self):
        state = load(case("04") / "golden-state.json")
        ss.render_all(state, self.tmp, self.cfg)
        doc = (self.tmp / "portal-clientes" / "2026-10-09" / "01-azure-boards-tasks.md").read_text(encoding="utf-8")
        ready, history = doc.split("## Tareas que todavía no deben subirse")[0], doc.split("## Descartadas")[1]
        self.assertNotIn("### PCL-T2", ready)
        self.assertIn("PCL-T2", history)
        self.assertIn("sustituida por PCL-T4", history)

    def test_pending_project_tasks_get_their_own_folder(self):
        state = load(case("07") / "golden-state.json")
        t = copy.deepcopy(state["tasks"][0])
        t.update(id="PEND-T1", project_id="PENDING", title="Definir proveedor de correo transaccional", status="needs_clarification")
        state["tasks"].append(t)
        state["open_questions"].append({"id": "Q2", "question": "¿A qué proyecto pertenece?", "blocks": ["PEND-T1"]})
        self.assertEqual(ss.validate_state(state, self.cfg)[0], [])
        ss.render_all(state, self.tmp, self.cfg)
        self.assertTrue((self.tmp / "_pendiente-de-asignar" / "2026-10-14" / "01-azure-boards-tasks.md").is_file())

    def test_merge_second_meeting_preserves_unmentioned_tasks(self):
        d = case("10")
        ss.merge_into_ledger(load(d / "previous-state.json"), self.tmp)
        report = ss.merge_into_ledger(load(d / "golden-state.json"), self.tmp)
        ledger = load(self.tmp / "datalake-ventas" / "_state" / "project-state.json")
        for tid, exp in load(d / "expected.json")["ledger_after_merge"].items():
            self.assertEqual(ledger["tasks"][tid]["status"], exp["status"], tid)
        self.assertEqual([m["id"] for m in ledger["meetings"]], ["2026-10-01-planning-lake", "2026-10-08-seguimiento-lake"])
        t3_history = [h["change"] for h in ledger["tasks"]["DLV-T3"]["history"]]
        self.assertIn("estado: confirmed -> deferred", t3_history)
        changes = {(c["task"], c["change"]) for c in report["datalake-ventas"]["changes"]}
        self.assertIn(("DLV-T4", "nueva"), changes)
        # idempotente
        ss.merge_into_ledger(load(d / "golden-state.json"), self.tmp)
        again = load(self.tmp / "datalake-ventas" / "_state" / "project-state.json")
        self.assertEqual(len(again["decisions"]), len(ledger["decisions"]))
        self.assertEqual(len(again["tasks"]["DLV-T3"]["history"]), len(ledger["tasks"]["DLV-T3"]["history"]))

    def test_context_reports_next_ids_from_ledger(self):
        d = case("10")
        ss.merge_into_ledger(load(d / "previous-state.json"), self.tmp)
        cfg = copy.deepcopy(self.cfg)
        cfg["docs_root"] = str(self.tmp)
        ctx = ss.build_context(cfg, [])
        self.assertEqual(ctx["ledgers"]["datalake-ventas"]["next_task_id_number"], 4)
        self.assertEqual(ctx["uploader"]["status"], "pending")

    def test_export_only_ready_tasks(self):
        rows = ss.export_rows(load(case("04") / "golden-state.json"))
        self.assertEqual([r["id"] for r in rows], ["PCL-T1", "PCL-T3", "PCL-T4"])
        self.assertEqual(set(rows[0]), set(ss.EXPORT_COLUMNS))

    def test_cli_end_to_end(self):
        state_path = self.tmp / "state.json"
        shutil.copy(case("11") / "golden-state.json", state_path)
        base = ["--config", str(FIXTURE_CONFIG)]
        self.assertEqual(ss.main(base + ["validate", str(state_path)]), 0)
        self.assertEqual(ss.main(base + ["ops-plan", str(state_path), "--snapshot", str(case("11") / "boards-snapshot.json")]), 0)
        self.assertTrue(load(state_path)["ops_plan"])
        self.assertEqual(ss.main(base + ["render", str(state_path), "--out", str(self.tmp / "docs")]), 0)
        self.assertEqual(ss.main(base + ["merge", str(state_path), "--docs-root", str(self.tmp / "docs")]), 0)
        self.assertEqual(ss.main(base + ["export", str(state_path), "--format", "csv", "--out", str(self.tmp / "t.csv")]), 0)
        self.assertEqual(ss.main(base + ["check-expectations", str(state_path), str(case("11") / "expected.json")]), 0)
        doc = (self.tmp / "docs" / "portal-clientes" / "2026-10-16" / "01-azure-boards-tasks.md").read_text(encoding="utf-8")
        self.assertIn("Nada se escribió en Azure Boards", doc)


class Configuration(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sprintscribe-cfg-"))
        self.old_home = os.environ.get("SPRINTSCRIBE_HOME")

    def tearDown(self):
        if self.old_home is None:
            os.environ.pop("SPRINTSCRIBE_HOME", None)
        else:
            os.environ["SPRINTSCRIBE_HOME"] = self.old_home
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_workspace_overrides_user(self):
        home = self.tmp / "home"
        home.mkdir()
        (home / "config.json").write_text(json.dumps({"po": {"name": "Brian"}, "boards": {"mode": "draft", "org": "org-usuario"}}))
        ws = self.tmp / "repo"
        (ws / ".sprintscribe").mkdir(parents=True)
        (ws / ".sprintscribe" / "config.json").write_text(json.dumps({"docs_root": "docs", "boards": {"org": "org-equipo"}}))
        os.environ["SPRINTSCRIBE_HOME"] = str(home)
        cfg, used = ss.load_config(cwd=ws)
        self.assertEqual(len(used), 2)
        self.assertEqual(cfg["boards"]["org"], "org-equipo")
        self.assertEqual(cfg["boards"]["mode"], "draft")
        self.assertEqual(Path(cfg["docs_root"]), (ws / "docs").resolve())

    def test_example_config_is_valid(self):
        cfg = load(ROOT / "config" / "sprintscribe.config.example.json")
        self.assertEqual(ss.config_errors(cfg), [])
        self.assertEqual(cfg["boards"]["mode"], "draft")
        self.assertEqual(cfg["uploader"]["status"], "pending")

    def test_no_secrets_in_repository_configs(self):
        pattern = re.compile(r"(pat|token|password|secret)\"\s*:\s*\"[^\"]+", re.I)
        for path in list((ROOT / "config").glob("*.json")) + [FIXTURE_CONFIG]:
            self.assertIsNone(pattern.search(path.read_text(encoding="utf-8")), path)


class Packaging(unittest.TestCase):
    def frontmatter(self, path):
        text = path.read_text(encoding="utf-8")
        m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
        self.assertIsNotNone(m, path)
        fields = {}
        for line in m.group(1).splitlines():
            if ":" in line and not line.startswith(" "):
                k, v = line.split(":", 1)
                fields[k.strip()] = v.strip().strip("'\"")
        return fields, text

    def test_skill_follows_agent_skills_spec(self):
        fields, text = self.frontmatter(SKILL / "SKILL.md")
        self.assertEqual(fields["name"], SKILL.name)
        self.assertRegex(fields["name"], r"^[a-z0-9]+(-[a-z0-9]+)*$")
        self.assertTrue(0 < len(fields["description"]) <= 1024)
        self.assertLess(len(text.splitlines()), 500)
        for link in re.findall(r"\]\(((?:references|assets|scripts)/[^)#]+)\)", text):
            self.assertTrue((SKILL / link).exists(), "enlace roto en SKILL.md: %s" % link)

    def test_agent_template_has_placeholders(self):
        agent = ROOT / "adapters" / "copilot" / "agents" / "sprintscribe.agent.md"
        fields, text = self.frontmatter(agent)
        self.assertIn("description", fields)
        self.assertIn("{{SPRINTSCRIBE_CLI}}", text)

    def test_workspace_install_and_upgrade(self):
        spec = importlib.util.spec_from_file_location("installer", ROOT / "install.py")
        installer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(installer)
        tmp = Path(tempfile.mkdtemp(prefix="sprintscribe-install-"))
        try:
            self.assertEqual(installer.main(["--scope", "workspace", "--target", str(tmp), "--with-mcp"]), 0)
            agent = (tmp / ".github" / "agents" / "sprintscribe.agent.md").read_text(encoding="utf-8")
            self.assertNotIn("{{", agent)
            self.assertIn("python3 .github/skills/sprintscribe/scripts/sprintscribe.py", agent)
            self.assertTrue((tmp / ".github" / "skills" / "sprintscribe" / "SKILL.md").is_file())
            self.assertFalse(list((tmp / ".github" / "skills").rglob("__pycache__")))
            cfg = tmp / ".sprintscribe" / "config.json"
            cfg.write_text('{"po": {"name": "Otra PO"}}', encoding="utf-8")
            self.assertEqual(installer.main(["--scope", "workspace", "--target", str(tmp)]), 0)
            self.assertIn("Otra PO", cfg.read_text(encoding="utf-8"), "reinstalar no debe pisar la configuracion")
            foreign = tmp / ".github" / "agents" / "sprintscribe.agent.md"
            foreign.write_text("agente de otra persona", encoding="utf-8")
            self.assertEqual(installer.main(["--scope", "workspace", "--target", str(tmp)]), 1)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_version_is_consistent(self):
        self.assertEqual((ROOT / "VERSION").read_text().strip(), ss.__version__)


if __name__ == "__main__":
    unittest.main()
