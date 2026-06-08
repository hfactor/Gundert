#!/usr/bin/env python3
"""Build Gundert.ttf and Gundert-Alt.ttf from SVG sources.

Reads all SVGs from /svg, maps them to Malayalam Unicode codepoints,
generates GSUB liga/salt/ss01 features, and compiles two font files.
"""

import datetime
import os
import re
import xml.etree.ElementTree as ET
from io import StringIO

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.svgLib import SVGPath
from fontTools.feaLib.builder import addOpenTypeFeatures

# ---------------------------------------------------------------------------
# Version — bump VERSION for each release.
# VERSION_DATE should match the release date (YYYY-MM-DD).
# ---------------------------------------------------------------------------
VERSION      = "0.1.0"
VERSION_DATE = "2026-06-08"

# Metadata written into the font's name table
COPYRIGHT    = "Copyright 2018 Indrajith Baby, Hiran Venugopalan. Glyph artwork based on Hermann Gundert (1816–1893)."
MANUFACTURER = "Indrajith Baby, Hiran Venugopalan"
DESIGNER     = "Indrajith Baby, Hiran Venugopalan"
VENDOR_ID    = "GUND"          # 4-char OS/2 achVendID
VENDOR_URL   = "https://github.com/hiranvv/Gundert"
DESIGNER_URL = "https://github.com/hiranvv"
DESCRIPTION  = (
    "Vattezhuthu — a digital preservation of Hermann Gundert's "
    "historical Malayalam typeface, drawn from his 1872 dictionary. "
    "Vattezhuthu (\"round script\") is a medieval predecessor of modern Malayalam. "
    "This is not a shaping font: only DFLT dflt is declared so HarfBuzz "
    "does not apply Indic reordering or conjunct formation."
)
LICENSE_DESC = (
    "This Font Software is licensed under the MIT License. "
    "Permission is hereby granted, free of charge, to any person obtaining a copy "
    "of this font to use, copy, modify, merge, publish, distribute, sublicense, "
    "and/or sell copies, subject to the above copyright notice."
)
LICENSE_URL  = "https://opensource.org/licenses/MIT"

# ---------------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SVG_DIR = os.path.join(BASE_DIR, "svg")
OUT_DIR = os.path.join(BASE_DIR, "fonts")

UPM = 1000
ASCENDER = 800
DESCENDER = -200
LINE_GAP = 0
WIN_ASCENT = 1000
WIN_DESCENT = 200
X_HEIGHT = 500
CAP_HEIGHT = 700

VOWEL_CP = {
    "a": 0x0D05, "aa": 0x0D06, "i": 0x0D07, "ii": 0x0D08, "u": 0x0D09,
    "e": 0x0D0E, "ee": 0x0D0F, "o": 0x0D12, "oo": 0x0D13,
}

CONSONANT_CP = {
    "ka": 0x0D15, "nga": 0x0D19, "ca": 0x0D1A, "nya": 0x0D1E,
    "tta": 0x0D1F, "nna": 0x0D23, "ta": 0x0D24, "na": 0x0D28,
    "nnna": 0x0D29, "pa": 0x0D2A, "ma": 0x0D2E, "ya": 0x0D2F,
    "ra": 0x0D30, "rra": 0x0D31, "la": 0x0D32, "lla": 0x0D33,
    "llla": 0x0D34, "va": 0x0D35,
}

# Matra suffix → list of Unicode codepoints (split matras have 2)
MATRA_CP = {
    "aa": [0x0D3E],
    "i":  [0x0D3F],
    "ii": [0x0D40],
    "u":  [0x0D41],
    "uu": [0x0D42],
    "e":  [0x0D46],
    "ee": [0x0D47],
    "ai": [0x0D48],
    "o":  [0x0D46, 0x0D3E],   # split matra — 3-codepoint sequence
    "oo": [0x0D47, 0x0D3E],   # split matra — 3-codepoint sequence
}

SPLIT_MATRAS = {"o", "oo"}

