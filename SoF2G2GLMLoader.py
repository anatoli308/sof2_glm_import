import os


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
            "No base path found! You need to load a glm from your SoF2 base path!",
        )
        return {"CANCELLED"}

    # TODO WIP
    #
    print(f"You selected file: {selected_glm_file}")
    print(f"You selected base path: {base_path}")

    op.report({"INFO"}, f"GLM loaded: {selected_glm_file}")
    return {"FINISHED"}
