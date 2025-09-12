# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

from .mod_reload import reload_modules
reload_modules(locals(), __package__, ["JAG2Scene", "JAG2GLA", "JAFilesystem"], [".JAG2Constants"])  # nopep8

import os
import re
import json

import bpy
from typing import Tuple, List, Dict, Optional, cast, Set, Any
from . import JAG2Scene
from . import JAG2GLA
from . import JAFilesystem
from .JAG2Constants import SkeletonFixes

# Cache-Variablen
_cached_shader_query = None        # zuletzt gesuchte shader-name (query)
_cached_shader_items = None        # enum-kompatible items list
_cached_shader_data: Dict[str, Dict[str, Any]] = {}  # name -> parsed dict

def _find_matching_brace(text: str, start_index: int) -> Optional[int]:
    depth = 0
    i = start_index
    L = len(text)
    while i < L:
        c = text[i]
        if c == '{':
            depth += 1
        elif c == '}':
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
    """
    Parse content inside one { ... } block.
    Returns:
      {
        "tags": [...],
        "props": {k: v},
        "blocks": [ block_or_flat_dict, ... ]
      }
    - anonymous inner blocks are appended as flat dicts of their props/tags:
        blocks: [ {"map": "...", "rgbGen": "..."}, ... ]
    - named blocks are appended as dicts: {"key": key, "value": value_or_None, "content": {tags,props,blocks}}
    """
    res = {"tags": [], "props": {}, "blocks": []}
    i = 0
    L = len(block_text)

    def _skip_whitespace_and_comments_no_newline():
        """skip spaces and tabs and comments, but NOT newlines"""
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
        """Read a token until whitespace or brace but do not skip newlines beforehand"""
        nonlocal i
        _skip_whitespace_and_comments_no_newline()
        if i >= L:
            return None
        # token ends at whitespace or '{' or '}'
        start = i
        while i < L and not block_text[i].isspace() and block_text[i] not in "{}":
            i += 1
        return block_text[start:i]

    while True:
        _skip_whitespace_and_comments_no_newline()
        if i >= L:
            break

        # anonymous block starting with '{'
        if block_text[i] == '{':
            match_end = _find_matching_brace(block_text, i)
            if match_end is None:
                break
            inner = block_text[i+1:match_end]
            inner_parsed = _parse_block_content(inner)
            # flatten anonymous block: build flat dict from props and tags
            flat = {}
            # tags -> put them as keys with True or as list? we put tags as keys with True.
            for t in inner_parsed.get("tags", []):
                flat[t] = True
            for k, v in inner_parsed.get("props", {}).items():
                flat[k] = v
            # if inner blocks exist, keep them nested under 'blocks'
            if inner_parsed.get("blocks"):
                flat["blocks"] = inner_parsed["blocks"]
            res["blocks"].append(flat)
            i = match_end + 1
            continue

        # read a key token (do NOT consume following newline here)
        key = _read_token_no_newline()
        if key is None:
            break

        # Now decide: is this a standalone tag (token on its own line) or a key/value?
        # Find next newline position
        nl = block_text.find('\n', i)
        next_nl_idx = nl if nl != -1 else L

        # find next non-space character before that newline
        j = i
        while j < next_nl_idx and block_text[j] in " \t\r":
            j += 1
        # if newline comes immediately (j == next_nl_idx), it's a tag
        if j >= next_nl_idx:
            # tag (token stands alone on its line)
            res["tags"].append(key)
            # advance i to after newline (if exists)
            i = next_nl_idx + 1 if nl != -1 else L
            continue

        # else, there is something else on same line after key:
        # it could be either a value or a brace starting a nested block
        if block_text[j] == '{':
            # key { ... }  (named block without value)
            match_end = _find_matching_brace(block_text, j)
            if match_end is None:
                # malformed -> treat key as tag
                res["tags"].append(key)
                i = j + 1
                continue
            inner = block_text[j+1:match_end]
            inner_parsed = _parse_block_content(inner)
            res["blocks"].append({
                "key": key,
                "value": None,
                "content": inner_parsed
            })
            i = match_end + 1
            continue

        # otherwise, there is a value on same line; read until brace or newline
        # check if an opening brace appears later on same line
        brace_on_line = block_text.find('{', i, next_nl_idx)
        if brace_on_line != -1:
            # value is substring i..brace_on_line
            value = block_text[i:brace_on_line].strip()
            # then block from brace_on_line..matching
            match_end = _find_matching_brace(block_text, brace_on_line)
            if match_end is None:
                # malformed: store as prop until newline
                value = block_text[i:next_nl_idx].strip()
                _store_prop(res["props"], key, value)
                i = next_nl_idx + 1 if nl != -1 else L
                continue
            inner = block_text[brace_on_line+1:match_end]
            inner_parsed = _parse_block_content(inner)
            # store as named block with value
            res["blocks"].append({
                "key": key,
                "value": value if value != "" else None,
                "content": inner_parsed
            })
            i = match_end + 1
            continue
        else:
            # no brace on same line -> value ends at newline
            value = block_text[i:next_nl_idx].strip()
            _store_prop(res["props"], key, value)
            i = next_nl_idx + 1 if nl != -1 else L
            continue

    return res

