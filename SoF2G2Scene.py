from .mod_reload import reload_modules

reload_modules(
    locals(),
    __package__,
    ["SoF2Filesystem", "SoF2G2Constants", "SoF2G2GLM", "SoF2G2GLA"],
    [".error_types", ".casts"],
)  # nopep8

from typing import Optional, Tuple  # noqa: E402
from . import SoF2Filesystem  # noqa: E402
from . import SoF2G2Constants  # noqa: E402
from . import SoF2G2GLM  # noqa: E402
from . import SoF2G2GLA  # noqa: E402
from .error_types import ErrorMessage, NoError  # noqa: E402
from .casts import optional_cast  # noqa: E402

import bpy  # pyright: ignore[reportMissingImports]  # noqa: E402


def findSceneRootObject() -> Optional[bpy.types.Object]:
    scene_root = None
    if "scene_root" in bpy.data.objects:
        # if so, use that
        scene_root = bpy.data.objects["scene_root"]
    return scene_root


class Scene:
    def __init__(self, basepath: str):
        self.basepath = basepath
        self.scale = 1.0
        self.glm: Optional[SoF2G2GLM.GLM] = None
        self.gla: Optional[SoF2G2GLA.GLA] = None

    # Fills scene from on GLM file
    def loadFromGLM(
        self, glm_filepath_rel: str, selected_skin_data: dict
    ) -> Tuple[bool, ErrorMessage]:
        success, glm_filepath_abs = SoF2Filesystem.FindFile(
            glm_filepath_rel, self.basepath, ["glm"]
        )
        if not success:
            print("File not found: ", self.basepath + glm_filepath_rel + ".glm", sep="")
            return False, ErrorMessage(
                f".glm file {glm_filepath_rel} not found in basepath ({self.basepath})"
            )

        if (
            len(selected_skin_data.get("prefs", {}).get("surfaces_on", {})) == 0
            and len(selected_skin_data.get("prefs", {}).get("surfaces_off", {})) == 0
            and selected_skin_data
        ):
            print(
                "Warning: No surfaces_on/off found in skin file - need might need to tweak g2skin file if you see pink textures!"
            )
        else:
            print(
                f"Loaded {len(selected_skin_data.get('prefs', {}).get('surfaces_on', {}))} surfaces_on and {len(selected_skin_data.get('prefs', {}).get('surfaces_off', {}))} surfaces_off from skin data"
            )

        self.glm = SoF2G2GLM.GLM()

        success, message = self.glm.loadFromFile(glm_filepath_abs, selected_skin_data)
        if not success:
            return False, message
        return True, NoError

    # Loads scene from on GLA file
    def loadFromGLA(
        self,
        gla_filepath_rel: str,
        loadAnimations=SoF2G2GLA.AnimationLoadMode.NONE,
        startFrame=0,
        numFrames=1,
        data_frames_file=dict(),
    ) -> Tuple[bool, ErrorMessage]:
        # create default skeleton if necessary (doing it here is a bit of a hack)
        if gla_filepath_rel == "*default":
            self.gla = SoF2G2GLA.GLA()
            self.gla.header.numBones = 1
            self.gla.isDefault = True
            return True, NoError
        success, gla_filepath_abs = SoF2Filesystem.FindFile(
            gla_filepath_rel, self.basepath, ["gla"]
        )
        if not success:
            print("File not found: ", self.basepath + gla_filepath_rel + ".gla", sep="")
            return False, ErrorMessage(
                f".gla file {gla_filepath_rel} not found in basepath ({self.basepath})"
            )
        self.gla = SoF2G2GLA.GLA()
        success, message = self.gla.loadFromFile(
            gla_filepath_abs, loadAnimations, startFrame, numFrames, data_frames_file
        )
        if not success:
            return False, message
        return True, NoError

    # "Loads" model from Blender data
    def loadModelFromBlender(self, glm_filepath_rel, gla_filepath_rel):
        self.glm = SoF2G2GLM.GLM()
        success, message = self.glm.loadFromBlender(
            glm_filepath_rel, gla_filepath_rel, self.basepath
        )
        if not success:
            return False, message
        return True, ""

    # "Loads" skeleton & animation from Blender data
    def loadSkeletonFromBlender(self, gla_filepath_rel, gla_reference_rel):
        self.gla = SoF2G2GLA.GLA()
        gla_reference_abs = ""
        if gla_reference_rel != "":
            success, gla_reference_abs = SoF2Filesystem.FindFile(
                gla_reference_rel, self.basepath, ["gla"]
            )
            if not success:
                return False, "Could not find reference GLA"
        success, message = self.gla.loadFromBlender(gla_filepath_rel, gla_reference_abs)
        if not success:
            return False, message
        return True, ""

    # saves the model to a .glm file
    def saveToGLM(self, glm_filepath_rel):
        glm_filepath_abs = (
            SoF2Filesystem.AbsPath(glm_filepath_rel, self.basepath) + ".glm"
        )
        success, message = optional_cast(SoF2G2GLM.GLM, self.glm).saveToFile(
            glm_filepath_abs
        )
        if not success:
            return False, message
        return True, ""

    # saves the skeleton & animations to a .gla file
    def saveToGLA(self, gla_filepath_rel):
        gla_filepath_abs = (
            SoF2Filesystem.AbsPath(gla_filepath_rel, self.basepath) + ".gla"
        )
        success, message = optional_cast(SoF2G2GLA.GLA, self.gla).saveToFile(
            gla_filepath_abs
        )
        if not success:
            return False, message
        return True, ""

    # "saves" the scene to blender
    # skeletonFixes is an enum with possible skeleton fixes - e.g. 'JKA' for connection- and
    def saveToBlender(
        self,
        scale,
        selected_skin_data: dict,
        guessTextures: bool,
        useAnimation: bool,
        skeletonFixes: SoF2G2Constants.SkeletonFixes,
        data_frames_file: dict,
    ) -> Tuple[bool, ErrorMessage]:
        # is there already a scene root in blender?
        scene_root = findSceneRootObject()
        if scene_root:
            # make sure it's linked to the current scene
            if "scene_root" not in bpy.context.scene.collection.objects:
                bpy.context.scene.collection.objects.link(scene_root)
        else:
            # create it otherwise
            scene_root = bpy.data.objects.new("scene_root", None)
            scene_root.scale = (scale, scale, scale)
            bpy.context.scene.collection.objects.link(scene_root)
        # there's always a skeleton (even if it's *default)
        success, message = optional_cast(SoF2G2GLA.GLA, self.gla).saveToBlender(
            scene_root, useAnimation, skeletonFixes, data_frames_file
        )
        if not success:
            return False, message
        if self.glm:
            success, message = self.glm.saveToBlender(
                self.basepath,
                optional_cast(SoF2G2GLA.GLA, self.gla),
                scene_root,
                selected_skin_data,
                guessTextures,
            )
            if not success:
                return False, message
        return True, NoError

    # returns the relative path of the gla file referenced in the glm header
    def getRequestedGLA(self) -> str:
        return optional_cast(SoF2G2GLM.GLM, self.glm).getRequestedGLA()
