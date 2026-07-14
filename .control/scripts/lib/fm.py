"""Parser/escritor minimalista de frontmatter YAML (sin dependencias
externas). Soporta: strings, numeros, null, listas simples en una
linea ([a, b, c] o []), y fechas como strings YYYY-MM-DD.
No pretende ser un parser YAML completo -- solo lo que el schema usa.
"""
import re

FM_DELIM = "---"


def parse(text):
    """Devuelve (dict_frontmatter, cuerpo_markdown)."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != FM_DELIM:
        return {}, text
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == FM_DELIM:
            end = i
            break
    if end is None:
        return {}, text
    fm_lines = lines[1:end]
    body = "\n".join(lines[end + 1:]).lstrip("\n")
    data = {}
    for line in fm_lines:
        if not line.strip() or line.strip().startswith("#"):
            continue
        m = re.match(r"^([a-zA-Z_][a-zA-Z0-9_]*):\s*(.*)$", line)
        if not m:
            continue
        key, raw = m.group(1), m.group(2).strip()
        data[key] = _parse_value(raw)
    return data, body


def _parse_value(raw):
    if raw == "" or raw == "null" or raw == "~":
        return None
    if raw.startswith("[") and raw.endswith("]"):
        inner = raw[1:-1].strip()
        if not inner:
            return []
        return [v.strip().strip('"').strip("'") for v in inner.split(",")]
    if raw.startswith('"') and raw.endswith('"'):
        return raw[1:-1]
    if raw.startswith("'") and raw.endswith("'"):
        return raw[1:-1]
    if re.match(r"^-?\d+$", raw):
        return int(raw)
    if raw in ("true", "false"):
        return raw == "true"
    return raw


def _dump_value(v):
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, list):
        return "[" + ", ".join(str(x) for x in v) + "]"
    if isinstance(v, int):
        return str(v)
    return str(v)


def dump(data, body, key_order=None):
    keys = key_order or list(data.keys())
    fm_lines = [FM_DELIM]
    for k in keys:
        if k in data:
            fm_lines.append(f"{k}: {_dump_value(data[k])}")
    fm_lines.append(FM_DELIM)
    fm_lines.append("")
    return "\n".join(fm_lines) + (body or "")