def parse_shader_file(text: str) -> Dict[str, Dict]:
    """
    Parse whole shader file and return dict: shader_name -> parsed dict
    Each parsed dict: {tags, props, blocks}
    """
    # remove line comments '//' and '#' (simple)
    text_clean = re.sub(r'//.*', '', text)
    text_clean = re.sub(r'#.*', '', text_clean)

    results: Dict[str, Dict] = {}
    i = 0
    L = len(text_clean)

    while True:
        # skip whitespace
        while i < L and text_clean[i].isspace():
            i += 1
        if i >= L:
            break

        # read shader name (until whitespace or '{')
        start = i
        while i < L and not text_clean[i].isspace() and text_clean[i] != '{':
            i += 1
        if i >= L:
            break
        name = text_clean[start:i].strip()

        # skip whitespace until '{'
        while i < L and text_clean[i].isspace():
            i += 1
        if i >= L or text_clean[i] != '{':
            # no block start -> skip line
            nl = text_clean.find('\n', i)
            if nl == -1:
                break
            i = nl + 1
            continue

        brace_idx = i
        match_end = _find_matching_brace(text_clean, brace_idx)
        if match_end is None:
            break
        block_text = text_clean[brace_idx+1:match_end]
        parsed = _parse_block_content(block_text)
        results[name] = parsed
        i = match_end + 1

    return results

# module-level cache for skins (operators in Blender often block new instance attributes)
_cached_model_name = ""
_cached_items = []    
_cached_skin_data = {}   # filename -> parsed_dict

def GetPaths(basepath, filepath) -> Tuple[str, str]:
    if basepath == "":
        basepath, filepath = JAFilesystem.SplitPrefix(filepath)
        filepath = JAFilesystem.RemoveExtension(filepath)
    else:
        filepath = JAFilesystem.RelPathNoExt(filepath, basepath)
    return basepath, filepath

