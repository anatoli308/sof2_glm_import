import os

from . import SoF2G2Exporter
from . import SoF2G2Scene
from . import SoF2G2GLA
from . import frames_parser
from .SoF2G2Constants import SkeletonFixes
from typing import cast


def handle_load_glm_file(op):
    selected_glm_file = os.path.basename(os.path.normpath(op.filepath))

    norm_path = os.path.normpath(op.filepath)
    parts = norm_path.split(os.sep)
    if "base" in parts:
        base_index = parts.index("base")
        base_path = os.sep.join(parts[: base_index + 1])
    else:
        op.report(
            {"ERROR"},
            "No base path found! You need to load a glm/gla/md3 from your SoF2 base path!",
        )
        return {"CANCELLED"}

    # TODO WIP
    #
    print(f"You selected file: {selected_glm_file}")
    print(f"You selected base path: {base_path}")
    if selected_glm_file.endswith(".glm"):
        print("loading glm file")
        # success, message, all_data = SoF2G2Exporter.export_all_data(base_path)
        # if success:
        #    op.report({"INFO"}, message)
        #    print(message)

        # Gruppiere alle CharacterTemplates nach ihrem Modell
        """
        characters_by_model = {}
        npcs_data = all_data.get("npcs", {})
        for npc_filename, npc_content in npcs_data.items():
            char_templates = npc_content.get("CharacterTemplate", [])
            if not isinstance(char_templates, list):
                char_templates = [char_templates]

            for ct in char_templates:
                model = ct.get("Model", "")
                if model:  # Nur Modelle mit Pfad berücksichtigen
                    if model not in characters_by_model:
                        characters_by_model[model] = []
                    characters_by_model[model].append(ct)

        print(f"Found {len(characters_by_model)} unique models used by NPCs:")
        for model, characters in characters_by_model.items():
            num_no_deathmatch = sum(
                1 for char in characters if "Deathmatch" not in char
            )
            print(
                f"\nModel: {model} (used by {len(characters)} characters, {num_no_deathmatch} without 'Deathmatch' flag)"
            )
            for char in characters:
                if "Deathmatch" not in char:
                    print(f"  - {char.get('Name')}")
        """

        # Hier kannst du mit den `snow_characters` weiterarbeiten.
        # Zum Beispiel das erste gefundene Modell laden:

        # selected_glm_file = selected_glm_file.removesuffix(".glm")

        scale = op.scale / 100
        scene = SoF2G2Scene.Scene(base_path)
        success, message = scene.loadFromGLM(
            "/".join(parts[-4:]),
            {},
        )
        if not success:
            op.report({"ERROR"}, message)
            return {"FINISHED"}

        glafile = scene.getRequestedGLA()
        data_frames_file_path = os.path.normpath(
            base_path + "/" + glafile + "_mp.frames"
        )
        if not os.path.exists(data_frames_file_path):
            # Versuche ohne '_mp'
            data_frames_file_path = os.path.normpath(
                base_path + "/" + glafile + ".frames"
            )
        
        print(f"Loading .frames file: {data_frames_file_path}")
        text = open(
            data_frames_file_path,
            "r",
            encoding="utf-8",
        ).read()
        data_frames_file = frames_parser.parse_frames(text)
        
        gla_with_mp = glafile + "_mp"
        gla_path_with_mp = os.path.normpath(base_path + "/" + gla_with_mp + ".gla")
        if os.path.exists(gla_path_with_mp):
            glafile = gla_with_mp
        # sonst bleibt glafile wie es ist (ohne _mp)
        
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
            {},
            {},
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
        print("loading npc file")

    op.report({"INFO"}, f"GLM loading not implemented yet: {selected_glm_file}")
    return {"FINISHED"}
