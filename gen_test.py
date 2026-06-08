#!/usr/bin/env python3
"""Generate self-contained test HTML for Vattezhuthu font."""

import os
import base64
from datetime import datetime
from fontTools.ttLib import TTFont

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
SVG_DIR   = os.path.join(BASE_DIR, "svg")
FONTS_DIR = os.path.join(BASE_DIR, "fonts")
OUTPUT    = os.path.join(BASE_DIR, "docs", "index.html")

# ── Unicode data ─────────────────────────────────────────────────────────────

VOWEL_CP = {
    "a": 0x0D05, "aa": 0x0D06, "i": 0x0D07, "ii": 0x0D08, "u": 0x0D09,
    "e": 0x0D0E, "ee": 0x0D0F, "o": 0x0D12, "oo": 0x0D13,
}
VOWEL_ORDER = ["a", "aa", "i", "ii", "u", "e", "ee", "o", "oo"]

CONSONANT_CP = {
    "ka":0x0D15, "nga":0x0D19, "ca":0x0D1A, "nya":0x0D1E,
    "tta":0x0D1F, "nna":0x0D23, "ta":0x0D24, "na":0x0D28,
    "nnna":0x0D29, "pa":0x0D2A, "ma":0x0D2E, "ya":0x0D2F,
    "ra":0x0D30, "rra":0x0D31, "la":0x0D32, "lla":0x0D33,
    "llla":0x0D34, "va":0x0D35,
}
CONSONANT_ORDER = [
    "ka","nga","ca","nya","tta","nna","ta","na","nnna",
    "pa","ma","ya","ra","rra","la","lla","llla","va"
]

MATRA_CP = {
    "aa":[0x0D3E], "i":[0x0D3F], "ii":[0x0D40], "u":[0x0D41],
    "uu":[0x0D42], "e":[0x0D46], "ee":[0x0D47], "ai":[0x0D48],
    "o":[0x0D46,0x0D3E], "oo":[0x0D47,0x0D3E],
}
MATRA_ORDER = ["aa","i","ii","u","uu","e","ee","ai","o","oo"]

# Standalone vowel letter corresponding to each matra (for column headers)
MATRA_VOWEL = {
    "aa":0x0D06, "i":0x0D07, "ii":0x0D08, "u":0x0D09, "uu":0x0D0A,
    "e":0x0D0E,  "ee":0x0D0F, "ai":0x0D10, "o":0x0D12, "oo":0x0D13,
}

# ── Helpers ──────────────────────────────────────────────────────────────────

def b64font(name):
    with open(os.path.join(FONTS_DIR, name), "rb") as f:
        return base64.b64encode(f.read()).decode()

def cps(lst): return "".join(chr(c) for c in lst)
def combo_char(c, m): return chr(CONSONANT_CP[c]) + cps(MATRA_CP[m])
def cp_label(cps_list): return " ".join(f"U+{cp:04X}" for cp in cps_list)

def scan_svgs():
    consonants = sorted(CONSONANT_CP.keys(), key=len, reverse=True)
    combos, has_alt = set(), set()
    for fname in sorted(os.listdir(SVG_DIR)):
        if not fname.endswith(".svg"): continue
        stem = fname[:-4]
        is_alt = stem.endswith("-alt")
        base = stem[:-4] if is_alt else stem
        for c in consonants:
            if base == c:
                if is_alt: has_alt.add("gundert." + c)
                break
            if base.startswith(c + "-"):
                suf = base[len(c)+1:]
                if suf in MATRA_CP:
                    g = f"gundert.{c}_{suf}"
                    if is_alt: has_alt.add(g)
                    else: combos.add((c, suf))
                break
        else:
            for v in VOWEL_CP:
                if base == v:
                    if is_alt: has_alt.add("gundert." + v)
                    break
    return combos, has_alt

def font_meta():
    """Read version from Vattezhuthu.ttf name table."""
    try:
        tt = TTFont(os.path.join(FONTS_DIR, "Vattezhuthu.ttf"))
        ver = tt["name"].getDebugName(5) or "—"
    except Exception:
        ver = "—"
    return ver


# ── Section 1: Character Map (side-by-side tables) ───────────────────────────

