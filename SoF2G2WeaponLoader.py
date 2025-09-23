import os
from typing import cast

from .SoF2G2Constants import SkeletonFixes
from . import SoF2G2DataCache as DataCache
from . import SoF2G2Scene
from . import SoF2G2GLA
from . import frames_parser

def handle_load_weapon_file(op):
    basepath = os.path.normpath(op.basepath)

    _, weapons = DataCache.get_weapon_enum_items(basepath) #TODO caching if slow inside search context!?
    
    # Load SOF2.item file
    print("Loading SOF2.item")
    _, loaded_default_items_data = DataCache.get_default_item_file(basepath,"ext_data/SOF2.item")

    success, message = DataCache.generate_json_results(weapons, loaded_default_items_data, basepath)
    if success:
        op.report({"INFO"}, message)
        print(message)

    found_weapon_data = next((w for w in weapons if w.get("name") == op.weapon_selected), None)
    if not found_weapon_data:
        op.report({"ERROR"}, "No weapon data found for the selected weapon.")
        return {"CANCELLED"}

    scale = op.scale / 100
    
    scene = SoF2G2Scene.Scene(basepath)
    success, message = scene.loadFromGLM(found_weapon_data.get("wpn", {}).get("model"), {}) #found_weapon_data.get("weaponmodel", {}).get("model")
    if not success:
        op.report({"ERROR"}, message)
        return {"FINISHED"}

    glafile = scene.getRequestedGLA()
    data_frames_file_path = os.path.normpath(basepath + "/" + glafile + ".frames")
    print(f"Loading .frames file: {data_frames_file_path}")
    text = open(
        data_frames_file_path,
        "r",
        encoding="utf-8",
    ).read()
    data_frames_file = frames_parser.parse_frames(text)
    print(f"Loading GLA file: {glafile}")
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

    # Load shader file for weapon
    print("Loading .shader file: weapons.shader")
    _, loaded_shader_data = DataCache.get_shaders_data(basepath, "weapons")

    #TODO load gore stuff
    #TODO load righ/left hand for first person (SOF2.inview)
    #TODO .skl parsen & verarbeiten 

    guessTextures = True
    success, message = scene.saveToBlender(
        scale,
        {},
        loaded_shader_data,
        guessTextures,
        loadAnimations != SoF2G2GLA.AnimationLoadMode.NONE,
        SkeletonFixes[op.skeletonFixes],
        data_frames_file,
    )
    if not success:
        op.report({"ERROR"}, message)

    op.report({"INFO"}, f"Weapon/Object loaded: {op.weapon_selected}")
    return {"FINISHED"}
