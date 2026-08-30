Persist theme choice; add list scroll clearance (v0.2.10)

Two CSS/UX items reported from the field.

Theme (BACKLOG 12): the toggle was not persisted, so every reload — and every
move between the host and remote pages — re-read the OS setting and discarded the
user's choice, which reads as "the theme keeps reverting / is broken". Now:
- A tiny script in <head> applies the saved theme (localStorage 'dz-theme'),
  else the OS preference, BEFORE first paint (no flash), on both pages.
- initTheme() follows that attribute and writes the choice to localStorage on
  toggle.
- Added `color-scheme` (light/dark) to the theme blocks so native UI — scrollbars,
  form controls — matches the theme instead of staying light.
Note: the theme CSS/JS logic itself was already correct and unchanged vs the
backups, so this targets the most likely cause (non-persistence); the exact
reported symptom still wants a field confirmation.

List scroll (BACKLOG 12→5): no hard height clamp was found in the CSS, so this is
a defensive fix — generous bottom padding on .main (with safe-area-inset) so the
last list item clears the mobile browser chrome and the floating activity panel.
If the bottom is still unreachable, capture device/orientation and whether it
happens during a transfer, to pin it.