def section_charmap(combos, has_alt):
    TH = ("<tr><th>Name</th><th>Malayalam</th>"
          "<th>Vattezhuthu</th><th>Alt</th></tr>")

    def rows(names, cp_map):
        out = []
        for n in names:
            cp   = cp_map[n]
            ch   = chr(cp)
            gn   = f"gundert.{n}"
            altg = f'<span class="gf-alt-font">{ch}</span>' if gn in has_alt else "—"
            out.append(
                f"<tr>"
                f"<td class='cn'>{n}</td>"
                f"<td class='cml sysml'>{ch}</td>"
                f"<td class='cg gf-base-font'>{ch}</td>"
                f"<td class='cga'>{altg}</td>"
                f"</tr>"
            )
        return "".join(out)

    vtbl = f"<table class='char-table'>{TH}{rows(VOWEL_ORDER, VOWEL_CP)}</table>"
    ctbl = f"<table class='char-table'>{TH}{rows(CONSONANT_ORDER, CONSONANT_CP)}</table>"

    return f"""
<section id="charmap">
  <h2>Character Map</h2>
  <div class="charmap-wrap">
    <div class="charmap-col">
      <h3>Vowels <span class="cnt">({len(VOWEL_ORDER)})</span></h3>
      {vtbl}
    </div>
    <div class="charmap-col">
      <h3>Consonants <span class="cnt">({len(CONSONANT_ORDER)})</span></h3>
      {ctbl}
    </div>
  </div>
</section>"""


# ── Section 2: Combination Grid ───────────────────────────────────────────────

def section_grid(combos, has_alt):

    def g_pair(char, gname):
        """Vattezhuthu glyph cell: base · alt if available."""
        base = f"<span class='gf-base-font'>{char}</span>"
        if gname in has_alt:
            return base + f"<span class='sep'>·</span><span class='gf-alt-font'>{char}</span>"
        return base

    # ── Header row 1: Malayalam vowel letters (system font) ──────────────────
    hdr1 = "<tr><th class='corner' colspan='2'></th>"
    for m in MATRA_ORDER:
        vc = MATRA_VOWEL[m]
        hdr1 += f"<th class='mhdr'><span class='sysml mhdr-ch'>{chr(vc)}</span></th>"
    hdr1 += "</tr>"

    # ── Header row 2: same vowels in Gundert ─────────────────────────────────
    hdr2 = "<tr><th class='ghdr' colspan='2'>Vattezhuthu</th>"
    for m in MATRA_ORDER:
        vc    = MATRA_VOWEL[m]
        vch   = chr(vc)
        gname = f"gundert.{m}"      # standalone vowel glyph
        hdr2 += f"<td class='gv-cell'>{g_pair(vch, gname)}</td>"
    hdr2 += "</tr>"

    # ── Consonant rows ────────────────────────────────────────────────────────
    data = []
    for c in CONSONANT_ORDER:
        cp   = CONSONANT_CP[c]
        char = chr(cp)
        gname_con = f"gundert.{c}"
        row = (
            f"<tr>"
            f"<th class='con-sys'><span class='sysml'>{char}</span></th>"
            f"<th class='con-g'>{g_pair(char, gname_con)}</th>"
        )
        for m in MATRA_ORDER:
            if (c, m) in combos:
                seq   = combo_char(c, m)
                gname = f"gundert.{c}_{m}"
                row += f"<td class='cc'>{g_pair(seq, gname)}</td>"
            else:
                row += "<td class='ec'>—</td>"
        row += "</tr>"
        data.append(row)

    return f"""
<section id="grid">
  <h2>Combination Grid
    <span class="cnt" style="font-size:13px;font-weight:normal;margin-left:8px">
      {len(combos)} combos · base · alt where available
    </span>
  </h2>
  <div class="grid-scroll">
    <table class="combo-grid">
      {hdr1}{hdr2}{"".join(data)}
    </table>
  </div>
</section>"""


# ── Section 3: All Glyphs (compact) ──────────────────────────────────────────

