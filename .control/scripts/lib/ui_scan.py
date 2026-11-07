"""`pctl ui-scan`: UI code checks for skills/ui-design.md (stdlib, no browser).

Line-based rules over styles and markup:
  - accessibility (P1/P2): missing alt, removed focus outline, zoom disabled...
  - generic-AI patterns (P3): overused fonts, purple gradients, gradient text...
  - off-token values (P2): colors and fonts missing from the design doc
    (`architecture/design-system.md`: every hex there is allowed; fonts are
    the backticked names on lines that mention "font").
Plus consistency stats (distinct colors, font sizes, radii in use).

Silencing: `ui-scan-disable <rule>` on the line or the line above;
`ui-scan-disable-file <rule>` anywhere in the file; or a design doc line
`ui-scan-allow: rule-a, rule-b` (record why in an ADR).
Rendered-page checks (real contrast, overflow) need a browser: out of scope.
"""
import hashlib
import re

from . import indexes, lean, paths, review, tasks, util

DESIGN_DOC = paths.ARCH_DIR / "design-system.md"
STYLE_EXT = (".css", ".scss", ".sass", ".less")
MARKUP_EXT = (".html", ".htm", ".jsx", ".tsx", ".vue", ".svelte", ".astro")
CONFIG_RX = re.compile(r"(tailwind|theme|tokens?)[^/]*\.(js|ts|mjs|cjs|json)$")
PRIORITY = {"P1": "alta", "P2": "media", "P3": "baja"}
UI_KEY_RX = re.compile(r"ui-key: `([0-9a-f]{10})`")

HEX_RX = re.compile(r"#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b")
FONT_DECL_RX = re.compile(r"(?:font-family|fontFamily)\s*[:=]\s*([^;\n}]+)")
SIZE_RX = re.compile(r"font-size\s*:\s*([^;}\s]+)|\btext-\[(\d[^\]]*)\]")
RADIUS_RX = re.compile(r"border-radius\s*:\s*([^;}]+?)\s*(?:[;}]|$)|\brounded-\[([^\]]+)\]")
GENERIC_FONTS = {"serif", "sans-serif", "monospace", "cursive", "fantasy", "system-ui", "ui-sans-serif",
                 "ui-serif", "ui-monospace", "inherit", "initial", "unset", "-apple-system",
                 "blinkmacsystemfont", "emoji", "math"}
UNDER_075 = r"0?\.(?:[0-6]\d*|7(?:[0-4]\d*)?)"  # .1 to .74 (rem/em under 12px)
OVERUSED = r"Inter|Roboto|Arial|Helvetica|Open Sans|Geist|Poppins|Montserrat"

# (id, priority, file kinds, regex, message). kinds: s=styles, m=markup, c=config
RULES = [
    ("img-no-alt", "P1", "m", re.compile(r"<img\b(?![^>]*\balt\s*=)[^>]*>", re.I),
     "image without alt text (use alt=\"\" if decorative)"),
    ("zoom-disabled", "P1", "m", re.compile(r"user-scalable\s*=\s*(?:no|0)|maximum-scale\s*=\s*1(?:\.0)?\b", re.I),
     "viewport blocks pinch zoom"),
    ("outline-removed", "P1", "sm", re.compile(r"outline\s*:\s*(?:none|0)\b|\boutline-none\b"),
     "focus outline removed; the file has no focus-visible style"),
    ("div-click", "P2", "m", re.compile(r"<(?:div|span)\b[^>]*\s(?:onClick|@click|on:click|v-on:click)\s*=", re.I),
     "clickable div/span: use a button or link (keyboard and screen readers)"),
    ("positive-tabindex", "P2", "m", re.compile(r"tabindex\s*=\s*[\"'{]?\s*[1-9]", re.I),
     "positive tabindex breaks the natural focus order"),
    ("tiny-text", "P2", "sm", re.compile(rf"font-size\s*:\s*(?:(?:[0-9]|1[01])(?:\.\d+)?px|{UNDER_075}r?em)\b"
                                          rf"|\btext-\[(?:(?:[0-9]|1[01])px|{UNDER_075}rem)\]"),
     "text under 12px"),
    ("lorem", "P2", "m", re.compile(r"\blorem ipsum\b", re.I), "placeholder copy"),
    ("overused-font", "P3", "smc", re.compile(rf"(?:font-family|fontFamily)\s*[:=][^;\n]*\b(?:{OVERUSED})\b"
                                              rf"|fonts\.googleapis\.com/css2?\?family=(?:{OVERUSED.replace(' ', '[+ ]')})\b"
                                              rf"|next/font/google['\"].*\b(?:{OVERUSED.replace(' ', '_')})\b"),
     "default font as identity; pick a pairing for the personality"),
    ("ai-gradient", "P3", "smc", re.compile(r"\bfrom-(?:purple|violet|indigo|fuchsia)-\d+\b.*\bto-(?:blue|cyan|sky|indigo|purple|pink|fuchsia)-\d+"
                                            r"|gradient\([^)]*(?:purple|violet|indigo|#8b5cf6|#7c3aed|#a855f7|#6366f1|#9333ea)", re.I),
     "purple/blue gradient, the default AI look"),
    ("gradient-text", "P3", "sm", re.compile(r"background-clip\s*:\s*text|\bbg-clip-text\b"), "gradient text"),
    ("side-stripe", "P3", "sm", re.compile(r"\bborder-l-(?:[4-9]|\[\d+px\])\b|border-left\s*:\s*(?:[4-9]|\d\d)px\s+solid"),
     "thick colored stripe on one side of a card"),
    ("glow-blob", "P3", "sm", re.compile(r"\bshadow-(?:purple|violet|indigo|cyan|fuchsia|pink)-\d+|\bblur-3xl\b"
                                         r"|box-shadow\s*:[^;]*\b0\s+0\s+\d{2,}px[^;]*(?:#|rgba?\()"),
     "glow or blurred blob as decoration"),
    ("bouncy-motion", "P3", "sm", re.compile(r"\banimate-(?:bounce|ping)\b|<marquee\b|\bmarquee\b[^;\n]*(?:animation|infinite)"
                                             r"|cubic-bezier\([^)]*,\s*-?(?:1\.[1-9]|[2-9])"),
     "bouncy, pinging or marquee motion"),
    ("justified-text", "P3", "sm", re.compile(r"text-align\s*:\s*justify|\btext-justify\b"), "justified text (rivers, harder to read)"),
    ("hype-copy", "P3", "m", re.compile(r"\b(?:seamless(?:ly)?|supercharge\w*|world-class|unlock(?:s|ing)? (?:the|your)|revolutioni[sz]\w+"
                                        r"|effortless(?:ly)?|next-level|cutting-edge|game-?chang\w+|elevate your)\b", re.I),
     "empty superlative; say the specific benefit"),
]


