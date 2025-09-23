import os
from typing import cast

from .SoF2G2Constants import SkeletonFixes
from .SoF2G2DataCache import get_npcs_folder_data_cached
from . import SoF2G2DataCache as DataCache
from . import SoF2G2Scene
from . import SoF2G2GLA
from . import frames_parser
from . import skl_parser


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
    _, npcs_files_data = get_npcs_folder_data_cached(op.basepath)

    npcs_data, character_template = find_character_template_by_key(
        npcs_files_data, op.npc_selected
    )

    # lese alle skl dateien aus basepath/skeletons folder,parse mit skl_parser.py und speichere sie im array all_skl_data
    all_skl_data = []
    for skl_file in os.listdir(os.path.join(op.basepath, "skeletons")):
        if skl_file.endswith(".skl"):
            skl_data = skl_parser.parse_skl(
                open(
                    os.path.join(op.basepath, "skeletons", skl_file),
                    "r",
                    encoding="utf-8",
                ).read()
            )
            # Add filename to the parsed data
            if isinstance(skl_data, dict):
                skl_data["filename"] = skl_file
            all_skl_data.append(skl_data)

    success, message = DataCache.generate_npc_json_results(
        npcs_data, op.basepath
    )
    if success:
        op.report({"INFO"}, message)
        print(message)
    
    # Generate individual SKL files
    success_skl, message_skl = DataCache.generate_individual_skl_files(all_skl_data, op.basepath)
    if success_skl:
        op.report({"INFO"}, message_skl)
        print(message_skl)

    if character_template:
        print(f"Found character template for {op.npc_selected}:")
        parent_template = character_template.get("group_info", {}).get(
            "ParentTemplate", None
        )
        if parent_template:
            print(
                f"NPC got a Parent NPC template #TODO load it later: {parent_template}"
            )

        character_model_path = character_template.get("char_template", {}).get(
            "Model", None
        )
        _, all_g2skin_files_data = DataCache.get_skins(
            getattr(op, "basepath", ""), character_model_path
        )

        character_template_skin_files = character_template.get("char_template", {}).get(
            "Skin", {}
        )
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
