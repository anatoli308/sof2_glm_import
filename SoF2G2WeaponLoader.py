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
    

    found_weapon_data = next((w for w in weapons if w.get("displayName") == op.weapon_selected), None)
    if not found_weapon_data:
        op.report({"ERROR"}, "No weapon data found for the selected weapon.")
        return {"CANCELLED"}

    scale = op.scale / 100

    scene = SoF2G2Scene.Scene(basepath)
    success, message = scene.loadFromGLM(found_weapon_data.get("model"), {})
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

    guessTextures = True
    success, message = scene.saveToBlender(
        scale,
        {},
        guessTextures,
        loadAnimations != SoF2G2GLA.AnimationLoadMode.NONE,
        SkeletonFixes[op.skeletonFixes],
        data_frames_file,
    )
    if not success:
        op.report({"ERROR"}, message)

    op.report({"INFO"}, f"Weapon/Object loaded: {op.weapon_selected}")
    return {"FINISHED"}