def section_all_glyphs(combos, has_alt):
    def card(char, gname, label, cp_str):
        base = f'<span class="gf-base-font cg">{char}</span>'
        if gname in has_alt:
            alt  = f'<span class="gf-alt-font cg calt">{char}</span>'
            body = base + f'<span class="csep">·</span>' + alt
            wcls = "cw"
        else:
            body = base
            wcls = ""
        return (
            f'<div class="gc {wcls}">'
            f'<div class="cgl">{body}</div>'
            f'<div class="cgi"><code>{label}</code><small>{cp_str}</small></div>'
            f'</div>'
        )

    vc = "".join(
        card(chr(VOWEL_CP[n]), f"gundert.{n}", n, f"U+{VOWEL_CP[n]:04X}")
        for n in VOWEL_ORDER
    )
    cc_con = "".join(
        card(chr(CONSONANT_CP[n]), f"gundert.{n}", n, f"U+{CONSONANT_CP[n]:04X}")
        for n in CONSONANT_ORDER
    )

    combo_groups = ""
    for c in CONSONANT_ORDER:
        cards = []
        for m in MATRA_ORDER:
            if (c, m) in combos:
                seq  = combo_char(c, m)
                cpl  = [CONSONANT_CP[c]] + MATRA_CP[m]
                gn   = f"gundert.{c}_{m}"
                cards.append(card(seq, gn, f"{c}-{m}", cp_label(cpl)))
        if cards:
            combo_groups += (
                f'<div class="cgrp">'
                f'<h4>{c} <span class="cnt">({len(cards)})</span></h4>'
                f'<div class="gg">{"".join(cards)}</div>'
                f'</div>'
            )

    total_base = len(VOWEL_ORDER) + len(CONSONANT_ORDER) + len(combos)
    return f"""
<section id="allglyphs">
  <h2>All Glyphs</h2>
  <p class="note">{total_base} base · {len(has_alt)} alternates.
    <span class="sep-note">Left = Vattezhuthu · Right = Alt (when available)</span></p>

  <h3>Vowels <span class="cnt">({len(VOWEL_ORDER)})</span></h3>
  <div class="gg">{vc}</div>

  <h3>Consonants <span class="cnt">({len(CONSONANT_ORDER)})</span></h3>
  <div class="gg">{cc_con}</div>

  <h3>Combinations <span class="cnt">({len(combos)})</span></h3>
  {combo_groups}
</section>"""


# ── Section 4: HarfBuzz Proof ────────────────────────────────────────────────

