import os
from typing import cast

from .SoF2G2Constants import SkeletonFixes
from .SoF2G2DataCache import get_npcs_folder_data_cached
from . import SoF2G2DataCache as DataCache
from . import SoF2G2Exporter
from . import SoF2G2Scene
from . import SoF2G2GLA
from . import frames_parser
# skl parsing is handled within exporter now


def find_skin_data_by_file_value(skin_data: dict, file_name: str):
    """
    Gibt das Value (dict) zurück, dessen Key den file_name enthält.
    Beispiel: file_name="prometheus_snow1" findet den Value von "prometheus_snow1.g2skin".
    """
    for skin_file, skin_value in skin_data.items():
        if file_name in skin_file:
            return skin_value
    return None


def find_character_template_by_key(npcs_data, key):
    """
    Find the character template for a specific NPC key.

    Args:
        npcs_data: Dictionary containing all NPC data
        key: String name of the NPC to find

    Returns:
        Dictionary containing the character template, or None if not found
    """
    all_char_templates = []
    for npc_filename, npc_content in npcs_data.items():
        char_templates = npc_content.get("CharacterTemplate", [])
        if not isinstance(char_templates, list):
            char_templates = [char_templates]

        # Extend each char_template with npc_filename and group_info
        for char_template in char_templates:
            extended_template = dict(char_template)  # Create a copy
            extended_template["npc_filename"] = npc_filename
            extended_template["group_info"] = npc_content.get("GroupInfo", {})
            all_char_templates.append(extended_template)

    found_char_template = None
    for char_template in all_char_templates:
        if char_template.get("Name") == key:
            found_char_template = {
                "char_template": char_template,
                "npc_filename": char_template.get("npc_filename"),
                "group_info": char_template.get("group_info", {}),
            }
    return all_char_templates, found_char_template


