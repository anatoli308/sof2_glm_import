# frames_parser.py
import re
import os
from pathlib import Path
from typing import Dict, Any

# --- Tokenizer (ähnlich wie beim skl_parser) ---
token_re = re.compile(r'"([^"]*)"|(\{)|(\})|([^\s\{\}]+)', re.MULTILINE)

def tokenize(text: str):
    tokens = []
    for m in token_re.finditer(text):
        if m.group(1) is not None:
            tokens.append(m.group(1))
        elif m.group(2) is not None:
            tokens.append('{')
        elif m.group(3) is not None:
            tokens.append('}')
        else:
            tokens.append(m.group(4))
    return tokens

# --- Value conversion (numbers, vectors) ---
def convert_value(s: str):
    if s == "":
        return s
    # vector like "0.000 -5.152 0.000"
    if re.match(r'^-?\d+(\.\d+)?(\s+-?\d+(\.\d+)?)+$', s):
        parts = [float(x) for x in s.split()]
        if all(float(x).is_integer() for x in parts):
            parts = [int(x) for x in parts]
        return parts
    if re.match(r'^-?\d+\.\d+$', s):
        return float(s)
    if re.match(r'^-?\d+$', s):
        return int(s)
    return s

# --- recursive block parser ---
def parse_block(tokens, i):
    assert tokens[i] == '{'
    i += 1
    result = {}
    while i < len(tokens):
        tok = tokens[i]
        if tok == '}':
            return result, i + 1
        key = tok
        # nested block: KEY { ... }
        if i + 1 < len(tokens) and tokens[i+1] == '{':
            sub, ni = parse_block(tokens, i+1)
            if key in result:
                if isinstance(result[key], list):
                    result[key].append(sub)
                else:
                    result[key] = [result[key], sub]
            else:
                result[key] = [sub]
            i = ni
            continue
        # key value pair
        if i + 1 < len(tokens):
            val = tokens[i+1]
            if val == '{':
                sub, ni = parse_block(tokens, i+1)
                if key in result:
                    if isinstance(result[key], list):
                        result[key].append(sub)
                    else:
                        result[key] = [result[key], sub]
                else:
                    result[key] = [sub]
                i = ni
            else:
                converted = convert_value(val)
                if key in result:
                    if isinstance(result[key], list):
                        result[key].append(converted)
                    else:
                        result[key] = [result[key], converted]
                else:
                    result[key] = converted
                i += 2
        else:
            i += 1
    raise ValueError("Unexpected end of tokens while parsing block")

# --- Helper: normalize parsed block for frames ---
def normalize_frames_block(block: Dict[str, Any]) -> Dict[str, Any]:
    b = dict(block)  # shallow copy
    # Convert startframe/duration/fps -> ints (convert_value already did, but ensure)
    for k in ("startframe", "duration", "fps"):
        if k in b:
            try:
                b[k] = int(b[k])
            except Exception:
                pass

    # averagevec -> list of floats (already converted by convert_value if matched)
    # Handle deltavecs: may be stored as list with a single dict
    if "deltavecs" in b:
        raw = b["deltavecs"]
        # raw may be a list of dicts or a single dict
        if isinstance(raw, list):
            # merge all inner dicts (usually just one)
            merged = {}
            for d in raw:
                if isinstance(d, dict):
                    merged.update(d)
        elif isinstance(raw, dict):
            merged = raw
        else:
            merged = {}

        # extract deltaN keys and build ordered list
        delta_items = []
        for kname, v in merged.items():
            m = re.match(r'delta(\d+)', kname, re.IGNORECASE)
            if m:
                idx = int(m.group(1))
                delta_items.append((idx, convert_value(v) if isinstance(v, str) else v))
        if delta_items:
            delta_items.sort(key=lambda x: x[0])
            deltalist = [item[1] for item in delta_items]
            b["deltavecs"] = deltalist
        else:
            # fallback: keep merged dict
            b["deltavecs"] = merged

    # Handle notetrack: may be single dict or list of dicts
    if "notetrack" in b:
        raw = b["notetrack"]
        tracks = raw if isinstance(raw, list) else [raw]
        normalized_tracks = []
        for t in tracks:
            if not isinstance(t, dict):
                continue
            nt = dict(t)
            if "frame" in nt:
                try:
                    nt["frame"] = int(nt["frame"])
                except Exception:
                    pass
            normalized_tracks.append(nt)
        b["notetrack"] = normalized_tracks

    return b

# --- Top-level frames parser ---
def parse_frames(text: str) -> Dict[str, Dict[str, Any]]:
    """
    Parse a .frames-like text and return mapping: filepath -> parsed block dict.
    """
    tokens = tokenize(text)
    i = 0
    out = {}
    while i < len(tokens):
        # skip stray braces/closing
        if tokens[i] == '}':
            i += 1
            continue
        # expecting: PATH { ... }
        if i + 1 < len(tokens) and tokens[i+1] == '{':
            path = tokens[i]
            block, ni = parse_block(tokens, i+1)
            out[path] = normalize_frames_block(block)
            i = ni
        else:
            # stray token (blank line etc.)
            i += 1
    return out

# --- Folder loader: scan basepath/skeletons for *.frames ---
def get_frames_folder_data(basepath: str) -> Dict[str, Dict[str, Any]]:
    """
    Scan <basepath>/skeletons and parse all files that end with ".frames".
    Returns mapping: filename -> parsed_dict (where parsed_dict maps filepath->block)
    """
    skeletons_dir = Path(basepath) / "skeletons"
    results = {}
    if not skeletons_dir.is_dir():
        return results

    for p in sorted(skeletons_dir.iterdir()):
        if not p.is_file():
            continue
        if not p.name.lower().endswith(".frames"):
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
            parsed = parse_frames(text)
            results[p.name] = parsed
        except Exception as e:
            print(f"Error parsing frames file {p}: {e}")
    return results