def _kind(rel):
    low = rel.lower()
    if low.endswith(".min.css") or low.endswith(".min.js"):
        return ""
    if low.endswith(STYLE_EXT):
        return "s"
    if low.endswith(MARKUP_EXT):
        return "m"
    return "c" if CONFIG_RX.search(low) else ""


def _norm_hex(h):
    h = h.lower().lstrip("#")
    return "#" + ("".join(c * 2 for c in h) if len(h) == 3 else h)


def design_doc():
    """(rel or None, allowed colors, allowed fonts, allowed rule ids)."""
    if not DESIGN_DOC.exists():
        return None, set(), set(), set()
    text = DESIGN_DOC.read_text(encoding="utf-8")
    colors = {_norm_hex(h) for h in HEX_RX.findall(text)}
    fonts = {f.lower() for line in text.splitlines() if "font" in line.lower()
             for f in re.findall(r"`([^`]+)`", line)}
    allow = set()
    for m in re.finditer(r"ui-scan-allow:\s*(.+)", text):
        allow |= {r.strip() for r in m.group(1).split(",") if r.strip()}
    return DESIGN_DOC.relative_to(util.PROJECT_ROOT).as_posix(), colors, fonts, allow


def _fonts_in(decl):
    names = [n.strip().strip("'\"` ").lower() for n in re.split(r"[,\[\]]", decl)]
    return [n for n in names if n and n not in GENERIC_FONTS and not n.startswith(("var(", "$", "theme("))
            and re.match(r"^[a-z][a-z0-9 _-]*$", n)]


def _disabled(rule, lines, n, file_off):
    if rule in file_off:
        return True
    near = lines[n - 1] + (lines[n - 2] if n > 1 else "")
    return f"ui-scan-disable {rule}" in near


OPEN_TAG_RX = re.compile(r"<[A-Za-z][\w.-]*\b[^<>]*$")


def _whole_tag(lines, i, max_lines=15):
    """Line i, joined with the next lines while a tag opened on it is still unclosed."""
    out = lines[i]
    j = i
    while OPEN_TAG_RX.search(out) and j + 1 < len(lines) and j - i < max_lines:
        j += 1
        out += " " + lines[j].strip()
    return out


