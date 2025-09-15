import os
import re
from typing import Tuple, List, Dict, Any, Optional

# ---------------- Tokenizer ----------------
_token_re = re.compile(r'"[^"]*"|\{|\}|[^\s\{\}]+')


def _tokenize(text: str) -> List[str]:
    """Return list of tokens: quoted strings, {, }, or bare tokens."""
    return _token_re.findall(text)


# ---------------- Helper: store value under key, convert to list on duplicates ----------------
def _store_value(d: Dict[str, Any], key: str, val: Any):
    """Store val under d[key]; convert to list if key repeats."""
    if key in d:
        existing = d[key]
        if isinstance(existing, list):
            existing.append(val)
        else:
            d[key] = [existing, val]
    else:
        d[key] = val


# ---------------- Recursive parser ----------------
def _parse_block(tokens: List[str], idx: int = 0) -> Tuple[Dict[str, Any], int]:
    """
    Parse tokens starting at idx inside a block (expecting tokens with no leading '{').
    Returns (obj, next_index) where next_index points to token AFTER the closing '}' (or EOF).
    Structure: dict with arbitrary keys; duplicate keys become lists.
    Anonymous inner blocks are stored under key "__anon__" as a list of their dicts.
    """
    obj: Dict[str, Any] = {}
    anon_list: List[Any] = []
    L = len(tokens)
    i = idx

    while i < L:
        tok = tokens[i]

        # closing brace -> end of this block
        if tok == "}":
            if anon_list:
                # attach anonymous blocks if any
                _store_value(
                    obj, "__anon__", anon_list if len(anon_list) > 1 else anon_list[0]
                )
            return obj, i + 1

        # opening brace without key -> anonymous block
        if tok == "{":
            inner, next_i = _parse_block(tokens, i + 1)
            anon_list.append(inner)
            i = next_i
            continue

        # normal token: treat as potential key
        key = tok.strip('"')
        i += 1

        # lookahead
        if i >= L:
            # key at EOF -> treat as flag with True
            _store_value(obj, key, True)
            break

        nxt = tokens[i]

        if nxt == "{":
            # Key { ... }  -> named block without explicit value
            inner, next_i = _parse_block(tokens, i + 1)
            # store block (as dict). If many blocks with same key -> list
            _store_value(obj, key, inner)
            i = next_i
            continue

        # nxt is not '{' -> it's a value (could be quoted or bare)
        value = nxt.strip('"')
        i += 1

        # check if after value there is a block: Key Value { ... }
        if i < L and tokens[i] == "{":
            inner, next_i = _parse_block(tokens, i + 1)
            # put value inside inner under special key "_value" to not lose it
            # if inner already had _value, we keep both by converting to list under "_value"
            if "_value" in inner:
                existing = inner["_value"]
                if isinstance(existing, list):
                    existing.append(value)
                else:
                    inner["_value"] = [existing, value]
            else:
                inner["_value"] = value
            _store_value(obj, key, inner)
            i = next_i
            continue
        else:
            # simple key:value pair
            _store_value(obj, key, value)
            continue

    # EOF reached (no closing brace)
    if anon_list:
        _store_value(obj, "__anon__", anon_list if len(anon_list) > 1 else anon_list[0])
    return obj, i


# ---------------- Public parser for one NPC text ----------------
def parse_npc_text(text: str) -> Dict[str, Any]:
    """
    Parse whole NPC file text into nested dicts/lists.
    Top-level may contain one or multiple top blocks (e.g., CharacterTemplate { ... }).
    Returns a dict mapping top-level block names to their parsed content,
    or a dict with keys/values if file contains direct key:value at top-level.
    """
    # remove windows CRs but keep newlines
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # remove trailing comments starting with // or # (but don't try to be too smart about inline quotes)
    # We'll remove //... and #... until eol
    text = re.sub(r"//.*", "", text)
    text = re.sub(r"#.*", "", text)

    tokens = _tokenize(text)
    i = 0
    L = len(tokens)
    result: Dict[str, Any] = {}

    while i < L:
        tok = tokens[i]
        if tok == "{":
            # anonymous top-level block (rare) -> parse and append under "__anon__"
            inner, next_i = _parse_block(tokens, i + 1)
            _store_value(result, "__anon__", inner)
            i = next_i
            continue

        # read top-level name
        name = tok.strip('"')
        i += 1
        # expect next token is '{' (if not, maybe it's key value at top)
        if i < L and tokens[i] == "{":
            inner, next_i = _parse_block(tokens, i + 1)
            _store_value(result, name, inner)
            i = next_i
            continue
        else:
            # top-level key value pairs (uncommon for .npc but supported)
            if i < L:
                val = tokens[i].strip('"')
                _store_value(result, name, val)
                i += 1
            else:
                _store_value(result, name, True)

    return result


