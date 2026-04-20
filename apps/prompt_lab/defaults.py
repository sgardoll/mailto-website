"""Default prompts and sample inputs for the lab UI.

The system and user prompts are lifted verbatim from
`apps/workflow_engine/prompt.py` so that what the user edits here is exactly
what the production pipeline sends. If upstream prompts change, import them
from there instead of duplicating — but at time of writing the production
module depends on `site_index` (frontmatter I/O), which we don't need in the
lab, so we keep a flat copy here.
"""
from __future__ import annotations
import json
from textwrap import dedent


SYSTEM_BASE = dedent("""\
    You are the curator of a single, evolving website that grows from emails the
    owner sends to a dedicated inbox. Each inbox is dedicated to one topic, goal,
    or task in the owner's life. You infer that topic from the stream of emails
    over time and refine it as more arrive.

    You have two prime directives:

    1. FOLD IN, DO NOT SILO. New content must extend or connect to existing
       threads on the site. Do not create isolated pages, drop-downs, or
       sub-sections that fragment the site. If a new email is on-topic for an
       existing thread, extend that thread. Only create a new thread when the
       email genuinely opens a new line of thought related to the inbox topic;
       if you do, justify it and link it to at least one existing thread.

    2. TAKE INITIATIVE. Do not just transcribe the email. Synthesise it into
       the site: extract what is actionable, what is a question worth pursuing,
       what tools/resources/next steps it implies, and turn that into helpful,
       lasting content the owner can actually use later. Speak in their voice,
       not as a chatbot reporting on a message.

    You always return a single JSON object describing file operations. You
    never include shell commands, scripts, or any path outside of
    src/content/entries/ or src/content/threads/. Markdown content must use
    YAML frontmatter that matches the schema in the prompt.
""")


SAMPLE_EMAIL = {
    "message_id": "<sample-msg-1@prompt-lab.local>",
    "from": "you@example.com",
    "to": "ideas+guitar@example.com",
    "subject": "fingerstyle arpeggio patterns that don't feel boring",
    "date": "2026-04-19T09:14:00+00:00",
    "text": (
        "Been noodling with PIMA arpeggios over Am - F - C - G and they all feel "
        "sterile. I want something that breathes more. Two things I want to try: "
        "(1) rolling the thumb across 6-5-4 instead of just plucking the root, "
        "(2) ghosting the middle finger to imply a triplet feel without actually "
        "playing triplets. Also found this lesson by Adam Rafferty on 'percussive "
        "arpeggios' that looks promising. Schedule: 20 min a day for 2 weeks, "
        "then record myself and compare to week one."
    ),
    "html": "",
    "headers": {},
}

SAMPLE_TOPIC_MD = (
    "This inbox is a working journal for the owner's acoustic-guitar practice, "
    "focused on fingerstyle technique and arrangement. It captures practice plans, "
    "specific technical experiments, and references (lessons, players, songs) worth "
    "returning to. The goal is steady, measurable improvement over months — not "
    "performance, not theory for its own sake."
)

SAMPLE_EXISTING_THREADS = [
    {
        "slug": "fingerstyle-right-hand",
        "title": "Fingerstyle right-hand technique",
        "summary": (
            "A running workbench for right-hand patterns (PIMA, thumb independence, "
            "travis picking) and the exercises used to drill them."
        ),
        "tags": ["technique", "right-hand"],
        "excerpt": (
            "Thread tracks PIMA drills and common pitfalls. Current focus: thumb "
            "independence over bass lines while the fingers hold a pattern. "
            "Entries log specific exercises, tempo targets, and what broke..."
        ),
    },
    {
        "slug": "practice-routine",
        "title": "Practice routine",
        "summary": (
            "How the owner is structuring daily practice: warm-up, technique drill, "
            "repertoire, and reflective recording."
        ),
        "tags": ["routine", "meta"],
        "excerpt": (
            "Currently 30 minutes a day split 5/15/10 across warmup, technique, and "
            "repertoire. Tracking adherence and noting which drills feel stale so "
            "they can be rotated out..."
        ),
    },
]

SAMPLE_EXISTING_ENTRIES = [
    {
        "slug": "pima-thumb-independence-week-1",
        "title": "PIMA thumb-independence week 1",
        "summary": "Week-one notes on drilling thumb independence under a P-I-M-A pattern.",
        "tags": ["technique", "pima"],
        "threads": ["fingerstyle-right-hand"],
    },
]


def topic_prompt_user(email: dict, topic_md: str, threads: list[dict], entries_count: int) -> str:
    return json.dumps({
        "task": "topic_curation",
        "instructions": (
            "Update the working topic statement for this inbox. Keep it short "
            "(under 100 words). Reflect what the inbox is REALLY about given all "
            "existing entries plus this new email. Be specific."
        ),
        "current_topic_md": topic_md,
        "current_threads": [
            {"slug": t["slug"], "title": t["title"], "summary": t["summary"]}
            for t in threads
        ],
        "current_entries_count": entries_count,
        "incoming_email": email,
        "expected_output_schema": {
            "topic_md": "string (markdown, < 100 words)"
        },
    }, indent=2)


def synthesis_prompt_user(email: dict, topic_md: str, threads: list[dict], entries: list[dict]) -> str:
    return json.dumps({
        "task": "synthesise_and_fold_in",
        "instructions": (
            "Decide how to integrate the incoming email into the site. "
            "Prefer extending an existing thread. You MAY: create a new entry, "
            "edit/replace an existing thread's content (rewriting its summary "
            "and body to incorporate the new entry), and create at most one new "
            "thread (only with a written justification). Every new entry MUST "
            "link to >=1 existing OR newly-created thread."
        ),
        "site_topic": topic_md,
        "existing_threads": threads,
        "existing_entries": entries,
        "incoming_email": email,
        "expected_output_schema": {
            "rationale": "string (2-4 sentences explaining how this folds in)",
            "operations": [
                {
                    "op": "create | edit",
                    "collection": "entries | threads",
                    "slug": "string (kebab-case, no path, no extension)",
                    "frontmatter": {
                        "title": "string", "summary": "string",
                        "receivedAt": "ISO8601 (entries only)",
                        "source": {"from": "...", "subject": "...", "messageId": "..."},
                        "tags": ["string"],
                        "threads": ["existing-thread-slug-or-just-created"],
                        "createdAt": "ISO8601 (threads only)",
                        "updatedAt": "ISO8601 (threads only)",
                        "status": "active | paused | done",
                        "relatedThreads": ["thread-slug"],
                    },
                    "body_markdown": "string (the body of the .md file, after frontmatter)",
                }
            ],
            "reply_summary": "string (2-3 sentences for the reply email)",
        },
    }, indent=2)


def system_for(task: str) -> str:
    return SYSTEM_BASE + f"\nCurrent task: {task}\n"


def default_user_for(task: str) -> str:
    if task == "topic_curation":
        return topic_prompt_user(
            SAMPLE_EMAIL, SAMPLE_TOPIC_MD, SAMPLE_EXISTING_THREADS,
            len(SAMPLE_EXISTING_ENTRIES),
        )
    return synthesis_prompt_user(
        SAMPLE_EMAIL, SAMPLE_TOPIC_MD, SAMPLE_EXISTING_THREADS,
        SAMPLE_EXISTING_ENTRIES,
    )
