# UNEXPLORED IDEAS — DropZone

Directions scoped but not built. Larger P3 features carried from the old backlog; the active bugs/tests live in PLAN.md.

## U1 Thumbnails toggle + thumbnail selection view (old BACKLOG 7)
**Idea.** Opt-in thumbnails (default OFF, so speed users keep fast icons) plus a grid view for custom multi-select of files.
**Why it matters.** Lets users pick files visually instead of by name.
**In hand.** Open questions to resolve at design time: whether thumbnails come from file metadata vs. generation, and how much generation latency is acceptable — measure before committing to generation.

**Update 2026-11-12.** Thumbnail generation is approved and moved to PLAN backlog 18 (made by the uploader's browser, always on, lazy-loaded; the opt-in toggle is dropped by Gabe). The grid view is not planned. Design agreed with Gabe so far, not yet a backlog item:
- Row: tap the thumbnail (or the icon of a file with no thumbnail) opens peek; tap the rest of the row toggles selection, shown by a row highlight and a select circle.
- Peek: an overlay with the 320 px image, the full filename (wrapped; only a name too long to fit is cut in the middle with "..." so its start and its extension stay visible) and one Download button, which starts the download, confirms it with a short notice and closes peek. Tap anywhere or the phone's Back closes it.
- One list-wide download button replaces "Download everything" and the per-person zip links: it reads "Download all N files" with nothing selected and "Download N selected" otherwise, and sticks to the bottom of the screen while anything is selected. One selected file downloads as the plain file; more than one as a zip.
- A person's header carries the same select circle and selects or clears all of that person's files.
- Selection is kept in the page and reapplied when the list is redrawn. The top "my files" card keeps its remove button and gains only thumbnail and peek.
- OPEN: whether the per-row download arrow stays. It depends on U4.

## U4 Several individual files from one tap
**Idea.** "Download N selected" delivers N separate files instead of one zip, with a zip on/off toggle beside the button.
**Why it matters.** On a phone an individual photo lands where the gallery can see it; a zip has to be unpacked first. If this works, the per-row download arrow can go.
**In hand.** Hurdles, none tested on our phones yet: Chrome asks once for permission to download multiple files; iPhone Safari asks per file and tends to drop downloads started in quick succession; the host's limit of 4 concurrent transfers means the page must start them one after another; the phone's share sheet is not available because browsers allow it only on HTTPS pages and it needs the whole file in memory (the approach reverted in v0.2.14). First step is a field test on Android Chrome and iPhone Safari: start 5 downloads about a second apart from one tap and count the files that arrive.

## U2 Split "Download everything" into size-capped parts (old BACKLOG 11)
**Idea.** Break one giant archive into multiple volumes up to a `MAX_ARCHIVE_BYTES` cap, packing whole files into each part without splitting a file across parts; the UI lists the parts.
**Why it matters.** One giant archive is unwieldy on a phone.
**In hand.** Archives already STORE (no compression, v0.2.03), so the packed size is predictable, which makes exact sizing feasible. Shares the exact-length machinery of the streaming zip (see ARCHITECTURE contract 4).

## U3 Unify upload progress + host activity into one status area (old BACKLOG 14)
**Idea.** One persistent status region showing both your own upload progress and the host's live download/queue activity, with no page-content jump as it updates, reachable without scrolling on phone and desktop widths.
**Why it matters.** Today the upload bar and the host-activity panel are separate and in different places (field feedback: "combine with the progress bar").
**In hand.** v0.2.08 made the activity a floating always-visible panel as an interim; pairs with the per-upload progress work in BACKLOG 15 (PLAN).