# ---------------- Folder loader ----------------
def get_npcs_folder_data(basepath: str) -> Dict[str, Dict[str, Any]]:
    """
    Scan basepath/npcs and parse all .npc files.
    Returns mapping: filename -> parsed_dict
    """
    npc_dir = os.path.join(basepath, "npcs")
    results: Dict[str, Dict[str, Any]] = {}
    if not os.path.isdir(npc_dir):
        return results

    for fn in sorted(os.listdir(npc_dir)):
        if not fn.lower().endswith(".npc"):
            continue
        path = os.path.join(npc_dir, fn)
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                txt = f.read()
            parsed = parse_npc_text(txt)
            results[fn] = parsed
        except Exception as e:
            print(f"Error parsing {path}: {e}")
    return results


# ===== Shader and skin parsing helpers =====


def _find_matching_brace(text: str, start_index: int) -> Optional[int]:
    depth = 0
    i = start_index
    L = len(text)
    while i < L:
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return None


def _store_prop(props: Dict[str, Any], key: str, value: str):
    if key in props:
        existing = props[key]
        if isinstance(existing, list):
            existing.append(value)
        else:
            props[key] = [existing, value]
    else:
        props[key] = value


def _parse_block_content(block_text: str) -> Dict[str, Any]:
    res = {"tags": [], "props": {}, "blocks": []}
    i = 0
    L = len(block_text)

    def _skip_whitespace_and_comments_no_newline():
        nonlocal i
        while i < L:
            if block_text[i] in " \t\r":
                i += 1
                continue
            if block_text.startswith("//", i):
                nl = block_text.find("\n", i)
                if nl == -1:
                    i = L
                    return
                i = nl + 1
                continue
            break

    def _read_token_no_newline():
        nonlocal i
        _skip_whitespace_and_comments_no_newline()
        if i >= L:
            return None
        start = i
        while i < L and not block_text[i].isspace() and block_text[i] not in "{}":
            i += 1
        return block_text[start:i]

    while True:
        _skip_whitespace_and_comments_no_newline()
        if i >= L:
            break

        if block_text[i] == "{":
            match_end = _find_matching_brace(block_text, i)
            if match_end is None:
                break
            inner = block_text[i + 1 : match_end]
            inner_parsed = _parse_block_content(inner)
            flat: Dict[str, Any] = {}
            for t in inner_parsed.get("tags", []):
                flat[t] = True
            for k, v in inner_parsed.get("props", {}).items():
                flat[k] = v
            if inner_parsed.get("blocks"):
                flat["blocks"] = inner_parsed["blocks"]
            res["blocks"].append(flat)
            i = match_end + 1
            continue

        key = _read_token_no_newline()
        if key is None:
            break

        nl = block_text.find("\n", i)
        next_nl_idx = nl if nl != -1 else L

        j = i
        while j < next_nl_idx and block_text[j] in " \t\r":
            j += 1
        if j >= next_nl_idx:
            res["tags"].append(key)
            i = next_nl_idx + 1 if nl != -1 else L
            continue

        if block_text[j] == "{":
            match_end = _find_matching_brace(block_text, j)
            if match_end is None:
                res["tags"].append(key)
                i = j + 1
                continue
            inner = block_text[j + 1 : match_end]
            inner_parsed = _parse_block_content(inner)
            res["blocks"].append({"key": key, "value": None, "content": inner_parsed})
            i = match_end + 1
            continue

        brace_on_line = block_text.find("{", i, next_nl_idx)
        if brace_on_line != -1:
            value = block_text[i:brace_on_line].strip()
            match_end = _find_matching_brace(block_text, brace_on_line)
            if match_end is None:
                value = block_text[i:next_nl_idx].strip()
                _store_prop(res["props"], key, value)
                i = next_nl_idx + 1 if nl != -1 else L
                continue
            inner = block_text[brace_on_line + 1 : match_end]
            inner_parsed = _parse_block_content(inner)
            res["blocks"].append(
                {
                    "key": key,
                    "value": value if value != "" else None,
                    "content": inner_parsed,
                }
            )
            i = match_end + 1
            continue
        else:
            value = block_text[i:next_nl_idx].strip()
            _store_prop(res["props"], key, value)
            i = next_nl_idx + 1 if nl != -1 else L
            continue
    
    res["tags"] = [tag for tag in res["tags"] if tag != ""]

    return res