def section_hbproof():
    ST = {
        "ok":  '<span class="st st-ok">✓ Works</span>',
        "par": '<span class="st st-par">◑ Partial</span>',
        "no":  '<span class="st st-no">□ Not in font</span>',
        "des": '<span class="st st-des">◎ By design</span>',
    }

    def row(label, seq, st_key, note):
        cp_str = " ".join(f"U+{ord(c):04X}" for c in seq)
        return (
            f"<tr>"
            f"<td class='pl'>{label}</td>"
            f"<td class='pcp'><code>{cp_str}</code></td>"
            f"<td class='pg gf-base-font'>{seq}</td>"
            f"<td class='ps'>{ST[st_key]}</td>"
            f"<td class='pn'>{note}</td>"
            f"<td class='pr sysml'>{seq}</td>"
            f"</tr>"
        )

    V   = chr(0x0D15)   # ക
    VIR = chr(0x0D4D)   # ്
    NG  = chr(0x0D19)   # ങ
    CA  = chr(0x0D1A)   # ച
    TA  = chr(0x0D24)   # ത
    LA  = chr(0x0D33)   # ള
    KHA = chr(0x0D16)   # ഖ
    UU  = chr(0x0D0A)   # ഊ independent (not in font)
    AA  = chr(0x0D3E)
    I   = chr(0x0D3F)
    II  = chr(0x0D40)
    E   = chr(0x0D46)
    EE  = chr(0x0D47)
    AI  = chr(0x0D48)

    liga_seq = V + AA
    conj_seq = V + VIR + V

    trows = "".join([
        row("a — vowel",                chr(0x0D05),  "ok",  "gundert.a ✓"),
        row("ka — consonant",           V,            "ok",  "gundert.ka ✓"),
        row("ka + aa",                  V+AA,         "ok",  "liga → gundert.ka_aa"),
        row("ka + i",                   V+I,          "ok",  "liga → gundert.ka_i"),
        row("ka + split-o  (3 cps)",    V+E+AA,       "ok",  "liga → gundert.ka_o"),
        row("ta + split-oo (3 cps)",    TA+EE+AA,     "ok",  "liga → gundert.ta_oo"),
        row("ca + ee",                  CA+EE,        "ok",  "liga → gundert.ca_ee"),
        row("ca + ai",                  CA+AI,        "ok",  "liga → gundert.ca_ai"),
        row("nga + aa  (no combos)",    NG+AA,        "par", "gundert.nga · aa matra invisible"),
        row("ca + ii  (combo missing)", CA+II,        "par", "gundert.ca · ii matra invisible"),
        row("lla + split-oo (missing)", LA+EE+AA,     "par", "gundert.lla · matras invisible"),
        row("kha  (not covered)",       KHA,          "no",  "U+0D16 → noglyph placeholder"),
        row("ഊ independent (missing)",  UU,           "no",  "U+0D0A → noglyph placeholder"),
        row("ka + virama + ka",         conj_seq,     "des", "no conjunct; virama → box; 3 glyphs"),
    ])

    return f"""
<section id="hbproof">
  <h2>HarfBuzz Proof</h2>

  <h3>Script Declaration</h3>
  <p>The font declares <code>languagesystem DFLT dflt;</code> only — no <code>mlym</code> / <code>mlm2</code>.
  HarfBuzz activates the Malayalam shaper only when it sees those script tags in the GSUB ScriptList.
  Without them: default shaper runs — no reordering, no halant/virama logic, no conjuncts.
  All combinations come from explicit <code>liga</code> GSUB&nbsp;Type&nbsp;4 rules.</p>
<pre class="fea">languagesystem DFLT dflt;   /* no "languagesystem mlym dflt;" */

feature liga {{
  lookup liga_vattezhuthu {{
    sub gundert.ka uni0D3E by gundert.ka_aa;          /* 2-cp */
    sub gundert.ka uni0D46 uni0D3E by gundert.ka_o;   /* 3-cp split matra */
    /* … 104 rules total */
  }} liga_vattezhuthu;
}} liga;</pre>

  <h3>Rendering Tests</h3>
  <p>Vattezhuthu column is primary. System (rightmost) is reference only.</p>
  <table class="ptbl">
    <tr>
      <th>Input</th><th>Codepoints</th>
      <th class="pt-g">Vattezhuthu</th><th>Status</th><th>Notes</th>
      <th class="pt-r">System<br><small>(ref)</small></th>
    </tr>
    {trows}
  </table>

  <h3>liga Toggle — proof it's GSUB, not shaping</h3>
  <div class="ldemo">
    <div class="lc">
      <div class="ll"><code>"liga" 1</code> on (default)</div>
      <div class="gf-base-font ls">{liga_seq}</div>
    </div>
    <div class="lc">
      <div class="ll"><code>"liga" 0</code> off</div>
      <div class="gf-base-font ls loff">{liga_seq}</div>
      <p class="lnote">ka shows; matra invisible (zero-width placeholder)</p>
    </div>
  </div>

  <h3>Virama — No Conjunct</h3>
  <div class="ldemo">
    <div class="lc">
      <div class="ll">Vattezhuthu — ക + ് + ക</div>
      <div class="gf-base-font ls">{conj_seq}</div>
      <p class="lnote">3 glyphs: ka · noglyph-box · ka</p>
    </div>
    <div class="lc lc-ref">
      <div class="ll">System (reference)</div>
      <div class="sysml ls-ref">{conj_seq}</div>
      <p class="lnote">System Malayalam forms a conjunct</p>
    </div>
  </div>
</section>"""


# ── CSS ───────────────────────────────────────────────────────────────────────