def _skin_contains_model(skin_path: str, model_name: str) -> bool:
        """Check if skin file contains the model in its prefs"""
        try:
            with open(skin_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            in_prefs = False
            in_models = False
            stack = []
            
            for raw in lines:
                line = raw.strip()
                if not line or line.startswith("//") or line.startswith("#"):
                    continue
                
                # Header + { auf einer Zeile
                if line.endswith("{") and not line.startswith("{"):
                    header = line.split("{", 1)[0].strip()
                    stack.append(header)
                    in_prefs = in_prefs or (header == "prefs")
                    in_models = in_models or (in_prefs and header == "models")
                    continue
                
                # Header ohne { → kommt in nächster Zeile
                if line in ("prefs", "models", "surfaces_on", "surfaces_off", "material", "group"):
                    stack.append(line)
                    in_prefs = in_prefs or (line == "prefs")
                    in_models = in_models or (in_prefs and line == "models")
                    continue
                
                # Nur Klammer öffnen
                if line == "{":
                    continue
                
                # Blockende
                if line == "}":
                    if stack:
                        last = stack.pop()
                        if last == "models":
                            in_models = False
                        elif last == "prefs":
                            in_prefs = False
                    continue
                
                # Model name in models block
                if in_models and line.startswith(('"', "'")):
                    # Extract model name from quoted string
                    quoted_name = line.strip('"\'')
                    if quoted_name == model_name:
                        return True
                elif in_models and '"' in line:
                    # Format: 1	"model_name"
                    parts = line.split('"')
                    if len(parts) >= 2:
                        quoted_name = parts[1]
                        if quoted_name == model_name:
                            return True
            
            return False
            
        except Exception as e:
            print(f"Error checking skin {skin_path}: {e}")
            return False

# Hilfsfkt: finde Block-Inhalt nach einem Keyword, unterstützt geschachtelte { ... }.
def _find_block_by_keyword(text: str, keyword: str) -> List[Tuple[str, int, int]]:
    """
    Returns list of tuples (block_content, start_index, end_index) for each occurrence of keyword { ... }.
    """
    results = []
    for m in re.finditer(r'\b' + re.escape(keyword) + r'\b', text):
        # Suche erste öffnende Klammer nach dem Match
        idx = m.end()
        # skip whitespace to find '{'
        while idx < len(text) and text[idx].isspace():
            idx += 1
        if idx >= len(text) or text[idx] != '{':
            continue
        # now find matching brace
        brace_open = idx
        depth = 0
        i = idx
        while i < len(text):
            c = text[i]
            if c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    # content between brace_open+1 .. i-1
                    content = text[brace_open+1:i]
                    results.append((content, brace_open, i+1))
                    break
            i += 1
    return results

# Hilfsfkt: parse lines mit key value (value kann "quoted" oder unquoted sein)
_val_re = re.compile(r'''\s*([^\s]+)\s+(?:"([^"]+)"|'([^']+)'|([^\s]+))''')

def _parse_kv_block(block_text: str) -> Dict[str, str]:
    """
    Parse key value lines inside a simple block (no nested braces expected here).
    Returns dict key->value (strings).
    """
    d: Dict[str, str] = {}
    for raw_line in block_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        # remove inline comments starting with // or # (simple)
        line = re.sub(r'//.*$', '', line)
        line = re.sub(r'#.*$', '', line)
        if not line:
            continue
        m = _val_re.match(line)
        if m:
            key = m.group(1)
            val = m.group(2) or m.group(3) or m.group(4) or ""
            d[key] = val
    return d

def parse_g2skin_to_json(text: str) -> Dict:
    # Entferne Kommentarzeilen (grob)
    text_clean = re.sub(r'//.*', '', text)
    text_clean = re.sub(r'#.*', '', text_clean)

    result = {"prefs": {}, "materials": []}

    # -------- prefs block --------
    prefs_blocks = _find_block_by_keyword(text_clean, "prefs")
    if prefs_blocks:
        prefs_text, _, _ = prefs_blocks[0]
        # parse subblocks models, surfaces_on, surfaces_off
        for sub in ("models", "surfaces_on", "surfaces_off"):
            found = {}
            subblocks = _find_block_by_keyword(prefs_text, sub)
            if subblocks:
                block_text, _, _ = subblocks[0]
                found = _parse_kv_block(block_text)
            result["prefs"][sub] = found
    else:
        result["prefs"]["models"] = {}
        result["prefs"]["surfaces_on"] = {}
        result["prefs"]["surfaces_off"] = {}

    # -------- material blocks (kann mehrere geben) --------
    for mat_content, _, _ in _find_block_by_keyword(text_clean, "material"):
        mat: Dict = {}
        # name kann innerhalb des material-blocks stehen
        name_match = re.search(r'name\s+(?:"([^"]+)"|\'([^\']+)\'|([^\s{]+))', mat_content)
        if name_match:
            mat["name"] = name_match.group(1) or name_match.group(2) or name_match.group(3)

        # finde alle group { ... } Blöcke innerhalb des material-blocks
        groups_list: List[Dict[str, str]] = []
        for grp_content, _, _ in _find_block_by_keyword(mat_content, "group"):
            grp_kv = _parse_kv_block(grp_content)
            groups_list.append(grp_kv)
        mat["groups"] = groups_list

        # optional: auch top-level keys in material (falls vorhanden)
        # z.B. material { somekey value ... }
        # Wir können zusätzlich alle simple kv pairs extrahieren, die nicht in groups waren:
        top_level_kv = _parse_kv_block(re.sub(r'group\s*{[\s\S]*?}', '', mat_content))
        # Entferne 'name' falls doppelt
        top_level_kv.pop('name', None)
        if top_level_kv:
            mat["props"] = top_level_kv

        result["materials"].append(mat)

    return result

class GLMImport(bpy.types.Operator):
    '''Import GLM Operator.'''
    bl_idname = "import_scene.glm"
    bl_label = "Import SoF2 Ghoul 2 Model (.glm)"
    bl_description = "Imports a Ghoul 2 model (.glm), looking up the skeleton (and optionally the animation) from the referenced (or optionally a different) .gla file."
    # register is a must-have when using WindowManager.invoke_props_popup
    bl_options = {'REGISTER', 'UNDO'}
    
    # erwartet: parse_shader_file(text: str) -> Dict[name, parsed_dict]
    # und modul-level caches:
    # _cached_model_name, _cached_shader_query, _cached_shader_items, _cached_shader_data

    def _get_shaders(self, context=None):
        """
        Lade und parse genau eine Shader-Datei:
        <basepath>/shaders/{_cached_model_name}.shader

        Liefert eine Enum-kompatible Liste von (name, name, description)
        für alle Shader-Definitionen, die in dieser Datei vorkommen.
        """
        global _cached_shader_query, _cached_shader_items, _cached_shader_data, _cached_model_name

        # bestimme query-name (primär _cached_model_name, fallback self.filepath)
        selected_shader = _cached_model_name if _cached_model_name else os.path.splitext(
            os.path.basename(self.filepath if hasattr(self, "filepath") else ""))[0]

        if not selected_shader:
            return [("None", "None", "No shader selected")]

        selected_shader = selected_shader.strip()

        # cache hit?
        if _cached_shader_query == selected_shader and _cached_shader_items:
            return _cached_shader_items

        # dateipfad (Ordner "shaders" wie in deiner letzten Version)
        shader_dir = os.path.join(self.basepath if hasattr(self, "basepath") else "", "shaders")
        filename = f"{selected_shader}.shader"
        file_path = os.path.join(shader_dir, filename)

        items = []
        shader_data = {}

        if os.path.isfile(file_path):
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    txt = f.read()
                parsed_defs = parse_shader_file(txt)  # dict name->parsed
                shader_data.update(parsed_defs)
                for name in parsed_defs.keys():
                    items.append((name, name, f"shader: {name} (from {filename})"))
            except Exception as e:
                print(f"Error parsing shader file {file_path}: {e}")
        else:
            # fallback: keine Datei gefunden
            items.append(("None", "None", f"No shader file {filename} found in {shader_dir}"))

        # cache results
        _cached_shader_query = selected_shader
        _cached_shader_items = items
        _cached_shader_data = shader_data

        return items
    
    #UNUSED FOR NOW - will keep it for later use if needed to parse all shader files
    def _get_shaders_folder(self, context=None):
        """
        Suche Shader-Definitionen im <basepath>/shader, basierend auf dem aktuellen
        Modell-Namen, der in _cached_model_name gespeichert ist (Fallback: self.filepath).
        Liefert Enum-kompatible items und cached die geparsten Shader-Daten in
        _cached_shader_data (name -> parsed dict).
        """
        global _cached_shader_query, _cached_shader_items, _cached_shader_data, _cached_model_name

        # 1) Bestimme den "selected shader" query: primär aus _cached_model_name
        selected_shader = None
        if _cached_model_name:
            selected_shader = _cached_model_name
        else:
            # Fallback: model name aus self.filepath ableiten (wie bei _get_skins)
            selected_shader = os.path.splitext(os.path.basename(self.filepath if hasattr(self, "filepath") else ""))[0]

        if not selected_shader:
            return [("None", "None", "No shader selected")]

        selected_shader = selected_shader.strip()

        # 2) Cache-Hit?
        if _cached_shader_query == selected_shader and _cached_shader_items:
            return _cached_shader_items

        # 3) Suche shader-files im shader-Ordner
        shader_dir = os.path.join(self.basepath if hasattr(self, "basepath") else "", "shaders")
        items = []
        shader_data = {}

        if os.path.isdir(shader_dir):
            for fn in os.listdir(shader_dir):
                if not fn.lower().endswith(".shader"):
                    continue
                path = os.path.join(shader_dir, fn)
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        txt = f.read()
                    parsed_defs = parse_shader_file(txt)  # erwartet: dict name->parsed
                    # sammle alle definitions
                    for name, parsed in parsed_defs.items():
                        shader_data[name] = parsed
                        # tolerant match:
                        # - exakt gleich
                        # - name endswith selected_shader
                        # - oder basename(name) == selected_shader
                        basename = name.split("/")[-1]
                        if (name == selected_shader) or name.endswith("/" + selected_shader) or (basename == selected_shader):
                            items.append((name, name, f"shader: {name} (from {fn})"))
                except Exception as e:
                    print(f"Error reading shader file {path}: {e}")

        if not items:
            items.append(("None", "None", "No shader found"))

        # 4) cache results
        _cached_shader_query = selected_shader
        _cached_shader_items = items
        _cached_shader_data = shader_data

        return items

    
    def _get_skins(self, context=None):
        global _cached_model_name, _cached_items, _cached_skin_data

        model_name = os.path.splitext(os.path.basename(self.filepath if hasattr(self, "filepath") else ""))[0]

        if model_name == _cached_model_name and _cached_items:
            print(f"Using cached skins for model:{model_name}, count: {len(_cached_items)}")
            return _cached_items

        items = []
        skin_data = {}
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

                            # Enum-kompatibel: description nur kurz
                            desc = f"Skin: {filename}, materials={len(parsed_dict.get('materials', []))}"
                            items.append((filename, filename, desc))

                            # Daten separat ablegen
                            skin_data[filename] = parsed_dict

                    except Exception as e:
                        print(f"Error while checking skin {skin_path}: {e}")

        if not items:
            items.append(("None", "None", "No skin found"))

        _cached_model_name = model_name
        _cached_items = items
        _cached_skin_data = skin_data
        print("Available skins:", len(items))
        return items

    # properties
    filepath: bpy.props.StringProperty(
        name="File Path",
        description="The .glm file to import",
        default="",
        subtype='FILE_PATH'
    )  # pyright: ignore [reportInvalidTypeForm]
    skin: bpy.props.EnumProperty(
        name="Skin", description="Available skins for this model", 
        items=_get_skins)  # pyright: ignore [reportInvalidTypeForm]
    basepath: bpy.props.StringProperty(
        name="Base Path", description="The base folder relative to which paths should be interpreted. Leave empty to let the importer guess (needs /GameData/ in filepath).", default="D:/sof2/base/")  # pyright: ignore [reportInvalidTypeForm]
    glaOverride: bpy.props.StringProperty(
        name=".gla override", description="Gla file to use, relative to base. Leave empty to use the one referenced in the file.", maxlen=64, default="")  # pyright: ignore [reportInvalidTypeForm]
    scale: bpy.props.FloatProperty(
        name="Scale", description="Scale to apply to the imported model.", default=10, min=0, max=1000, subtype='PERCENTAGE')  # pyright: ignore [reportInvalidTypeForm]
    skeletonFixes: bpy.props.EnumProperty(name="skeleton changes", description="You can select a preset for automatic skeleton changes which result in a nicer imported skeleton.", default='NONE', items=[
        (SkeletonFixes.NONE.value, "None", "Don't change the skeleton in any way.", 0),
        (SkeletonFixes.JKA_HUMANOID.value, "Jedi Academy _humanoid",
         "Fixes for the default humanoid Jedi Academy skeleton", 1)
    ])  # pyright: ignore [reportInvalidTypeForm, reportArgumentType]
    loadAnimations: bpy.props.EnumProperty(name="animations", description="Whether to import all animations, some animations or only a range from the .gla. (Importing huge animations takes forever.)", default='NONE', items=[
        (JAG2GLA.AnimationLoadMode.NONE.value, "None", "Don't import animations.", 0),
        (JAG2GLA.AnimationLoadMode.ALL.value, "All", "Import all animations", 1),
        (JAG2GLA.AnimationLoadMode.RANGE.value, "Range", "Import a certain range of frames", 2)
    ])  # pyright: ignore [reportInvalidTypeForm, reportArgumentType]
    startFrame: bpy.props.IntProperty(
        name="Start frame", description="If only a range of frames of the animation is to be imported, this is the first.", min=0)  # pyright: ignore [reportInvalidTypeForm]
    numFrames: bpy.props.IntProperty(
        name="number of frames", description="If only a range of frames of the animation is to be imported, this is the total number of frames to import", min=1)  # pyright: ignore [reportInvalidTypeForm]

    def execute(self, context):
         # Validate selected skin
        # the EnumProperty usually returns an identifier string like "None" or "myskin.g2skin"
        selected_skin = self.skin if isinstance(self.skin, str) else (self.skin[0] if getattr(self.skin, "__len__", None) else "")
        if not selected_skin or selected_skin == "None":
            self.report({'ERROR'}, "Kein gültiger Skin ausgewählt. Wähle zuerst einen Skin aus.")
            return {'CANCELLED'}
        
        #try to get available shaders for the glm name in base/shaders folder
        #available_shaders = self._get_shaders()
        #if available_skins:
        #    self.skin = selected_skin  # default auf ersten Skin setzen
        
        selected_skin_data = _cached_skin_data.get(selected_skin)
        if not selected_skin_data:
            self.report({'ERROR'}, f"Skin data for {selected_skin} not found or could not be parsed.")
            return {'CANCELLED'}
        
        print("\n== GLM Import ==\n")
        # initialize paths
        basepath, filepath = GetPaths(self.basepath, self.filepath)
        if self.basepath != "" and JAFilesystem.RemoveExtension(self.filepath) == filepath:
            self.report({'ERROR'}, "Invalid Base Path")
            return {'FINISHED'}
        # de-percentagionise scale
        scale = self.scale / 100
        # load GLM
        scene = JAG2Scene.Scene(basepath)
        success, message = scene.loadFromGLM(filepath, selected_skin_data)
        if not success:
            self.report({'ERROR'}, message)
            return {'FINISHED'}
        # load GLA - has to be done in any case since that's where the skeleton is stored
        if self.glaOverride == "":
            glafile = scene.getRequestedGLA()
        else:
            glafile = cast(str, self.glaOverride)
        loadAnimations = JAG2GLA.AnimationLoadMode[self.loadAnimations]
        success, message = scene.loadFromGLA(
            glafile, loadAnimations, cast(int, self.startFrame), cast(int, self.numFrames))
        if not success:
            self.report({'ERROR'}, message)
            return {'FINISHED'}

        guessTextures = True # Anatoli - True for now dont need that in SoF2 idk what it does
        success, message = scene.saveToBlender(
            scale, selected_skin_data, guessTextures, loadAnimations != JAG2GLA.AnimationLoadMode.NONE, SkeletonFixes[self.skeletonFixes])
        if not success:
            self.report({'ERROR'}, message)
        return {'FINISHED'}
            
    def invoke(self, context, event):  # pyright: ignore [reportIncompatibleMethodOverride]
        # show file selection window
        wm = context.window_manager
        wm.fileselect_add(self)
        return {'RUNNING_MODAL'}


class GLAImport(bpy.types.Operator):
    '''Import GLA Operator.'''
    bl_idname = "import_scene.gla"
    bl_label = "Import SoF2 Ghoul 2 Skeleton (.gla)"
    bl_description = "Imports a Ghoul 2 skeleton (.gla) and optionally the animation."
    bl_options = {'REGISTER', 'UNDO'}

    filename_ext = "*.gla"  # I believe this limits the shown files.

    # properties
    filepath: bpy.props.StringProperty(
        name="File Path", description="The .gla file to import", maxlen=1024, default="", subtype='FILE_PATH')  # pyright: ignore [reportInvalidTypeForm]
    basepath: bpy.props.StringProperty(
        name="Base Path", description="The base folder relative to which paths should be interpreted. Leave empty to let the importer guess (needs /GameData/ in filepath).", default="D:/sof2/base/")  # pyright: ignore [reportInvalidTypeForm]
    scale: bpy.props.FloatProperty(
        name="Scale", description="Scale to apply to the imported model.", default=10, min=0, max=1000, subtype='PERCENTAGE')  # pyright: ignore [reportInvalidTypeForm]
    skeletonFixes: bpy.props.EnumProperty(name="skeleton changes", description="You can select a preset for automatic skeleton changes which result in a nicer imported skeleton.", default='NONE', items=[
        (SkeletonFixes.NONE.value, "None", "Don't change the skeleton in any way.", 0),
        (SkeletonFixes.JKA_HUMANOID.value, "Jedi Academy _humanoid",
         "Fixes for the default humanoid Jedi Academy skeleton", 1)
    ])  # pyright: ignore [reportInvalidTypeForm, reportArgumentType]
    loadAnimations: bpy.props.EnumProperty(name="animations", description="Whether to import all animations, some animations or only a range from the .gla. (Importing huge animations takes forever.)", default='NONE', items=[
        (JAG2GLA.AnimationLoadMode.NONE.value, "None", "Don't import animations.", 0),
        (JAG2GLA.AnimationLoadMode.ALL.value, "All", "Import all animations", 1),
        (JAG2GLA.AnimationLoadMode.RANGE.value, "Range", "Import a certain range of frames", 2)
    ])  # pyright: ignore [reportInvalidTypeForm, reportArgumentType]
    startFrame: bpy.props.IntProperty(
        name="Start frame", description="If only a range of frames of the animation is to be imported, this is the first.", min=0)  # pyright: ignore [reportInvalidTypeForm]
    numFrames: bpy.props.IntProperty(
        name="number of frames", description="If only a range of frames of the animation is to be imported, this is the total number of frames to import", min=1)  # pyright: ignore [reportInvalidTypeForm]

    def execute(self, context):
        print("\n== GLA Import ==\n")
        # de-percentagionise scale
        scale = self.scale / 100
        # initialize paths
        basepath, filepath = GetPaths(self.basepath, self.filepath)
        if self.basepath != "" and JAFilesystem.RemoveExtension(self.filepath) == filepath:
            self.report({'ERROR'}, "Invalid Base Path")
            return {'FINISHED'}
        # load GLA
        scene = JAG2Scene.Scene(basepath)
        loadAnimations = JAG2GLA.AnimationLoadMode[self.loadAnimations]
        success, message = scene.loadFromGLA(
            filepath, loadAnimations, self.startFrame, self.numFrames)
        if not success:
            self.report({'ERROR'}, message)
            return {'FINISHED'}
        # output to blender
        success, message = scene.saveToBlender(
            scale, "", False, loadAnimations != JAG2GLA.AnimationLoadMode.NONE, SkeletonFixes[self.skeletonFixes])
        if not success:
            self.report({'ERROR'}, message)
        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        wm.fileselect_add(self)
        return {'RUNNING_MODAL'}


class GLMExport(bpy.types.Operator):
    '''Export GLM Operator.'''
    bl_idname = "export_scene.glm"
    bl_label = "Export SoF2 Ghoul 2 Model (.glm)"
    bl_description = "Exports a Ghoul 2 model (.glm)"
    bl_options = {'REGISTER', 'UNDO'}

    filename_ext = "*.glm"

    # properties
    filepath: bpy.props.StringProperty(
        name="File Path", description="The filename to export to", maxlen=1024, default="", subtype='FILE_PATH')  # pyright: ignore [reportInvalidTypeForm]
    basepath: bpy.props.StringProperty(
        name="Base Path", description="The base folder relative to which paths should be interpreted. Leave empty to let the exporter guess (needs /GameData/ in filepath).", default="")  # pyright: ignore [reportInvalidTypeForm]
    gla: bpy.props.StringProperty(
        name=".gla name", description="Name of the skeleton this model uses (must exist!)", default="models/players/_humanoid/_humanoid")  # pyright: ignore [reportInvalidTypeForm]

    def execute(self, context):
        print("\n== GLM Export ==\n")
        # initialize paths
        basepath, filepath = GetPaths(self.basepath, self.filepath)
        if self.basepath != "" and JAFilesystem.RemoveExtension(self.filepath) == filepath:
            self.report({'ERROR'}, "Invalid Base Path")
            return {'FINISHED'}
        # try to load from Blender's data to my intermediate format
        scene = JAG2Scene.Scene(basepath)
        success, message = scene.loadModelFromBlender(filepath, self.gla)
        if not success:
            self.report({'ERROR'}, message)
            return {'FINISHED'}
        # try to save
        success, message = scene.saveToGLM(filepath)
        if not success:
            self.report({'ERROR'}, message)
        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        wm.fileselect_add(self)
        return {'RUNNING_MODAL'}


class GLAExport(bpy.types.Operator):
    '''Export GLA Operator.'''
    bl_idname = "export_scene.gla"
    bl_label = "Export SoF2 Ghoul 2 Skeleton & Animation (.gla)"
    bl_description = "Exports a Ghoul 2 Skeleton and its animations (.gla)"
    bl_options = {'REGISTER', 'UNDO'}

    filename_ext = "*.gla"

    # properties
    filepath: bpy.props.StringProperty(
        name="File Path", description="The filename to export to", maxlen=1024, default="", subtype='FILE_PATH')  # pyright: ignore [reportInvalidTypeForm]
    basepath: bpy.props.StringProperty(
        name="Base Path", description="The base folder relative to which paths should be interpreted. Leave empty to let the exporter guess (needs /GameData/ in filepath).", default="")  # pyright: ignore [reportInvalidTypeForm]
    glapath: bpy.props.StringProperty(
        name="gla name", description="The relative path of this gla. Leave empty to let the exporter guess (needs /GameData/ in filepath).", maxlen=64, default="")  # pyright: ignore [reportInvalidTypeForm]
    glareference: bpy.props.StringProperty(
        name="gla reference", description="Copies the bone indices from this skeleton, if any (e.g. for new animations for existing skeleton; path relative to the Base Path)", maxlen=64, default="")  # pyright: ignore [reportInvalidTypeForm]

    def execute(self, context):
        print("\n== GLA Export ==\n")
        # initialize paths
        basepath, filepath = GetPaths(self.basepath, self.filepath)
        print("Basepath: {}\tFilename: {}".format(
            basepath, filepath))  # todo delete!!!!!
        glapath = filepath
        if self.glapath != "":
            glapath = self.glapath
        glapath = glapath.replace("\\", "/")
        if self.basepath != "" and JAFilesystem.RemoveExtension(self.filepath) == filepath:
            self.report({'ERROR'}, "Invalid Base Path")
            return {'FINISHED'}
        # try to load from Blender's data to my intermediate format
        scene = JAG2Scene.Scene(basepath)
        success, message = scene.loadSkeletonFromBlender(
            glapath, self.glareference)
        if not success:
            self.report({'ERROR'}, message)
            return {'FINISHED'}
        # try to save
        success, message = scene.saveToGLA(filepath)
        if not success:
            self.report({'ERROR'}, message)
        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        wm.fileselect_add(self)
        return {'RUNNING_MODAL'}


class ObjectAddG2Properties(bpy.types.Operator):
    bl_idname = "object.add_g2_properties"
    bl_label = "Add G2 properties"
    bl_description = "Adds Ghoul 2 properties"

    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type in ['MESH', 'ARMATURE'] or False

    def execute(self, context):
        obj = context.active_object
        if obj.type == 'MESH':
            # don't overwrite those that already exist
            if not "g2_prop_off" in obj:
                obj.g2_prop_off = False  # pyright: ignore [reportAttributeAccessIssue]
            if not "g2_prop_tag" in obj:
                obj.g2_prop_tag = False  # pyright: ignore [reportAttributeAccessIssue]
            if not "g2_prop_name" in obj:
                obj.g2_prop_name = ""  # pyright: ignore [reportAttributeAccessIssue]
            if not "g2_prop_shader" in obj:
                obj.g2_prop_shader = ""  # pyright: ignore [reportAttributeAccessIssue]
        else:
            assert (obj.type == 'ARMATURE')
            if not "g2_prop_scale" in obj:
                obj.g2_prop_scale = 100  # pyright: ignore [reportAttributeAccessIssue]
        return {'FINISHED'}


class ObjectRemoveG2Properties(bpy.types.Operator):
    bl_idname = "object.remove_g2_properties"
    bl_label = "Remove G2 properties"
    bl_description = "Removes Ghoul 2 properties"

    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type in ['MESH', 'ARMATURE'] or False

    def execute(self, context):
        obj = context.active_object
        if obj.type == 'MESH':
            bpy.types.Object.__delitem__(obj, "g2_prop_off")
            bpy.types.Object.__delitem__(obj, "g2_prop_tag")
            bpy.types.Object.__delitem__(obj, "g2_prop_name")
            bpy.types.Object.__delitem__(obj, "g2_prop_shader")
        else:
            assert (obj.type == 'ARMATURE')
            bpy.types.Object.__delitem__(obj, "g2_prop_scale")
        return {'FINISHED'}


class GLAMetaExport(bpy.types.Operator):
    '''Export GLA Metadata Operator.'''
    bl_idname = "export_scene.gla_meta"
    bl_label = "Export SoF2 Ghoul 2 Animation metadata (.cfg)"
    bl_description = "Exports timeline markers labelling the animations to a .cfg file"
    bl_options = {'REGISTER', 'UNDO'}

    filename_ext = "*.cfg"

    # properties
    filepath: bpy.props.StringProperty(
        name="File Path", description="The filename to export to", maxlen=1024, default="", subtype='FILE_PATH')  # pyright: ignore [reportInvalidTypeForm]
    offset: bpy.props.IntProperty(
        name="Offset", description="Frame offset for the animations, e.g. 21376 if you plan on merging with Jedi Academy's _humanoid.gla", min=0, default=0)  # pyright: ignore [reportInvalidTypeForm]

    def execute(self, context):
        print("\n== GLA Metadata Export ==\n")

        startFrame = context.scene.frame_start
        endFrame = context.scene.frame_end
        fps = context.scene.render.fps

        class Marker:
            def __init__(self, blenderMarker):
                self.name = blenderMarker.name
                self.start = blenderMarker.frame - startFrame  # frames start at 0
                self.len = None  # to be determined

        markers = []
        maxLen = 23  # maximum name length, default minimum is 24
        for marker in context.scene.timeline_markers:
            if marker.frame >= startFrame and marker.frame <= endFrame:
                maxLen = max(maxLen, len(marker.name))
                markers.append(Marker(marker))

        if len(markers) == 0:
            self.report({'ERROR'}, 'No timeline markers found! Add Markers to label animations.')

        # sort by frame
        markers.sort(key=lambda marker: marker.start)

        # determine length
        last = None
        for marker in markers:
            if last:
                last.len = marker.start - last.start
            last = marker
        assert (last)  # otherwise len(markers) == 0
        last.len = endFrame - last.start

        file = open(self.filepath, "w")

        # name, start, length, loop (always false, cannot be set yet), fps (always scene's fps currently)
        pattern = "{:<" + str(maxLen) + "} {:<7} {:<7} {:<7} {}\n"

        file.write("// Animation Data generated from Blender Markers\n")
        file.write(pattern.format("// name", "start", "length", "loop", "fps"))

        for marker in markers:
            file.write(pattern.format(marker.name, marker.start +
                       self.offset, marker.len, 0, fps))

        file.close()

        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        wm.fileselect_add(self)
        return {'RUNNING_MODAL'}

# menu button callback functions


def menu_func_export_glm(self, context):
    self.layout.operator(GLMExport.bl_idname, text="SoF2 Ghoul 2 model (.glm)")


def menu_func_export_gla(self, context):
    self.layout.operator(GLAExport.bl_idname,
                         text="SoF2 Ghoul 2 skeleton/animation (.gla)")


def menu_func_export_gla_meta(self, context):
    self.layout.operator(GLAMetaExport.bl_idname,
                         text="SoF2 Ghoul 2 animation markers (.cfg)")


def menu_func_import_glm(self, context):
    self.layout.operator(GLMImport.bl_idname, text="SoF2 Ghoul 2 model (.glm)")


def menu_func_import_gla(self, context):
    self.layout.operator(GLAImport.bl_idname,
                         text="SoF2 Ghoul 2 skeleton/animation (.gla)")

# menu button init/destroy


def register():
    bpy.utils.register_class(GLMExport)
    bpy.utils.register_class(GLAExport)
    bpy.utils.register_class(GLAMetaExport)
    bpy.utils.register_class(GLMImport)
    bpy.utils.register_class(GLAImport)

    bpy.utils.register_class(ObjectAddG2Properties)
    bpy.utils.register_class(ObjectRemoveG2Properties)

    bpy.types.TOPBAR_MT_file_export.append(menu_func_export_glm)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export_gla)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export_gla_meta)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import_glm)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import_gla)


def unregister():
    bpy.utils.unregister_class(GLMExport)
    bpy.utils.unregister_class(GLAExport)
    bpy.utils.unregister_class(GLAMetaExport)
    bpy.utils.unregister_class(GLMImport)
    bpy.utils.unregister_class(GLAImport)

    bpy.utils.unregister_class(ObjectAddG2Properties)
    bpy.utils.unregister_class(ObjectRemoveG2Properties)

    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export_glm)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export_gla)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import_glm)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import_gla)