def parse_shader_file(text: str) -> Dict[str, Dict]:
    text_clean = re.sub(r"//.*", "", text)
    text_clean = re.sub(r"#.*", "", text_clean)

    results: Dict[str, Dict] = {}
    i = 0
    L = len(text_clean)

    while True:
        while i < L and text_clean[i].isspace():
            i += 1
        if i >= L:
            break

        start = i
        while i < L and not text_clean[i].isspace() and text_clean[i] != "{":
            i += 1
        if i >= L:
            break
        name = text_clean[start:i].strip()

        while i < L and text_clean[i].isspace():
            i += 1
        if i >= L or text_clean[i] != "{":
            nl = text_clean.find("\n", i)
            if nl == -1:
                break
            i = nl + 1
            continue

        brace_idx = i
        match_end = _find_matching_brace(text_clean, brace_idx)
        if match_end is None:
            break
        block_text = text_clean[brace_idx + 1 : match_end]
        parsed = _parse_block_content(block_text)
        results[name] = parsed
        i = match_end + 1

    return results


def _find_block_by_keyword(text: str, keyword: str) -> List[Tuple[str, int, int]]:
    results = []
    for m in re.finditer(r"\b" + re.escape(keyword) + r"\b", text):
        idx = m.end()
        while idx < len(text) and text[idx].isspace():
            idx += 1
        if idx >= len(text) or text[idx] != "{":
            continue
        brace_open = idx
        depth = 0
        i = idx
        while i < len(text):
            c = text[i]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    content = text[brace_open + 1 : i]
                    results.append((content, brace_open, i + 1))
                    break
            i += 1
    return results


_val_re = re.compile(r"""\s*([^\s]+)\s+(?:"([^"]+)"|'([^']+)'|([^\s]+))""")


def _parse_kv_block(block_text: str) -> Dict[str, str]:
    d: Dict[str, str] = {}
    for raw_line in block_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        line = re.sub(r"//.*$", "", line)
        line = re.sub(r"#.*$", "", line)
        if not line:
            continue
        m = _val_re.match(line)
        if m:
            key = m.group(1)
            val = m.group(2) or m.group(3) or m.group(4) or ""
            d[key] = val
    return d


def parse_g2skin_to_json(text: str) -> Dict:
    text_clean = re.sub(r"//.*", "", text)
    text_clean = re.sub(r"#.*", "", text_clean)

    result: Dict[str, Any] = {"prefs": {}, "materials": []}

    prefs_blocks = _find_block_by_keyword(text_clean, "prefs")
    if prefs_blocks:
        prefs_text, _, _ = prefs_blocks[0]
        for sub in ("models", "surfaces_on", "surfaces_off"):
            found: Dict[str, str] = {}
            subblocks = _find_block_by_keyword(prefs_text, sub)
            if subblocks:
                block_text, _, _ = subblocks[0]
                found = _parse_kv_block(block_text)
            result["prefs"][sub] = found
    else:
        result["prefs"]["models"] = {}
        result["prefs"]["surfaces_on"] = {}
        result["prefs"]["surfaces_off"] = {}

    for mat_content, _, _ in _find_block_by_keyword(text_clean, "material"):
        mat: Dict[str, Any] = {}
        name_match = re.search(
            r'name\s+(?:"([^"]+)"|\'([^\']+)\'|([^\s{]+))', mat_content
        )
        if name_match:
            mat["name"] = (
                name_match.group(1) or name_match.group(2) or name_match.group(3)
            )

        groups_list: List[Dict[str, str]] = []
        for grp_content, _, _ in _find_block_by_keyword(mat_content, "group"):
            grp_kv = _parse_kv_block(grp_content)
            groups_list.append(grp_kv)
        mat["groups"] = groups_list

        top_level_kv = _parse_kv_block(re.sub(r"group\s*{[\s\S]*?}", "", mat_content))
        top_level_kv.pop("name", None)
        if top_level_kv:
            mat["props"] = top_level_kv

        result["materials"].append(mat)

    return result