CSS = r"""
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
     font-size:13px;color:#1a1a1a;background:#ebebeb;padding:20px}

@font-face{font-family:'Vattezhuthu';   src:url('data:font/ttf;base64,BASE_FONT') format('truetype')}
@font-face{font-family:'VattezhuthuAlt';src:url('data:font/ttf;base64,ALT_FONT')  format('truetype')}
.gf-base-font{font-family:'Vattezhuthu',   serif}
.gf-alt-font {font-family:'VattezhuthuAlt',serif}
.sysml       {font-family:'Noto Sans Malayalam','Kailasa','AnjaliOldLipi',serif}

/* layout */
header{margin-bottom:20px}
header h1{font-size:24px;font-weight:700}
header p{color:#666;margin-top:3px;font-size:12px}
nav{display:flex;gap:14px;margin-bottom:20px;border-bottom:1px solid #ccc;padding-bottom:10px}
nav a{color:#0066cc;text-decoration:none;font-size:12px}
nav a:hover{text-decoration:underline}
section{background:#fff;border:1px solid #ddd;border-radius:7px;padding:20px;margin-bottom:20px}
h2{font-size:17px;margin-bottom:14px}
h3{font-size:13px;font-weight:600;margin:16px 0 8px;color:#333;
   border-bottom:1px solid #eee;padding-bottom:3px}
h4{font-size:12px;color:#666;margin:12px 0 5px}
p{font-size:12px;color:#555;line-height:1.5;margin-bottom:8px}
code{font-size:11px;background:#f3f3f3;padding:1px 4px;border-radius:3px}
.note{font-size:11px;color:#888;margin-bottom:10px}
.sep-note{color:#bbb;margin-left:6px}
.cnt{color:#aaa;font-weight:normal}
.sep{color:#ccc;margin:0 2px;font-size:10px}

/* ── charmap ── */
.charmap-wrap{display:flex;gap:20px;align-items:flex-start;flex-wrap:wrap}
.charmap-col{flex:1;min-width:260px}
.char-table{border-collapse:collapse;font-size:12px;width:100%}
.char-table th{background:#f5f5f5;text-align:left;padding:5px 10px;
               border-bottom:2px solid #ddd;font-size:11px;color:#666}
.char-table td{padding:4px 10px;border-bottom:1px solid #f0f0f0;vertical-align:middle}
.cn {font-size:11px;color:#888;font-style:italic;min-width:50px}
.cml{font-size:32px;line-height:1.1}
.cg {font-size:32px;line-height:1.1}
.cga{font-size:32px;line-height:1.1;color:#666}

/* ── combo grid ── */
.grid-scroll{overflow-x:auto;padding-bottom:4px}
.combo-grid{border-collapse:collapse}
.combo-grid th,.combo-grid td{border:1px solid #e0e0e0}

.corner{background:#f5f5f5;min-width:120px}
.mhdr{background:#f8f8f8;text-align:center;padding:5px 3px;min-width:60px}
.mhdr-ch{font-size:26px;display:block;line-height:1}
.ghdr{background:#eef2ff;text-align:center;font-size:11px;color:#446;
      padding:5px 8px;font-weight:600}
.gv-cell{background:#eef2ff;text-align:center;padding:3px 5px;white-space:nowrap}
.gv-cell .gf-base-font,.gv-cell .gf-alt-font{font-size:26px;vertical-align:middle}

/* row header: 2 sticky columns */
.con-sys{background:#f8f8f8;text-align:center;padding:5px 8px;
         position:sticky;left:0;z-index:2;min-width:52px}
.con-sys .sysml{font-size:28px;display:block;line-height:1.1}
.con-g{background:#f0f0f0;text-align:center;padding:5px 8px;
       position:sticky;left:52px;z-index:2;min-width:72px;white-space:nowrap}
.con-g .gf-base-font,.con-g .gf-alt-font{font-size:28px;vertical-align:middle}

.cc{text-align:center;padding:3px 4px;white-space:nowrap;vertical-align:middle}
.cc .gf-base-font,.cc .gf-alt-font{font-size:28px;vertical-align:middle}
.ec{text-align:center;color:#ccc;font-size:11px;padding:4px}

/* ── all glyphs ── */
.gg{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px}
.gc{border:1px solid #e4e4e4;border-radius:5px;background:#fafafa;
    width:72px;display:flex;flex-direction:column;align-items:center;
    padding:6px 3px 5px;overflow:hidden}
.cw{width:120px}
.cgl{font-size:32px;line-height:1.25;text-align:center;white-space:nowrap}
.cg{display:inline-block;vertical-align:middle}
.calt{color:#777}
.csep{color:#ddd;font-size:9px;margin:0 1px;vertical-align:middle}
.cgi{text-align:center;margin-top:3px}
.cgi code{font-size:8px;color:#777;display:block;word-break:break-all;line-height:1.3}
.cgi small{font-size:8px;color:#bbb;display:block}
.cgrp{margin-bottom:12px}

/* ── HarfBuzz proof ── */
pre.fea{background:#1e1e1e;color:#d4d4d4;padding:14px;border-radius:6px;
        font-size:11px;line-height:1.6;overflow-x:auto;margin:10px 0;
        font-family:'Menlo','Consolas',monospace}
.ptbl{border-collapse:collapse;width:100%;font-size:12px;margin:10px 0}
.ptbl th{background:#f5f5f5;padding:6px 10px;text-align:left;
         border-bottom:2px solid #ddd;font-size:11px;color:#666;white-space:nowrap}
.ptbl td{padding:6px 10px;border-bottom:1px solid #eee;vertical-align:middle}
.pl{font-weight:600;font-size:12px;white-space:nowrap}
.pcp{font-size:10px;color:#999;white-space:nowrap}
.pg{font-size:38px;line-height:1}          /* Gundert — large, primary */
.pt-g{min-width:80px}
.ps{white-space:nowrap}
.pn{font-size:11px;color:#666}
.pr{font-size:22px;line-height:1;color:#888} /* System — smaller, secondary */
.pt-r{min-width:60px;color:#aaa;font-size:11px;text-align:center}

.st{display:inline-block;font-size:10px;font-weight:700;
    padding:2px 6px;border-radius:3px;white-space:nowrap}
.st-ok {background:#d4edda;color:#1a6630}
.st-par{background:#fff3cd;color:#7a5800}
.st-no {background:#e9e9e9;color:#666}
.st-des{background:#dae8ff;color:#1a55a0}

.ldemo{display:flex;gap:12px;margin:12px 0 6px;flex-wrap:wrap}
.lc{flex:1;min-width:150px;border:1px solid #e0e0e0;border-radius:6px;
    padding:12px;background:#fafafa}
.lc-ref{border-color:#ddd;opacity:.7}
.ll{font-size:10px;color:#777;margin-bottom:6px}
.ls{font-size:52px;line-height:1.1}
.ls-ref{font-size:32px;line-height:1.1;color:#888}
.loff{font-feature-settings:"liga" 0}
.lnote{font-size:10px;color:#aaa;margin-top:5px}

/* ── footer ── */
footer{margin-top:8px;padding:12px 0;border-top:1px solid #ddd;
       font-size:11px;color:#aaa;display:flex;justify-content:space-between}
"""


