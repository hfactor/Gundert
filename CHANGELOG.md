# Changelog

All notable changes to this project will be documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [0.1.0] — 2026-06-08

### Changed
- Font family renamed from **Gundert** to **Vattezhuthu**
- Unicode encoding: migrated from Private Use Area (PUA) to standard Malayalam Unicode codepoints (U+0D05–U+0D35)
- Complete rewrite of build pipeline (`build.py`) using fontTools FontBuilder
- GSUB features: 104 liga rules + 45 salt/ss01 alternates
- Added `Vattezhuthu-Alt.ttf` — alternate glyph forms as defaults

### Added
- Full name table: copyright, unique ID, PostScript name, designer, description, license (MIT)
- Accurate `head` timestamps
- `VENDOR_ID = GUND`, `fsSelection` REGULAR bit
- `gen_test.py` — self-contained test HTML generator (`docs/index.html`)
- `LICENSE` (MIT), `README.md`, `CHANGELOG.md`
- `fonts/pua/` — archived original PUA font exports

### Fixed
- SVG renames: `ca-a.svg` → `ca-aa.svg`, `rra-e-alt.svg` → `rra-ai.svg`
- `head.created` / `head.modified` were epoch 0 (1969) — now stamped correctly

---

## [0.0.3] — 2026-06-05

- Added 16 corrected glyphs by Indrajith Baby
- Name corrections (aa instead of a)
- Updated `ka-uu-alt.svg`

## [0.0.2] — earlier

- Initial Unicode-mapped font build
- SVG sources reorganised

## [0.0.1] — 2018

- Original PUA font (`gundertfont.*`) created from Gundert's 1872 dictionary artwork
