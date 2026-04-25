"""Manual smoke test for per-task sampling overrides + thinking-mode plumbing.

Run with the project venv:
    .venv/bin/python scripts/smoke_sampling.py

Exits non-zero if any call fails or the merged sampling doesn't match what
the preset asked for. Captures and prints:
  1. The merged (sampling, extra_body) the helper builds for each preset
  2. The actual log line emitted by chat_json showing what went on the wire
  3. The model's response (truncated)
"""
from __future__ import annotations

import dataclasses
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from packages.config_contract import LmStudioConfig
from apps.workflow_engine import config as workflow_config
from apps.workflow_engine import lm_studio

# Capture INFO logs from workflow.lm_studio so we can verify what hit the wire.
log = logging.getLogger("workflow.lm_studio")
log.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter("[%(name)s] %(message)s"))
log.addHandler(handler)

# Each preset = (label, model_id, base cfg overrides, task_overrides for "topic_curation")
QWEN_PRESET = {
    "label": "Qwen 3.6 — instruct preset on topic_curation",
    "model": "qwen3.6-27b-mlx",
    "task_overrides": {
        "topic_curation": {
            "temperature": 0.7,
            "top_p": 0.8,
            "top_k": 20,
            "presence_penalty": 1.5,
            "enable_thinking": False,
        },
    },
    # What _sampling_for should produce for this preset:
    "expected_sampling": {"temperature": 0.7, "top_p": 0.8, "presence_penalty": 1.5},
    "expected_extra_body": {
        "top_k": 20,
        "chat_template_kwargs": {"enable_thinking": False},
    },
}

GEMMA_PRESET = {
    "label": "Gemma 4 — single preset on topic_curation",
    "model": "google/gemma-4-26b-a4b",
    "task_overrides": {
        "topic_curation": {
            "temperature": 1.0,
            "top_p": 0.95,
            "top_k": 64,
            "enable_thinking": False,
        },
    },
    "expected_sampling": {"temperature": 1.0, "top_p": 0.95},
    "expected_extra_body": {
        "top_k": 64,
        "chat_template_kwargs": {"enable_thinking": False},
    },
}


SYSTEM = (
    "You curate the rolling topic statement for a single-inbox website. "
    "Reply with a single JSON object: {\"topic_md\": \"<markdown under 100 words>\"}."
)
USER = json.dumps({
    "task": "topic_curation",
    "current_topic_md": "",
    "incoming_email_body": (
        "Watched a Tommy Emmanuel breakdown of Somewhere Over the Rainbow last "
        "night. Realised the bass thumb breaks the pattern every couple of bars "
        "— that's what makes it sound human. Maybe the goal of Travis picking "
        "isn't evenness, it's knowing when to disrupt."
    ),
})


def run_one(preset: dict, base_cfg: LmStudioConfig) -> bool:
    print(f"\n===== {preset['label']} =====")
    # Inherit base_cfg's model-load safety (context_length, gpu_offload,
    # ttl_seconds, estimate_before_load) so the smoke test never tries to
    # load a 26B+ model with the model's default 32k–256k context window.
    cfg = dataclasses.replace(
        base_cfg,
        model=preset["model"],
        max_tokens=512,
        task_overrides=preset["task_overrides"],
    )
    print(
        f"  load params       : context_length={cfg.context_length} "
        f"gpu_offload={cfg.gpu_offload} ttl={cfg.ttl_seconds} "
        f"estimate={cfg.estimate_before_load}"
    )

    # 1. Verify the merge helper produces what we expect.
    sampling, extra_body = lm_studio._sampling_for(cfg, task="topic_curation")
    print(f"  merged sampling   : {sampling}")
    print(f"  merged extra_body : {extra_body}")
    if sampling != preset["expected_sampling"]:
        print(f"  FAIL: sampling mismatch (expected {preset['expected_sampling']})")
        return False
    if extra_body != preset["expected_extra_body"]:
        print(f"  FAIL: extra_body mismatch (expected {preset['expected_extra_body']})")
        return False
    print("  merge OK")

    # 2. Make a real call. Failure here is fine — we still proved the merge.
    try:
        result = lm_studio.chat_json(
            cfg, system=SYSTEM, user=USER, task="topic_curation",
        )
    except Exception as e:
        print(f"  call failed: {type(e).__name__}: {str(e)[:200]}")
        # If the configured model isn't loadable, ensure_running falls back to
        # whatever IS loaded (cfg.model gets mutated). Note that — it's still a
        # successful proof of the plumbing.
        if cfg.model != preset["model"]:
            print(f"  (note: cfg.model fell back to {cfg.model!r})")
        return False
    topic_md = result.get("topic_md") or ""
    if cfg.model != preset["model"]:
        print(f"  (note: cfg.model fell back to {cfg.model!r})")
    print(f"  response.topic_md ({len(topic_md)} chars):")
    print("  " + topic_md.replace("\n", "\n  ")[:600])
    return True


def main() -> int:
    # Load the project config so the smoke test inherits the same model-load
    # safety knobs the workflow engine uses (context_length, gpu_offload,
    # ttl_seconds, estimate_before_load). Without this, the smoke test was
    # constructing a raw LmStudioConfig and asking `lms` to load 26B+ models
    # with the model's default context window — which on Apple Silicon could
    # exhaust unified memory and crash the machine.
    project_cfg = workflow_config.load()
    base_cfg = project_cfg.lm_studio
    print(
        f"Loaded base lm_studio cfg from config.yaml: "
        f"context_length={base_cfg.context_length}, "
        f"gpu_offload={base_cfg.gpu_offload}, "
        f"ttl_seconds={base_cfg.ttl_seconds}, "
        f"estimate_before_load={base_cfg.estimate_before_load}"
    )

    results = []
    for preset in (QWEN_PRESET, GEMMA_PRESET):
        results.append((preset["label"], run_one(preset, base_cfg)))

    print("\n===== summary =====")
    failures = 0
    for label, ok in results:
        marker = "ok" if ok else "FAIL"
        print(f"  [{marker}] {label}")
        if not ok:
            failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