# ── HTML ─────────────────────────────────────────────────────────────────────

def generate_html(base_b64, alt_b64, combos, has_alt, font_ver, generated):
    css = CSS.replace("BASE_FONT", base_b64).replace("ALT_FONT", alt_b64)
    base_count = len(VOWEL_ORDER) + len(CONSONANT_ORDER) + len(combos)
    total      = base_count + len(has_alt)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Vattezhuthu — Font Test</title>
<style>{css}</style>
</head>
<body>

<header>
  <h1>Vattezhuthu</h1>
  <p>Malayalam Unicode · {base_count} base glyphs · {len(has_alt)} alternates · {total} total</p>
</header>

<nav>
  <a href="#charmap">Character Map</a>
  <a href="#grid">Combination Grid</a>
  <a href="#allglyphs">All Glyphs</a>
  <a href="#hbproof">HarfBuzz Proof</a>
</nav>

{section_charmap(combos, has_alt)}
{section_grid(combos, has_alt)}
{section_all_glyphs(combos, has_alt)}
{section_hbproof()}

<footer>
  <span>Generated: {generated}</span>
  <span>Font: {font_ver}</span>
</footer>

</body>
</html>"""


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("Encoding fonts...")
    base_b64 = b64font("Vattezhuthu.ttf")
    alt_b64  = b64font("Vattezhuthu-Alt.ttf")

    print("Scanning SVGs...")
    combos, has_alt = scan_svgs()

    font_ver  = font_meta()
    generated = datetime.now().strftime("%Y-%m-%d  %H:%M")

    print("Generating HTML...")
    html = generate_html(base_b64, alt_b64, combos, has_alt, font_ver, generated)

    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(html)

    size_kb = os.path.getsize(OUTPUT) // 1024
    print(f"Written: {OUTPUT}  ({size_kb} KB)")
    print(f"Font: {font_ver}  ·  Generated: {generated}")


if __name__ == "__main__":
    main()
