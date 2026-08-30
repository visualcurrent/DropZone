# DropZone — Development Workflow

This file defines how we develop DropZone across many short, focused sessions,
often with an AI agent doing the edits. The goal is simple: any session can pick
up exactly where the last one stopped, with no lost context.

## Why this system

DropZone is a small project: one Python file, pure standard library, one
developer. A heavy process (sprints, boards, branching models) would cost more
than it returns. But "no process" fails a different way — an AI agent starts
each session with an empty memory, so context must live in files, not in a
person's head.

The answer is a **docs-driven, one-task-at-a-time loop**. A few living Markdown
files hold all the state. Each session does one backlog item, start to finish,
and writes down what changed. Nothing else is required.

## The living documents

- **BACKLOG.md** — the single source of truth for what to do next. Tasks are
  ordered by priority and sized to fit one session each. The top unblocked item
  is always the next thing to work on.
- **SESSION.md** — the handoff note. It records the current focus, what the last
  session did, decisions made, and any open question. Read it first; update it
  last.
- **CHANGELOG.md** — the user-facing history, one entry per released version.
- **docs/DEVELOPMENT.md** — this file. The rules of the game.
- **docs/commits/** — one Markdown file per change, holding a ready-to-use git
  commit message. We are not on git right now, so commit messages are staged
  here and replayed later (see "Committing" below).
- **docs/notes/** — supporting material: logs, investigation notes, findings
  that a backlog item depends on.

## The session loop

Each working session follows the same five steps:

1. **Orient.** Read SESSION.md, then the top item in BACKLOG.md. Do not scan the
   whole codebase — trust the docs to point at what matters.
2. **Pick one task.** Take the highest-priority unblocked backlog item. One item
   per session keeps the context small and the change reviewable.
3. **Do the work.** Make the change. Keep it minimal and in the spirit of the
   existing code (single file, standard library only, no new dependencies unless
   a backlog item explicitly approves one).
4. **Verify.** Run the task's "Definition of done" check. DropZone has no unit
   tests yet, so most checks are a short manual script (start the server, do the
   action, confirm the result). If a check is worth automating, add it as its
   own backlog item.
5. **Record.** Update SESSION.md (what changed, what is next), tick the item off
   in BACKLOG.md, add a CHANGELOG.md entry if a user-visible change shipped, and
   write a commit note in docs/commits/.

## Task sizing

A backlog item is the right size when one focused session can finish it and
verify it. If an item needs research before it can be scoped (for example, the
upload freeze), the first session's job is to investigate and split it into
smaller, well-defined items — not to force a fix.

## Versioning

Format: `release.beta.incremental` — for example `v0.2.01`.

- **incremental** — two digits, bumped by 1 on every shipped app change (a fix
  or a small feature): `v0.2.01`, `v0.2.02`, ... `v0.2.10`.
- **beta** — the feature line. Bumped at a milestone, which resets incremental
  to `00`: `v0.2.xx` -> `v0.3.00`.
- **release** — stays `0` while pre-1.0; moves to `1` for the first stable
  public release.

Current baseline is **v0.2.00**. The next shipped app change is **v0.2.01**.

The version string lives in one constant in DropZone.py (BACKLOG item 3 adds it
and shows it, with its release stage, on the host page). CHANGELOG.md mirrors
it. Bump the version in the same change that ships the work, never separately.
Pure-doc changes get a commit note but need not bump the version.

## Committing (while off git)

For every change, write `docs/commits/NNNN-short-title.md` where `NNNN` is the
next number in sequence. The file holds a complete commit message:

- Line 1: a concise subject in imperative mood (e.g. "Fix upload freeze on large
  files"), ideally under ~60 characters.
- A blank line, then a body explaining what changed and why.

When git is reconnected, these notes are replayed in order as commit messages,
so the history reads cleanly even though the commits were deferred.

## Guiding principles

- **Keep it simple.** Simplicity is a feature of this project, not an accident.
  Prefer the smallest change that solves the problem. Zero third-party
  dependencies is a hard rule unless a backlog item says otherwise.
- **One change at a time.** Small, isolated changes are easy to verify and easy
  to undo.
- **Write it down.** If a decision or finding is not in a doc, it does not exist
  for the next session.
