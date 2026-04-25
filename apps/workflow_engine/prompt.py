"""Prompt builders for topic curation and content synthesis."""
from __future__ import annotations
import json
from textwrap import dedent

from .site_index import SiteIndex


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


VOICE_RULE = dedent("""\
    Write in the owner's voice, not about the owner. The incoming email body
    is a sample of their voice — match its cadence, register, and the specific
    words they use. Write as "I forwarded" / "I watched" / "I've been working
    on" — never "the owner forwarded" or "the user watched". Do not soften
    rough phrasing into corporate language. Do not hedge with "the email
    suggests" or "it appears that"; state the point directly.
""")


def topic_prompt_user(idx: SiteIndex, email: dict) -> str:
    return json.dumps({
        "task": "topic_curation",
        "instructions": (
            "Update the working topic statement for this inbox. Keep it short "
            "(under 100 words). Reflect what the inbox is REALLY about given all "
            "existing entries plus this new email. Be specific."
        ),
        "current_topic_md": idx.topic,
        "current_threads": [
            {"slug": t.slug, "title": t.title, "summary": t.summary} for t in idx.threads
        ],
        "current_entries_count": len(idx.entries),
        "incoming_email": email,
        "expected_output_schema": {
            "topic_md": "string (markdown, < 100 words)"
        },
    }, indent=2)


def synthesis_prompt_user(idx: SiteIndex, email: dict) -> str:
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
        "site_topic": idx.topic,
        "existing_threads": [
            {
                "slug": t.slug, "title": t.title, "summary": t.summary,
                "tags": t.tags, "excerpt": t.excerpt,
            } for t in idx.threads
        ],
        "existing_entries": [
            {
                "slug": e.slug, "title": e.title, "summary": e.summary,
                "tags": e.tags, "threads": e.threads,
            } for e in idx.entries
        ],
        "incoming_email": email,
        "expected_output_schema": {
            "rationale": "string (2-4 sentences explaining how this folds in)",
            "operations": [
                {
                    "op": "create | edit",
                    "collection": "entries | threads",
                    "slug": "string (kebab-case, no path, no extension)",
                    "frontmatter": {
                        # entries
                        "title": "string", "summary": "string",
                        "receivedAt": "ISO8601 (entries only)",
                        "source": {"from": "...", "subject": "...", "messageId": "..."},
                        "tags": ["string"],
                        "threads": ["existing-thread-slug-or-just-created"],
                        # threads
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
    return SYSTEM_BASE + "\n" + VOICE_RULE + f"\nCurrent task: {task}\n"
