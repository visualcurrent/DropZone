# UNEXPLORED IDEAS — DropZone

Directions scoped but not built. Larger P3 features carried from the old backlog; the active bugs/tests live in PLAN.md.

## U1 Thumbnails toggle + thumbnail selection view (old BACKLOG 7)
**Idea.** Opt-in thumbnails (default OFF, so speed users keep fast icons) plus a grid view for custom multi-select of files.
**Why it matters.** Lets users pick files visually instead of by name.
**In hand.** Open questions to resolve at design time: whether thumbnails come from file metadata vs. generation, and how much generation latency is acceptable — measure before committing to generation.

## U2 Split "Download everything" into size-capped parts (old BACKLOG 11)
**Idea.** Break one giant archive into multiple volumes up to a `MAX_ARCHIVE_BYTES` cap, packing whole files into each part without splitting a file across parts; the UI lists the parts.
**Why it matters.** One giant archive is unwieldy on a phone.
**In hand.** Archives already STORE (no compression, v0.2.03), so the packed size is predictable, which makes exact sizing feasible. Shares the exact-length machinery of the streaming zip (see ARCHITECTURE contract 4).

## U3 Unify upload progress + host activity into one status area (old BACKLOG 14)
**Idea.** One persistent status region showing both your own upload progress and the host's live download/queue activity, with no page-content jump as it updates, reachable without scrolling on phone and desktop widths.
**Why it matters.** Today the upload bar and the host-activity panel are separate and in different places (field feedback: "combine with the progress bar").
**In hand.** v0.2.08 made the activity a floating always-visible panel as an interim; pairs with the per-upload progress work in BACKLOG 15 (PLAN).