def handle_load_npc_file(op):
    # Export everything in one go; no preloading here
    success, message, all_data = SoF2G2Exporter.export_all_data(op.basepath)
    if success:
        op.report({"INFO"}, message)
        print(message)

    # Now fetch data needed for loading the selected NPC
    npcs_files_data = all_data["npcs"]

    npcs_data, character_template = find_character_template_by_key(
        npcs_files_data, op.npc_selected
    )

    if character_template:
        print(f"Found character template for {op.npc_selected}:")
        character_model_path = character_template.get("char_template", {}).get(
            "Model", None
        )
        _, all_g2skin_files_data = DataCache.get_skins(
            getattr(op, "basepath", ""), character_model_path
        )

        g2_skin_file_name = None
        parent_char_template_skin_information = None
        if not all_g2skin_files_data:
            parent_template = character_template.get("group_info", {}).get(
                "ParentTemplate", None
            )
            if parent_template:
                print(
                    f"NPC got a Parent NPC template #TODO load it later: {parent_template}"
                )
                _, parent_char_template_data = find_character_template_by_key(
                    npcs_files_data, parent_template
                )
                if parent_char_template_data:
                    character_model_path = parent_char_template_data.get(
                        "char_template", {}
                    ).get("Model", None)
                    _, all_g2skin_files_data = DataCache.get_skins(
                        getattr(op, "basepath", ""), character_model_path
                    )
                    parent_char_template_skin_files = parent_char_template_data.get(
                        "char_template", {}
                    ).get("Skin", {})
                    if isinstance(parent_char_template_skin_files, dict):
                        parent_char_template_skin_information = (
                            parent_char_template_skin_files
                        )
                    elif isinstance(parent_char_template_skin_files, list):
                        parent_char_template_skin_information = (
                            parent_char_template_skin_files[0]
                        )
                    else:
                        print(
                            "In deiner Parent .npc Datei sind die Skin Einträge fehlerhaft (wrong type):",
                            type(parent_char_template_skin_files),
                        )
                        return {"CANCELLED"}

            if not parent_char_template_skin_information:
                op.report(
                    {"ERROR"},
                    "No g2skin file found! Check your loaded .npc file definition if you load one.",
                )
                return {"CANCELLED"}
            else:
                g2_skin_file_name = parent_char_template_skin_information.get("File")

        if not g2_skin_file_name:
            character_template_skin_files = character_template.get(
                "char_template", {}
            ).get("Skin", {})
            if isinstance(character_template_skin_files, dict):
                character_template_skin_information = character_template_skin_files
            elif isinstance(character_template_skin_files, list):
                character_template_skin_information = (
                    character_template_skin_files[0]
                    if character_template_skin_files
                    else None
                )
            else:
                print(
                    "In deiner .npc Datei sind die Skin Einträge fehlerhaft (wrong type):",
                    type(character_template_skin_files),
                )
                return {"CANCELLED"}

            if not character_template_skin_information:
                # if no skin found we try first g2skin file in all_g2skin_files_data
                g2_skin_file_name = next(iter(all_g2skin_files_data.keys()), None)
                if not g2_skin_file_name:
                    op.report(
                        {"ERROR"},
                        "No g2skin file found! Check your loaded .npc file definition if you load one.",
                    )
                    return {"CANCELLED"}
            else:
                # if skin found we use the first file name from the character template
                g2_skin_file_name = character_template_skin_information.get("File")

        print(f"Loading .g2skin file: {g2_skin_file_name}.g2skin")
        selected_g2skin_data = find_skin_data_by_file_value(
            all_g2skin_files_data, g2_skin_file_name
        )
        if not selected_g2skin_data:
            op.report(
                {"ERROR"},
                "No g2skin file found! Check your loaded .npc file definition if you load one.",
            )
            return {"CANCELLED"}

        loaded_model_from_g2 = os.path.splitext(os.path.basename(character_model_path))[
            0
        ]
        print(f"Loading .shader file: {loaded_model_from_g2}.shader")
        _, loaded_shader_data = DataCache.get_shaders_data(
            op.basepath, loaded_model_from_g2
        )

        skin_materials = selected_g2skin_data.get("materials", [])

        for mat in skin_materials:
            for group in mat.get("groups", []):
                for key in ["texture1", "shader1"]:
                    if key in group:
                        shader_key = group[key]
                        if shader_key in loaded_shader_data:
                            group[key] = loaded_shader_data[shader_key]["blocks"][0][
                                "map"
                            ]

        has_deathmatch_flag = character_template.get("char_template", {}).get(
            "Deathmatch", None
        )

        scale = op.scale / 100

        scene = SoF2G2Scene.Scene(op.basepath)
        success, message = scene.loadFromGLM(character_model_path, selected_g2skin_data)
        if not success:
            op.report({"ERROR"}, message)
            return {"FINISHED"}

        glafile = scene.getRequestedGLA()
        data_frames_file_path = os.path.normpath(
            op.basepath
            + "/"
            + glafile
            + (".frames" if has_deathmatch_flag else "_mp.frames")
        )
        print(f"Loading .frames file: {data_frames_file_path}")
        text = open(
            data_frames_file_path,
            "r",
            encoding="utf-8",
        ).read()
        data_frames_file = frames_parser.parse_frames(text)

        if not has_deathmatch_flag:
            glafile = glafile + "_mp"

        print(f"Loading GLA file: {glafile} ")
        loadAnimations = SoF2G2GLA.AnimationLoadMode[op.loadAnimations]
        success, message = scene.loadFromGLA(
            glafile,
            loadAnimations,
            cast(int, op.startFrame),
            cast(int, op.numFrames),
            data_frames_file,
        )
        if not success:
            op.report({"ERROR"}, message)
            return {"FINISHED"}

        # Load shader file for NPC

        guessTextures = True
        success, message = scene.saveToBlender(
            scale,
            selected_g2skin_data,
            loaded_shader_data,
            guessTextures,
            loadAnimations != SoF2G2GLA.AnimationLoadMode.NONE,
            SkeletonFixes[op.skeletonFixes],
            data_frames_file,
        )
        if not success:
            op.report({"ERROR"}, message)
        op.report({"INFO"}, f"NPC loaded: {op.npc_selected}")
        return {"FINISHED"}

    else:
        print(f"No character template found for key: {op.npc_selected}")
        return {"CANCELLED"}
