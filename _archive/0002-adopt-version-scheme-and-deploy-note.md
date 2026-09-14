Adopt release.beta.incremental versioning and record phone deploy step

Docs-only follow-up to the workflow setup; no app code changed, no version bump.

- docs/DEVELOPMENT.md: replace SemVer+channel section with the project's own
  `release.beta.incremental` format (e.g. v0.2.01). Baseline is v0.2.00; next
  shipped app change is v0.2.01. Note that pure-doc changes get a commit note
  but do not bump the version.
- CHANGELOG.md: rebaseline to v0.2.00; Unreleased header points at next v0.2.01.
- SESSION.md: record the phone deploy step (copy latest build onto the base
  name DropZone.py because Termux:Widget can't easily be repointed — intentional,
  not drift) and the plan to start item 1 with confirming logging.
- BACKLOG.md: item 1 now leads with low-risk instrumentation (log sizes/peak
  memory, silence the benign download-side BrokenPipeError) before any fix.