# All Malayalam codepoints not covered by vowels/consonants → noglyph marker
NOGLYPH_CP = [
    # Missing vowels
    0x0D0A, 0x0D10, 0x0D14,
    # Missing consonants
    0x0D16, 0x0D17, 0x0D18, 0x0D1B, 0x0D1C, 0x0D1D,
    0x0D20, 0x0D21, 0x0D22, 0x0D25, 0x0D26, 0x0D27,
    0x0D2B, 0x0D2C, 0x0D2D, 0x0D36, 0x0D37, 0x0D38, 0x0D39,
    # Virama
    0x0D4D,
]

# Matra codepoints that need individual glyphs (named uni0DXX) so GSUB can
# distinguish them. They render as blank/zero-width but must be separate glyphs.
MATRA_GLYPH_CP = {
    0x0D3E: "uni0D3E",  # ◌ാ  aa
    0x0D3F: "uni0D3F",  # ◌ി  i
    0x0D40: "uni0D40",  # ◌ീ  ii
    0x0D41: "uni0D41",  # ◌ു  u
    0x0D42: "uni0D42",  # ◌ൂ  uu
    0x0D46: "uni0D46",  # ◌െ  e
    0x0D47: "uni0D47",  # ◌േ  ee
    0x0D48: "uni0D48",  # ◌ൈ  ai
}


# ---------------------------------------------------------------------------
# SVG parsing
# ---------------------------------------------------------------------------

def get_viewbox(filepath):
    """Return (vb_x, vb_y, vb_w, vb_h) from SVG viewBox attribute."""
    tree = ET.parse(filepath)
    root = tree.getroot()
    vb = root.get("viewBox", "0 0 1000 1000")
    parts = re.split(r"[\s,]+", vb.strip())
    return tuple(float(p) for p in parts[:4])


def svg_to_glyph(filepath):
    """
    Load an SVG and convert to (TTGlyph, advance_width).

    Transform applied:
      font_x = svg_x - vb_x   (shift x so left edge of viewBox lands at 0)
      font_y = ASCENDER - svg_y  (flip Y; SVG top maps to font ascender)

    Cubic beziers are converted to quadratic via Cu2QuPen.
    reverse_direction=True restores correct TT winding after Y-flip.
    """
    vb_x, _vb_y, vb_w, _vb_h = get_viewbox(filepath)
    advance_width = round(vb_w)

    # 6-tuple (xx, xy, yx, yy, dx, dy): new_x = xx*x + yx*y + dx
    transform = (1, 0, 0, -1, -vb_x, ASCENDER)

    tt_pen = TTGlyphPen(None)
    cu2qu_pen = Cu2QuPen(tt_pen, max_err=1.0, reverse_direction=True)

    svg = SVGPath(filepath, transform=transform)
    svg.draw(cu2qu_pen)

    return tt_pen.glyph(), advance_width


# ---------------------------------------------------------------------------
# Simple box glyph for .notdef / noglyph
# ---------------------------------------------------------------------------

def make_box_glyph(adv=600, bottom=50, top=650, left=60, right=540, thickness=40):
    """Draw an outlined rectangle. Returns (TTGlyph, advance_width)."""
    pen = TTGlyphPen(None)

    # Outer contour — clockwise in Y-up space
    pen.moveTo((left, top))
    pen.lineTo((left, bottom))
    pen.lineTo((right, bottom))
    pen.lineTo((right, top))
    pen.closePath()

    # Inner contour — counter-clockwise (hole)
    t = thickness
    pen.moveTo((left + t, top - t))
    pen.lineTo((right - t, top - t))
    pen.lineTo((right - t, bottom + t))
    pen.lineTo((left + t, bottom + t))
    pen.closePath()

    return pen.glyph(), adv


# ---------------------------------------------------------------------------
# SVG directory scan and categorization
# ---------------------------------------------------------------------------

