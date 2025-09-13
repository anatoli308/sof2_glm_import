# skl_parser.py
import re

token_re = re.compile(r'"([^"]*)"|(\{)|(\})|([^\s\{\}]+)', re.MULTILINE)


def tokenize(text):
    tokens = []
    for m in token_re.finditer(text):
        if m.group(1) is not None:
            tokens.append(m.group(1))
        elif m.group(2) is not None:
            tokens.append("{")
        elif m.group(3) is not None:
            tokens.append("}")
        else:
            tokens.append(m.group(4))
    return tokens


def convert_value(s):
    # leere Strings behalten
    if s == "":
        return s
    # Vektor in einem String: "1 2 3" -> [1.0, 2.0, 3.0] (oder ints falls passend)
    if re.match(r"^-?\d+(\.\d+)?(\s+-?\d+(\.\d+)?)+$", s):
        parts = [float(x) for x in s.split()]
        if all(float(x).is_integer() for x in parts):
            parts = [int(x) for x in parts]
        return parts
    # float
    if re.match(r"^-?\d+\.\d+$", s):
        return float(s)
    # int
    if re.match(r"^-?\d+$", s):
        return int(s)
    # sonst String belassen
    return s


def parse_block(tokens, i):
    # tokens[i] muss '{' sein
    assert tokens[i] == "{"
    i += 1
    result = {}
    while i < len(tokens):
        tok = tokens[i]
        if tok == "}":
            return result, i + 1
        key = tok
        # verschachtelter Block: KEY { ... }
        if i + 1 < len(tokens) and tokens[i + 1] == "{":
            sub, ni = parse_block(tokens, i + 1)
            # wenn key schon existiert, als Liste führen
            if key in result:
                if isinstance(result[key], list):
                    result[key].append(sub)
                else:
                    result[key] = [result[key], sub]
            else:
                result[key] = [sub]
            i = ni
            continue
        # normaler Key Value (value kann bare token oder quoted string sein)
        if i + 1 < len(tokens):
            val = tokens[i + 1]
            # safety: falls val '{' (nochmal) -> parse nested
            if val == "{":
                sub, ni = parse_block(tokens, i + 1)
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


def parse_skl(text):
    """
    Parse a .skl-style text and return a nested dict.
    Example:
      data = parse_skl(open("average_sleeves.skl", "r", encoding="utf-8").read())
    Top-level repeated blocks (Action, PCJ, Skelement, ...) become lists.
    """
    tokens = tokenize(text)
    i = 0
    out = {}
    while i < len(tokens):
        # skip stray closing braces
        if tokens[i] == "}":
            i += 1
            continue
        # name followed by '{' -> block
        if i + 1 < len(tokens) and tokens[i + 1] == "{":
            name = tokens[i]
            block, ni = parse_block(tokens, i + 1)
            if name in out:
                if isinstance(out[name], list):
                    out[name].append(block)
                else:
                    out[name] = [out[name], block]
            else:
                out[name] = block
            i = ni
        else:
            # stray token, skip
            i += 1
    return out
