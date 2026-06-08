# Vattezhuthu

A digital preservation of Hermann Gundert's historical Vattezhuthu typeface, drawn from his 1872 Malayalam dictionary.

**Vattezhuthu** ("round script") is a medieval script and a predecessor of modern Malayalam, used in Kerala from roughly the 6th to the 13th century. This font maps the glyphs to their corresponding Unicode Malayalam codepoints.

## Fonts

| File | Description |
|---|---|
| `fonts/Vattezhuthu.ttf` | Base font — original glyph forms |
| `fonts/Vattezhuthu-Alt.ttf` | Alt font — alternate forms as defaults |

## Preview

Live test page: [hfactor.github.io/Gundert](https://hfactor.github.io/Gundert)

## Design notes

- **Not a shaping font.** Only `DFLT dflt` is declared — no `mlym` or `mlm2` script. HarfBuzz will not apply Indic reordering or conjunct formation.
- **GSUB liga** — 104 ligature rules map consonant + matra sequences to pre-drawn combination glyphs.
- **GSUB salt / ss01** — 45 alternate substitution rules expose variant glyph forms.
- Split matras (o = U+0D46 + U+0D3E, oo = U+0D47 + U+0D3E) use 3-codepoint sequences.

## Building

```bash
pip install fonttools
python3 build.py          # outputs fonts/Vattezhuthu.ttf + Vattezhuthu-Alt.ttf
python3 gen_test.py       # outputs docs/index.html
```

## Sources

SVG source files are in `/svg`. Named by convention: `consonant-vowel.svg`, `consonant-vowel-alt.svg`.

## Credits

Glyph artwork based on Hermann Gundert (1816–1893).  
Digital font by Indrajith Baby and Hiran Venugopalan.

## License

[MIT](LICENSE)
