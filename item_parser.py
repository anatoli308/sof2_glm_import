import re
from typing import Dict, List, Any, Union


def _strip_inline_comment(s: str) -> str:
    """Remove inline comments from a line."""
    return re.sub(r"//.*$", "", s).strip()


def _to_native(val: str) -> Union[str, int, float, bool]:
    """Convert string value to native Python type."""
    if val is None:
        return None
    v = val.strip()
    if not v:
        return ""
    low = v.lower()
    if low in ("true", "yes", "on"):
        return True
    if low in ("false", "no", "off"):
        return False
    # remove surrounding quotes
    if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
        v = v[1:-1]
        return v
    # int / float
    try:
        if "." in v:
            return float(v)
        return int(v)
    except Exception:
        return v


def _find_next_nonempty(lines: List[str], start: int) -> tuple[int, str]:
    """Return (index, stripped_line) of next non-empty, non-comment line or (-1,'')"""
    i = start
    while i < len(lines):
        line = _strip_inline_comment(lines[i]).strip()
        if line:
            return i, line
        i += 1
    return -1, ""


def _find_open_brace(lines: List[str], start_idx: int) -> int:
    """
    Given an index where a keyword was found (e.g. 'weapon' or 'item'),
    return the index of the line that contains the opening brace '{'.
    Could be the same line (keyword {) or on a following non-empty line.
    Returns -1 if not found.
    """
    line = _strip_inline_comment(lines[start_idx]).strip()
    if "{" in line:
        return start_idx
    idx, nxt = _find_next_nonempty(lines, start_idx + 1)
    if idx != -1 and nxt.startswith("{"):
        return idx
    return -1


def _skip_block(lines: List[str], brace_idx: int) -> int:
    """
    Skip a brace block starting at brace_idx (the line that contains '{').
    Returns index of the first line after the closing brace.
    """
    i = brace_idx
    brace_count = 0
    while i < len(lines):
        content = _strip_inline_comment(lines[i])
        brace_count += content.count("{")
        brace_count -= content.count("}")
        i += 1
        if brace_count <= 0:
            break
    return i


def _parse_key_value(line: str) -> tuple[Union[str, None], Union[Any, None]]:
    """
    Parse a single line into key/value.
    Accepts:
      - key "value"
      - key value
      - key\tvalue
      - key = value
      - key: value
    Returns (key, converted_value) or (None, None) if not parsable.
    """
    line = _strip_inline_comment(line)
    if not line:
        return None, None

    # separators in preference order
    for sep in ("\t", "=", ":"):
        if sep in line:
            parts = line.split(sep, 1)
            key = parts[0].strip()
            value = parts[1].strip()
            return key, _to_native(value)

    # fallback: split on whitespace (first token = key, rest = value)
    parts = line.split(None, 1)
    if len(parts) == 2:
        key, value = parts[0].strip(), parts[1].strip()
        return key, _to_native(value)

    # single token -> treat as flag
    return parts[0].strip(), True


def _parse_block(lines: List[str], brace_idx: int) -> tuple[Dict[str, Any], int]:
    """
    Parse a general brace block starting at line brace_idx (which contains '{').
    Returns (dict, next_line_index_after_closing_brace).
    """
    data: Dict[str, Any] = {}
    i = brace_idx
    brace_count = 0
    
    while i < len(lines):
        content = _strip_inline_comment(lines[i])
        open_ct = content.count("{")
        close_ct = content.count("}")
        
        # Remove braces for parsing tokens
        stripped = content
        if open_ct or close_ct:
            stripped = stripped.replace("{", " ").replace("}", " ").strip()

        if stripped:
            # Try parse as key-value
            k, v = _parse_key_value(stripped)
            if k:
                # Handle array fields (onsurf, offsurf, muzzle, etc.)
                if k in ("onsurf", "offsurf", "muzzle", "eject", "fxname", "bolt", "useeffect", "detonateeffect", "detonateloseffect", "inaireffect"):
                    if k not in data:
                        data[k] = []
                    if isinstance(v, str) and v:
                        data[k].append(v)
                # Handle numbered array fields (onsurf1, offsurf1, etc.)
                elif re.match(r"^(onsurf|offsurf|muzzle|eject|fxname|bolt|useeffect|detonateeffect|detonateloseffect|inaireffect)\d+$", k):
                    base_key = re.match(r"^(onsurf|offsurf|muzzle|eject|fxname|bolt|useeffect|detonateeffect|detonateloseffect|inaireffect)", k).group(1)
                    if base_key not in data:
                        data[base_key] = []
                    if isinstance(v, str) and v:
                        data[base_key].append(v)
                else:
                    # If value is True and next token is '{' -> it's actually a nested block where '{' is next line
                    if v is True:
                        # lookahead to see if next non-empty line is '{'
                        next_idx, next_line = _find_next_nonempty(lines, i + 1)
                        if next_idx != -1 and next_line.startswith("{"):
                            brace_line_idx = next_idx
                            nested_obj, after_idx = _parse_block(lines, brace_line_idx)
                            data[k] = nested_obj
                            i = after_idx
                            continue
                        else:
                            data[k] = v
                    else:
                        data[k] = v

        # update brace count after processing the line
        brace_count += open_ct
        brace_count -= close_ct
        i += 1
        if brace_count <= 0:
            break

    return data, i


def parse_item_file(text: str) -> List[Dict[str, Any]]:
    """
    Parse SOF2.item-like text and return list of item dicts.
    Handles both 'weapon' and 'item' blocks.
    """
    items: List[Dict[str, Any]] = []
    lines = text.splitlines()
    i = 0
    total_lines = len(lines)

    while i < total_lines:
        raw = _strip_inline_comment(lines[i]).strip()
        if not raw:
            i += 1
            continue

        # Look for 'weapon' or 'item' keyword
        m = re.match(r"^(weapon|item)\b", raw)
        if m:
            item_type = m.group(1)
            # find the brace line
            brace_idx = _find_open_brace(lines, i)
            if brace_idx == -1:
                # malformed block: skip this line
                i += 1
                continue
            # parse the block
            parsed, after = _parse_block(lines, brace_idx)
            # add the item type to the parsed data
            parsed["_type"] = item_type
            items.append(parsed)
            i = after
            continue

        # Skip other blocks that might exist in item files
        if re.match(r"^(version|difficultyLevels|wpnEncumbranceLevels)\b", raw):
            brace_idx = _find_open_brace(lines, i)
            if brace_idx == -1:
                i += 1
            else:
                i = _skip_block(lines, brace_idx)
            continue

        i += 1

    return items


def items_to_json(items: List[Dict[str, Any]]) -> str:
    """Convert items list to JSON string."""
    import json
    return json.dumps(items, indent=2, ensure_ascii=False)