def scan(include=None):
    """(findings, stats, doc_rel). finding: {rule, prio, msg, rel, line}."""
    doc_rel, colors, fonts, allow = design_doc()
    findings, used = [], {"colors": set(), "font sizes": set(), "radii": set()}
    for rel in util.project_files(include):
        kind = _kind(rel)
        if not kind:
            continue
        lines = util.read_lines(rel)
        text = "\n".join(lines)
        file_off = set(re.findall(r"ui-scan-disable-file\s+([\w-]+)", text))
        has_focus_style = "focus-visible" in text
        for n, line in enumerate(lines, 1):
            hits = []
            target = _whole_tag(lines, n - 1) if kind == "m" else line
            for rid, prio, kinds, rx, msg in RULES:
                if kind in kinds and rid not in allow and rx.search(target):
                    if (rid == "outline-removed" and has_focus_style) or \
                            (rid == "side-stripe" and "blockquote" in line):
                        continue
                    hits.append((rid, prio, msg))
            hexes = {_norm_hex(h) for h in HEX_RX.findall(line)} if kind in "sc" or "[#" in line else set()
            used["colors"] |= hexes
            used["font sizes"] |= {a or b for a, b in SIZE_RX.findall(line)}
            used["radii"] |= {a or b for a, b in RADIUS_RX.findall(line)}
            if doc_rel and colors and "off-token-color" not in allow:
                off = sorted(h for h in hexes if h not in colors)
                if off:
                    hits.append(("off-token-color", "P2", "color not in the design doc: " + ", ".join(off)))
            if doc_rel and fonts and "off-token-font" not in allow:
                for m in FONT_DECL_RX.finditer(line):
                    off = [f for f in _fonts_in(m.group(1)) if f not in fonts]
                    if off:
                        hits.append(("off-token-font", "P2", "font not in the design doc: " + ", ".join(off)))
            for rid, prio, msg in hits:
                if not _disabled(rid, lines, n, file_off):
                    findings.append({"rule": rid, "prio": prio, "msg": msg, "rel": rel, "line": n})
    stats = {k: len(v) for k, v in used.items()}
    return findings, stats, doc_rel


def _group(findings):
    groups = {}
    for f in findings:
        groups.setdefault((f["prio"], f["rule"]), []).append(f)
    return sorted(groups.items())


def report(include=None, changed_base=None, apply=False, limit=8):
    """(text, number of findings)."""
    findings, stats, doc_rel = scan(include)
    if changed_base:
        hunks = review.changed_hunks(changed_base)
        findings = [f for f in findings if any(s <= f["line"] <= e for s, e in hunks.get(f["rel"], []))]
    files = {f["rel"] for f in findings}
    lines = [f"ui-scan: {len(findings)} finding(s) in {len(files)} file(s); design doc: "
             + (doc_rel or "none (tokens unchecked; see skills/ui-design.md phase 3)")]
    tracked = lean.tracked_keys(UI_KEY_RX) if apply else {}
    created = []
    for (prio, rid), items in _group(findings):
        per_line = rid.startswith("off-token")  # message differs per location
        lines.append(f"{prio} {rid} x{len(items)}" + ("" if per_line else f": {items[0]['msg']}"))
        for f in items[:limit]:
            extra = f"  ({f['msg']})" if per_line else ""
            lines.append(f"  {f['rel']}:{f['line']}{extra}")
        if len(items) > limit:
            lines.append(f"  ... {len(items) - limit} more")
        if apply:
            key = hashlib.sha1(f"ui|{rid}".encode()).hexdigest()[:10]
            if key in tracked and tracked[key][1] != "done":
                lines.append(f"  tracked by {tracked[key][0]}")
                continue
            tid, _ = tasks.new_task(f"UI {prio}: {rid} ({len(items)})", prioridad=PRIORITY[prio],
                                    tipo="bug" if prio == "P1" else "chore", creado_por="agente")
            locs = "\n".join(f"- `{f['rel']}:{f['line']}`" for f in items[:30])
            tasks.set_body(tid, (
                f"\n## Contexto\n\n`pctl ui-scan` rule `{rid}`: {items[0]['msg']}. "
                f"See skills/ui-design.md.\n\n{locs}\n\nui-key: `{key}`\n\n"
                "## Criterios de aceptacion\n- [ ] `pctl ui-scan` no longer reports this rule "
                "(fixed, or silenced with the reason recorded)\n\n## Notas del agente\n\n"))
            created.append(tid)
    if created:
        indexes.reindex()
        lines.append("Created tasks: " + ", ".join(created))
    lines.append("In use: " + ", ".join(f"{v} {k}" for k, v in stats.items())
                 + " (many near-duplicates = consolidate into design tokens)")
    return "\n".join(lines), len(findings)


def brief_line():
    """One brief line when the project has UI files; scans only changed lines (cheap)."""
    ui = [r for r in util.project_files() if _kind(r) in ("s", "m")]
    if not ui:
        return None
    doc_rel = design_doc()[0]
    line = "UI: work follows `.control/skills/ui-design.md`" + ("" if doc_rel else " (no design doc yet)")
    hunks = review.changed_hunks("HEAD")
    changed = [r for r in ui if r in hunks]
    if changed:
        p1 = [f for f in scan(changed)[0] if f["prio"] == "P1"
              and any(s <= f["line"] <= e for s, e in hunks[f["rel"]])]
        if p1:
            line += f"; {len(p1)} P1 in uncommitted changes (`pctl ui-scan --changed`)"
    return line + "."
