import os

from . import SoF2G2Exporter
from . import SoF2G2Scene

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
        success, message, all_data = SoF2G2Exporter.export_all_data(base_path)
        if success:
            op.report({"INFO"}, message)
            print(message)
        
        # Gruppiere alle CharacterTemplates nach ihrem Modell
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
            num_no_deathmatch = sum(1 for char in characters if "Deathmatch" not in char)
            print(f"\nModel: {model} (used by {len(characters)} characters, {num_no_deathmatch} without 'Deathmatch' flag)")
            for char in characters:
                if "Deathmatch" not in char:
                    print(f"  - {char.get('Name')}")
        
        # Hier kannst du mit den `snow_characters` weiterarbeiten.
        # Zum Beispiel das erste gefundene Modell laden:

        scene = SoF2G2Scene.Scene(op.basepath)
        success, message = scene.loadFromGLM("models/characters/average_sleeves/average_sleeves.glm")
        if not success:
            op.report({"ERROR"}, message)
            return {"FINISHED"}
    else:
        print("loading npc file")

    op.report({"INFO"}, f"GLM loading not implemented yet: {selected_glm_file}")
    return {"FINISHED"}
