import re

_HEADING_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)


def split_sections(body):
    """Devuelve un dict ordenado {titulo_seccion: contenido} a partir de
    un cuerpo markdown con encabezados '## Titulo'."""
    matches = list(_HEADING_RE.finditer(body))
    sections = {}
    for i, m in enumerate(matches):
        title = m.group(1).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        sections[title] = body[start:end].strip("\n")
    return sections


def join_sections(order, sections):
    """Reconstruye el cuerpo a partir de una lista de titulos en orden y
    un dict {titulo: contenido}."""
    parts = []
    for title in order:
        content = sections.get(title, "")
        parts.append(f"## {title}\n\n{content}\n")
    return "\n" + "\n".join(parts)


_CHECKBOX_RE = re.compile(r"^-\s*\[( |x|X)\]\s*(.*)$", re.MULTILINE)


def parse_checkboxes(text):
    out = []
    for m in _CHECKBOX_RE.finditer(text or ""):
        out.append({"checked": m.group(1).lower() == "x", "texto": m.group(2).strip()})
    return out


def render_checkboxes(items):
    if not items:
        return "- [ ] "
    lines = []
    for it in items:
        mark = "x" if it.get("checked") else " "
        lines.append(f"- [{mark}] {it.get('texto','')}")
    return "\n".join(lines)
