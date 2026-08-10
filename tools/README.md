# tools/

One-shot refactor scripts, kept for the record rather than for routine use.

`extract.py` then `extract_js.py` turn `index.html` into `template.html` +
`i18n/en.json`. They were run once, against the site as it stood at commit
`cb86084`, and the result is committed. You do not need to run them again —
edit `template.html` and `i18n/*.json` directly.

They are here because the extraction is the kind of thing you want to be able
to audit: `extract.py` edits by byte offset rather than re-serialising the DOM,
so the template is provably lossless. Putting the English strings back into the
template reproduced the original file byte-for-byte.
