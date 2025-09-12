import os
from typing import Any, Dict, List, Optional, Tuple
from .SoF2DataParser import parse_shader_file, parse_g2skin_to_json

log_level = os.getenv("LOG_LEVEL", "INFO")

# Shader-related caches
_cached_shader_query: Optional[str] = None
_cached_shader_items: Optional[List[Tuple[str, str, str]]] = None
_cached_shader_data: Dict[str, Dict[str, Any]] = {}

# Skin-related caches
_cached_model_name: str = ""
_cached_items: List[Tuple[str, str, str]] = []
_cached_skin_data: Dict[str, Dict[str, Any]] = {}

def reset_shader_cache():
    global _cached_shader_query, _cached_shader_items, _cached_shader_data
    _cached_shader_query = None
    _cached_shader_items = None
    _cached_shader_data = {}

def reset_skin_cache():
    global _cached_model_name, _cached_items, _cached_skin_data
    _cached_model_name = ""
    _cached_items = []
    _cached_skin_data = {}


def get_shaders_data(basepath: str, filepath: str) -> List[Tuple[str, str, str]]:
    global _cached_shader_query, _cached_shader_items, _cached_shader_data, _cached_model_name

    selected_shader = _cached_model_name if _cached_model_name else os.path.splitext(
        os.path.basename(filepath or ""))[0]

    if not selected_shader:
        return [("None", "None", "No shader selected")]

    selected_shader = selected_shader.strip()

    if _cached_shader_query == selected_shader and _cached_shader_items:
        return _cached_shader_items

    shader_dir = os.path.join(basepath or "", "shaders")
    filename = f"{selected_shader}.shader"
    file_path = os.path.join(shader_dir, filename)

    items: List[Tuple[str, str, str]] = []
    shader_data: Dict[str, Dict[str, Any]] = {}

    if os.path.isfile(file_path):
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                txt = f.read()
            parsed_defs = parse_shader_file(txt)
            shader_data.update(parsed_defs)
            for name in parsed_defs.keys():
                items.append((name, name, f"shader: {name} (from {filename})"))
        except Exception as e:
            print(f"Error parsing shader file {file_path}: {e}")
    else:
        items.append(("None", "None", f"No shader file {filename} found in {shader_dir}"))

    _cached_shader_query = selected_shader
    _cached_shader_items = items
    _cached_shader_data = shader_data

    return items


def get_shaders_folder_data(basepath: str, filepath: str) -> List[Tuple[str, str, str]]:
    global _cached_shader_query, _cached_shader_items, _cached_shader_data, _cached_model_name

    selected_shader: Optional[str] = None
    if _cached_model_name:
        selected_shader = _cached_model_name
    else:
        selected_shader = os.path.splitext(os.path.basename(filepath or ""))[0]

    if not selected_shader:
        return [("None", "None", "No shader selected")]

    selected_shader = selected_shader.strip()

    if _cached_shader_query == selected_shader and _cached_shader_items:
        return _cached_shader_items

    shader_dir = os.path.join(basepath or "", "shaders")
    items: List[Tuple[str, str, str]] = []
    shader_data: Dict[str, Dict[str, Any]] = {}

    if os.path.isdir(shader_dir):
        for fn in os.listdir(shader_dir):
            if not fn.lower().endswith(".shader"):
                continue
            path = os.path.join(shader_dir, fn)
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    txt = f.read()
                parsed_defs = parse_shader_file(txt)
                for name, parsed in parsed_defs.items():
                    shader_data[name] = parsed
                    basename = name.split("/")[-1]
                    if (name == selected_shader) or name.endswith("/" + selected_shader) or (basename == selected_shader):
                        items.append((name, name, f"shader: {name} (from {fn})"))
            except Exception as e:
                print(f"Error reading shader file {path}: {e}")

    if not items:
        items.append(("None", "None", "No shader found"))

    _cached_shader_query = selected_shader
    _cached_shader_items = items
    _cached_shader_data = shader_data

    return items


def _skin_contains_model(skin_path: str, model_name: str) -> bool:
        try:
            with open(skin_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            in_prefs = False
            in_models = False
            stack: List[str] = []
            for raw in lines:
                line = raw.strip()
                if not line or line.startswith("//") or line.startswith("#"):
                    continue
                if line.endswith("{") and not line.startswith("{"):
                    header = line.split("{", 1)[0].strip()
                    stack.append(header)
                    in_prefs = in_prefs or (header == "prefs")
                    in_models = in_models or (in_prefs and header == "models")
                    continue
                if line in ("prefs", "models", "surfaces_on", "surfaces_off", "material", "group"):
                    stack.append(line)
                    in_prefs = in_prefs or (line == "prefs")
                    in_models = in_models or (in_prefs and line == "models")
                    continue
                if line == "{":
                    continue
                if line == "}":
                    if stack:
                        last = stack.pop()
                        if last == "models":
                            in_models = False
                        elif last == "prefs":
                            in_prefs = False
                    continue
                if in_models and line.startswith(('"', "'")):
                    quoted_name = line.strip('\"\'')
                    if quoted_name == model_name:
                        return True
                elif in_models and '"' in line:
                    parts = line.split('"')
                    if len(parts) >= 2:
                        quoted_name = parts[1]
                        if quoted_name == model_name:
                            return True
            return False
        except Exception as e:
            print(f"Error checking skin {skin_path}: {e}")
            return False


def get_skins(basepath: str, filepath: str) -> Tuple[List[Tuple[str, str, str]], Dict[str, Dict[str, Any]]]:
    global _cached_model_name, _cached_items, _cached_skin_data

    model_name = os.path.splitext(os.path.basename(filepath or ""))[0]

    if model_name == _cached_model_name and _cached_items:
        if log_level == "DEBUG":
            print(f"Using cached skins for model:{model_name}, count: {len(_cached_items)}")
        return _cached_items, _cached_skin_data

    items: List[Tuple[str, str, str]] = []
    skin_data: Dict[str, Dict[str, Any]] = {}
    skins_dir = os.path.join("D:/sof2/base/", "models", "characters", "skins")
    if os.path.exists(skins_dir):
        for filename in os.listdir(skins_dir):
            if filename.lower().endswith(".g2skin"):
                skin_path = os.path.join(skins_dir, filename)
                try:
                    if _skin_contains_model(skin_path, model_name):
                        with open(skin_path, "r", encoding="utf-8", errors="ignore") as f:
                            text = f.read()
                        parsed_dict = parse_g2skin_to_json(text)
                        desc = f"Skin: {filename}, materials={len(parsed_dict.get('materials', []))}"
                        items.append((filename, filename, desc))
                        skin_data[filename] = parsed_dict
                except Exception as e:
                    print(f"Error while checking skin {skin_path}: {e}")

    if not items:
        items.append(("None", "None", "No skin found"))

    _cached_model_name = model_name
    _cached_items = items
    _cached_skin_data = skin_data
    print("Available skins:", len(items))
    return items, skin_data