def categorize_svgs(svg_dir):
    """
    Scan SVG directory; return list of glyph-info dicts.

    Each dict has:
      fname, filepath, stem, glyph_name, glyph_base_name,
      is_alt, consonant (or None), vowel_suffix (or None)
    """
    # Longest-first to prevent prefix collisions (e.g. "nnna" before "nna")
    consonants = sorted(CONSONANT_CP.keys(), key=len, reverse=True)
    vowels = sorted(VOWEL_CP.keys(), key=len, reverse=True)

    results = []

    for fname in sorted(os.listdir(svg_dir)):
        if not fname.endswith(".svg"):
            continue

        stem = fname[:-4]
        filepath = os.path.join(svg_dir, fname)

        is_alt = stem.endswith("-alt")
        base_stem = stem[:-4] if is_alt else stem

        consonant = None
        vowel_suffix = None
        matched = False

        # Try consonant (with optional vowel suffix)
        for c in consonants:
            if base_stem == c:
                consonant = c
                matched = True
                break
            if base_stem.startswith(c + "-"):
                suffix = base_stem[len(c) + 1:]
                if suffix in MATRA_CP:
                    consonant = c
                    vowel_suffix = suffix
                    matched = True
                    break

        # Try standalone vowel
        if not matched:
            for v in vowels:
                if base_stem == v:
                    matched = True
                    break

        if not matched:
            print(f"  Warning: cannot categorize {fname} — skipping")
            continue

        glyph_base_name = "gundert." + base_stem.replace("-", "_")
        glyph_name = (glyph_base_name + ".alt") if is_alt else glyph_base_name

        results.append({
            "fname": fname,
            "filepath": filepath,
            "stem": base_stem,
            "glyph_name": glyph_name,
            "glyph_base_name": glyph_base_name,
            "is_alt": is_alt,
            "consonant": consonant,
            "vowel_suffix": vowel_suffix,
        })

    return results


# ---------------------------------------------------------------------------
# GSUB feature code generation
# ---------------------------------------------------------------------------

