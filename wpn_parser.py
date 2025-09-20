import json
import re
from typing import Dict, List, Any, Tuple, Union


def _strip_inline_comment(s: str) -> str:
    return re.sub(r"//.*$", "", s).strip()


def _to_native(val: str) -> Union[str, int, float, bool]:
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


def _find_next_nonempty(lines: List[str], start: int) -> Tuple[int, str]:
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
    Given an index where a keyword was found (e.g. 'weapon' or 'attack'),
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
    # find first '{' position in this line (could be other text too)
    # We'll iterate line by line and count literal '{' and '}' occurrences (safe enough)
    brace_count = 0
    while i < len(lines):
        # remove comments before counting
        content = _strip_inline_comment(lines[i])
        # count braces
        brace_count += content.count("{")
        brace_count -= content.count("}")
        i += 1
        if brace_count <= 0:
            break
    return i


def _parse_key_value(line: str) -> Tuple[Union[str, None], Union[Any, None]]:
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


def _parse_block(lines: List[str], brace_idx: int) -> Tuple[Dict[str, Any], int]:
    """
    Parse a general brace block starting at line brace_idx (which contains '{').
    Returns (dict, next_line_index_after_closing_brace).
    """
    data: Dict[str, Any] = {}
    i = brace_idx
    # initialize brace counting using counts in this and subsequent lines
    brace_count = 0
    # move into block: start counting including current line
    while i < len(lines):
        content = _strip_inline_comment(lines[i])
        # update brace counts BEFORE processing to allow lines like "{ key value }"
        open_ct = content.count("{")
        close_ct = content.count("}")
        # if this line has only a single '{' and nothing else we should skip it and continue
        # We'll still process key/value tokens on lines that contain other text.
        # Decrease logical depth only after processing this line.
        # But to avoid double-entering, we increment/decrement as we go.
        # Process content if it has non-brace tokens.
        # remove braces from the content for safe parsing of key-values on same line
        stripped = content
        if open_ct or close_ct:
            # remove braces for parsing tokens
            stripped = stripped.replace("{", " ").replace("}", " ").strip()

        if stripped:
            # Could be "attack {", "name "Knife"", or "key value"
            # detect nested blocks: if stripped is a known keyword and this line also contained a '{', treat nested.
            first_tok = stripped.split(None, 1)[0]
            if open_ct > 0 and first_tok in ("attack", "altattack", "projectile", "fireModes", "zoomFactors", "anim", "info"):
                # nested block header on same line e.g. "attack {"
                # find actual brace index (this line) and parse recursively
                nested_brace_idx = i
                nested_obj, next_i = _parse_block(lines, nested_brace_idx)
                
                # Special handling for multiple blocks that should be collected into arrays
                if first_tok in ("info", "anim"):
                    if first_tok not in data:
                        data[first_tok] = []
                    data[first_tok].append(nested_obj)
                else:
                    data[first_tok] = nested_obj
                
                i = next_i
                # continue outer loop (brace_count will be handled via counts)
                continue
            else:
                # Try parse as key-value
                k, v = _parse_key_value(stripped)
                if k:
                    # If value is True and next token is '{' -> it's actually a nested block where '{' is next line
                    if v is True:
                        # lookahead to see if next non-empty line is '{'
                        next_idx, next_line = _find_next_nonempty(lines, i + 1)
                        if next_idx != -1 and next_line.startswith("{"):
                            brace_line_idx = next_idx
                            nested_obj, after_idx = _parse_block(lines, brace_line_idx)
                            
                            # Special handling for multiple blocks that should be collected into arrays
                            if k in ("info", "anim"):
                                if k not in data:
                                    data[k] = []
                                data[k].append(nested_obj)
                            else:
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


def parse_wpn_file(text: str) -> List[Dict[str, Any]]:
    """
    Parse SOF2.wpn-like text and return list of weapon dicts.
    """
    weapons: List[Dict[str, Any]] = []
    lines = text.splitlines()
    i = 0
    total_lines = len(lines)

    while i < total_lines:
        raw = _strip_inline_comment(lines[i]).strip()
        if not raw:
            i += 1
            continue

        # Look for 'weapon' keyword (either 'weapon' or 'weapon {')
        m = re.match(r"^weapon\b", raw)
        if m:
            # find the brace line
            brace_idx = _find_open_brace(lines, i)
            if brace_idx == -1:
                # malformed block: skip this line
                i += 1
                continue
            # parse the block
            parsed, after = _parse_block(lines, brace_idx)
            # parsed is the content of the weapon block
            weapons.append(parsed)
            i = after
            continue

        # Skip big non-weapon blocks: detect keywords and skip properly
        if re.match(r"^(version|difficultyLevels|wpnEncumbranceLevels)\b", raw):
            brace_idx = _find_open_brace(lines, i)
            if brace_idx == -1:
                i += 1
            else:
                i = _skip_block(lines, brace_idx)
            continue

        i += 1

    return weapons


def weapons_to_json(weapons: List[Dict[str, Any]]) -> str:
    return json.dumps(weapons, indent=2, ensure_ascii=False)


def parse_inview_file(text: str) -> List[Dict[str, Any]]:
    """
    Parse SOF2.inview-like text and return list of weapon inview dicts.
    Similar to parse_wpn_file but looks for 'weapon' blocks in inview format.
    """
    weapons: List[Dict[str, Any]] = []
    lines = text.splitlines()
    i = 0
    total_lines = len(lines)

    while i < total_lines:
        raw = _strip_inline_comment(lines[i]).strip()
        if not raw:
            i += 1
            continue

        # Look for 'weapon' keyword (either 'weapon' or 'weapon {')
        m = re.match(r"^weapon\b", raw)
        if m:
            # find the brace line
            brace_idx = _find_open_brace(lines, i)
            if brace_idx == -1:
                # malformed block: skip this line
                i += 1
                continue
            # parse the block
            parsed, after = _parse_block(lines, brace_idx)
            # parsed is the content of the weapon block
            weapons.append(parsed)
            i = after
            continue

        # Skip other blocks that might exist in inview files
        if re.match(r"^(version|difficultyLevels|wpnEncumbranceLevels)\b", raw):
            brace_idx = _find_open_brace(lines, i)
            if brace_idx == -1:
                i += 1
            else:
                i = _skip_block(lines, brace_idx)
            continue

        i += 1

    return weapons


def inview_to_json(inview_weapons: List[Dict[str, Any]]) -> str:
    return json.dumps(inview_weapons, indent=2, ensure_ascii=False)