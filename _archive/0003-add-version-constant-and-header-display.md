Show running build and release stage in the page header (v0.2.01)

BACKLOG item 3. Gives every build a visible identity — useful because the phone
deploys by copying the latest file onto the base name DropZone.py.

- Add `__version__ = "0.2.01"` and `VERSION_STAGE` (nightly | beta | stable),
  documented against the release.beta.incremental scheme.
- Header now renders "v{__version__} · {VERSION_STAGE}" next to the theme
  toggle, on both host and remote pages.