def generate_gsub(glyph_infos):
    """Return OpenType feature code string for liga, salt, and ss01."""

    # Collect combination glyphs grouped by consonant
    combos_by_consonant = {}
    for info in glyph_infos:
        if info["is_alt"] or not info["consonant"] or not info["vowel_suffix"]:
            continue
        c = info["consonant"]
        combos_by_consonant.setdefault(c, []).append(
            (info["vowel_suffix"], info["glyph_base_name"])
        )

    # Collect alt pairs (base_name, alt_name)
    base_names = {i["glyph_base_name"] for i in glyph_infos}
    alt_pairs = []
    for info in glyph_infos:
        if info["is_alt"] and info["glyph_base_name"] in base_names:
            alt_pairs.append((info["glyph_base_name"], info["glyph_name"]))
    alt_pairs.sort()

    lines = [
        "languagesystem DFLT dflt;",
        "",
        "feature liga {",
        "  lookup liga_vattezhuthu {",
    ]

    for consonant in sorted(combos_by_consonant.keys()):
        cons_gname = f"gundert.{consonant}"  # actual glyph name in font
        vowels = combos_by_consonant[consonant]

        # Split matras (3-codepoint sequences) must come before 2-codepoint ones
        vowels_sorted = sorted(
            vowels,
            key=lambda x: (0 if x[0] in SPLIT_MATRAS else 1, x[0]),
        )

        lines.append("")
        lines.append(f"    # — {consonant} combinations —")
        for vs, gname in vowels_sorted:
            # Matra glyphs are named uni0DXX; each codepoint is a distinct glyph
            matra_gnames = " ".join(f"uni{cp:04X}" for cp in MATRA_CP[vs])
            lines.append(f"    sub {cons_gname} {matra_gnames} by {gname};")

    lines += [
        "  } liga_vattezhuthu;",
        "} liga;",
        "",
    ]

    if alt_pairs:
        lines += ["feature salt {", "  lookup alts_vattezhuthu {"]
        for base, alt in alt_pairs:
            lines.append(f"    sub {base} from [{base} {alt}];")
        lines += [
            "  } alts_vattezhuthu;",
            "} salt;",
            "",
            "feature ss01 {",
            "  lookup alts_vattezhuthu;",
            "} ss01;",
        ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Font builder
# ---------------------------------------------------------------------------

def build_font(glyph_infos, is_alt_font=False):
    """
    Build and return a TTFont.

    is_alt_font=True: swap base glyph outlines with their alt SVGs
    (both base and .alt slots use the alt SVG in the Alt font).
    """

    # Map base_name → alt SVG path (for the swap)
    alt_svg_map = {
        info["glyph_base_name"]: info["filepath"]
        for info in glyph_infos if info["is_alt"]
    }

    glyphs = {}   # glyph_name → TTGlyph
    metrics = {}  # glyph_name → (advance_width, lsb)

    # .notdef
    notdef_g, notdef_adv = make_box_glyph(adv=600, bottom=50, top=650, left=60, right=540)
    glyphs[".notdef"] = notdef_g
    metrics[".notdef"] = (notdef_adv, 60)

    # gundert.noglyph — small dotted square marker
    ng_g, ng_adv = make_box_glyph(adv=550, bottom=100, top=500, left=75, right=475, thickness=30)
    glyphs["gundert.noglyph"] = ng_g
    metrics["gundert.noglyph"] = (ng_adv, 75)

    # Matra placeholder glyphs (uni0DXX) — zero-width, no outlines.
    # Each codepoint gets its own glyph so GSUB liga rules can reference them
    # individually. They're invisible (zero advance) when rendered standalone.
    for cp, matra_gname in MATRA_GLYPH_CP.items():
        pen = TTGlyphPen(None)
        glyphs[matra_gname] = pen.glyph()
        metrics[matra_gname] = (0, 0)

    # Base glyphs
    for info in glyph_infos:
        if info["is_alt"]:
            continue
        gname = info["glyph_name"]
        filepath = info["filepath"]

        # Alt font: load base slot from alt SVG if available
        if is_alt_font and gname in alt_svg_map:
            filepath = alt_svg_map[gname]

        try:
            g, adv = svg_to_glyph(filepath)
            glyphs[gname] = g
            metrics[gname] = (adv, 0)
        except Exception as exc:
            print(f"  Error {info['fname']}: {exc}")
            g, adv = make_box_glyph()
            glyphs[gname] = g
            metrics[gname] = (adv, 0)

    # Alt glyphs (.alt suffix) — always loaded from alt SVG
    for info in glyph_infos:
        if not info["is_alt"]:
            continue
        gname = info["glyph_name"]
        try:
            g, adv = svg_to_glyph(info["filepath"])
            glyphs[gname] = g
            metrics[gname] = (adv, 0)
        except Exception as exc:
            print(f"  Error {info['fname']}: {exc}")
            g, adv = make_box_glyph()
            glyphs[gname] = g
            metrics[gname] = (adv, 0)

    # Glyph order: .notdef, noglyph, matra placeholders, base glyphs, alts
    glyph_order = [".notdef", "gundert.noglyph"]
    glyph_order += list(MATRA_GLYPH_CP.values())
    glyph_order += [i["glyph_name"] for i in glyph_infos if not i["is_alt"]]
    glyph_order += [i["glyph_name"] for i in glyph_infos if i["is_alt"]]

    # cmap: vowels + consonants → their glyphs; matras → their uni0DXX glyphs;
    # everything else → noglyph
    cmap = {}
    for name, cp in VOWEL_CP.items():
        gname = f"gundert.{name}"
        cmap[cp] = gname if gname in glyphs else "gundert.noglyph"
    for name, cp in CONSONANT_CP.items():
        gname = f"gundert.{name}"
        cmap[cp] = gname if gname in glyphs else "gundert.noglyph"
    for cp, matra_gname in MATRA_GLYPH_CP.items():
        cmap[cp] = matra_gname
    for cp in NOGLYPH_CP:
        cmap[cp] = "gundert.noglyph"

    # --- Assemble font ---
    fb = FontBuilder(UPM, isTTF=True)
    fb.setupGlyphOrder(glyph_order)
    fb.setupCharacterMap(cmap)
    fb.setupGlyf(glyphs)
    fb.setupHorizontalMetrics(metrics)
    fb.setupHorizontalHeader(ascent=ASCENDER, descent=DESCENDER)

    family = "Vattezhuthu"
    style  = "Alt Regular" if is_alt_font else "Regular"

    # PostScript name must be ASCII with no spaces; max 63 chars
    ps_name   = f"Vattezhuthu-{'AltRegular' if is_alt_font else 'Regular'}"
    full_name = f"Vattezhuthu {style}"
    unique_id = f"{VERSION_DATE};{VENDOR_ID};{ps_name}"

    fb.setupNameTable({
        "copyright":             COPYRIGHT,
        "familyName":            family,
        "styleName":             style,
        "uniqueFontIdentifier":  unique_id,
        "fullName":              full_name,
        "version":               f"Version {VERSION}",
        "psName":                ps_name,
        "manufacturer":          MANUFACTURER,
        "designer":              DESIGNER,
        "description":           DESCRIPTION,
        "vendorURL":             VENDOR_URL,
        "designerURL":           DESIGNER_URL,
        "licenseDescription":    LICENSE_DESC,
        "licenseInfoURL":        LICENSE_URL,
    })

    # OS/2: fsSelection bit 6 = REGULAR (set when font is not bold/italic/oblique)
    fs_selection = 0b0100_0000  # 64 = REGULAR
    fb.setupOS2(
        sTypoAscender=ASCENDER,
        sTypoDescender=DESCENDER,
        sTypoLineGap=LINE_GAP,
        usWinAscent=WIN_ASCENT,
        usWinDescent=WIN_DESCENT,
        sxHeight=X_HEIGHT,
        sCapHeight=CAP_HEIGHT,
        fsType=0,
        fsSelection=fs_selection,
        achVendID=VENDOR_ID,
        # Weight 400 = Regular, Width 5 = Medium (normal)
        usWeightClass=400,
        usWidthClass=5,
    )

    fb.setupPost()
    fb.setupHead(unitsPerEm=UPM)

    # Stamp accurate created/modified timestamps.
    # fontTools epoch is 1904-01-01 00:00:00 UTC (Mac epoch).
    _mac_epoch = datetime.datetime(1904, 1, 1, tzinfo=datetime.timezone.utc)
    _now = datetime.datetime.now(tz=datetime.timezone.utc)
    _ts  = int((_now - _mac_epoch).total_seconds())
    fb.font["head"].created  = _ts
    fb.font["head"].modified = _ts

    # GSUB features
    gsub_code = generate_gsub(glyph_infos)
    addOpenTypeFeatures(fb.font, StringIO(gsub_code))

    return fb.font


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    print("Scanning SVG directory...")
    glyph_infos = categorize_svgs(SVG_DIR)
    base_count = sum(1 for i in glyph_infos if not i["is_alt"])
    alt_count = sum(1 for i in glyph_infos if i["is_alt"])
    print(f"  {base_count} base glyphs, {alt_count} alt glyphs")

    print("\nBuilding Vattezhuthu.ttf...")
    base_font = build_font(glyph_infos, is_alt_font=False)
    base_path = os.path.join(OUT_DIR, "Vattezhuthu.ttf")
    base_font.save(base_path)
    print(f"  Saved: {base_path}")

    print("\nBuilding Vattezhuthu-Alt.ttf...")
    alt_font = build_font(glyph_infos, is_alt_font=True)
    alt_path = os.path.join(OUT_DIR, "Vattezhuthu-Alt.ttf")
    alt_font.save(alt_path)
    print(f"  Saved: {alt_path}")

    print("\nDone.")


if __name__ == "__main__":
    main()
