"""Route MechanicSpec to new_module / extend_module / upgrade_state_only."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import lm_studio
from .logging_setup import get
from .schemas.envelope import MechanicSpec

log = get("plan")

_MODEL = None  # type: ignore[assignment]


def _get_model():
    global _MODEL
    if _MODEL is None:
        from sentence_transformers import SentenceTransformer
        log.info("Loading sentence-transformers model all-MiniLM-L6-v2 (first use)")
        _MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    return _MODEL


def plan(spec: MechanicSpec, site_dir: Path, lm_cfg) -> str:
    """Return one of: 'new_module', 'extend_module', 'upgrade_state_only'."""
    manifest_path = Path(site_dir) / "public" / "spa" / "spa_manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
    else:
        manifest = {"schema_version": "1", "modules": []}
    modules = manifest.get("modules", [])
    manifest_snapshot = [
        {"module_id": m.get("module_id"), "title": m.get("title"), "kind": m.get("kind")}
        for m in modules
    ]

    if not modules:
        log.info(
            "PLAN decision=new_module best_sim=n/a manifest_modules=0 snapshot=%s",
            manifest_snapshot,
        )
        return "new_module"

    model = _get_model()
    spec_text = f"{spec.title}: {spec.intent}"
    module_texts = [f"{m.get('title','')}: {m.get('kind','')}" for m in modules]
    spec_emb = model.encode([spec_text])
    module_embs = model.encode(module_texts)
    sims = model.similarity(spec_emb, module_embs)[0]
    sims_list = [float(x) for x in sims]
    best_idx = max(range(len(sims_list)), key=lambda i: sims_list[i])
    best_sim = sims_list[best_idx]

    if best_sim > 0.85:
        decision = "extend_module"
        rationale = (
            f"cosine_sim={best_sim:.3f} exceeds 0.85 threshold "
            f"(match: {modules[best_idx].get('module_id')})"
        )
    elif best_sim < 0.40:
        decision = "new_module"
        rationale = (
            f"cosine_sim={best_sim:.3f} below 0.40 threshold — unrelated to existing modules"
        )
    else:
        decision, rationale = _lm_judge(spec, modules, sims_list, lm_cfg)

    log.info(
        "PLAN decision=%s best_sim=%.3f manifest_modules=%d rationale=%s snapshot=%s",
        decision,
        best_sim,
        len(modules),
        rationale,
        manifest_snapshot,
    )
    return decision


def _lm_judge(
    spec: MechanicSpec, modules: list[dict], sims: list[float], lm_cfg
) -> tuple[str, str]:
    """Call LM to resolve ambiguous similarity range (0.40–0.85). Returns (decision, rationale)."""
    module_summary = [
        {
            "module_id": m.get("module_id"),
            "title": m.get("title"),
            "kind": m.get("kind"),
            "similarity": round(s, 3),
        }
        for m, s in zip(modules, sims)
    ]
    new_spec_summary = {
        "kind": spec.kind.value if hasattr(spec.kind, "value") else str(spec.kind),
        "title": spec.title,
        "intent": spec.intent,
    }
    system = (
        "You route a new mechanic against existing SPA modules. "
        "Choose exactly one of: new_module, extend_module, upgrade_state_only. "
        'Respond with a single JSON object: {"decision": "...", "rationale": "..."}.'
    )
    user = json.dumps(
        {
            "new_mechanic": new_spec_summary,
            "existing_modules": module_summary,
        },
        indent=2,
    )
    raw = lm_studio.chat_json(lm_cfg, system=system, user=user, task="plan")
    decision = raw.get("decision", "new_module")
    rationale = raw.get("rationale", "")
    if decision not in ("new_module", "extend_module", "upgrade_state_only"):
        log.warning(
            "LM judge returned unknown decision=%r; defaulting to new_module", decision
        )
        decision = "new_module"
        rationale = (
            f"judge emitted unknown decision; fell back to new_module. "
            f"original_rationale={rationale}"
        )
    return decision, rationale
