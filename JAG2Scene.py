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

# Main File containing the important definitions

from .mod_reload import reload_modules
reload_modules(locals(), __package__, ["JAFilesystem", "JAG2Constants", "JAG2GLM", "JAG2GLA"], [".error_types", ".casts"])  # nopep8

from typing import Optional, Tuple
from . import JAFilesystem
from . import JAG2Constants
from . import JAG2GLM
from . import JAG2GLA
from .error_types import ErrorMessage, NoError
from .casts import optional_cast

import bpy


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
        self.glm: Optional[JAG2GLM.GLM] = None
        self.gla: Optional[JAG2GLA.GLA] = None
        self.surfaces_on = set()
        self.surfaces_off = set()

    # Fills scene from on GLM file
    def loadFromGLM(self, glm_filepath_rel: str, skin_rel: str = "") -> Tuple[bool, ErrorMessage]:
        success, glm_filepath_abs = JAFilesystem.FindFile(
            glm_filepath_rel, self.basepath, ["glm"])
        if not success:
            print("File not found: ", self.basepath +
                  glm_filepath_rel + ".glm", sep="")
            return False, ErrorMessage(f".glm file {glm_filepath_rel} not found in basepath ({self.basepath})")
        
        # Load skin prefs before loading GLM
        if skin_rel:
            success, message = self._loadSkinPrefs(skin_rel)
            if not success:
                print(f"Warning: Could not load skin prefs: {message}")

        if len(self.surfaces_on) == 0 and len(self.surfaces_off) == 0 and skin_rel:
            print("Warning: No surfaces_on/off found in skin file - fallback to model default")        
        
        self.glm = JAG2GLM.GLM()

        g2skin_definition = {
            "surfaces_off": list(self.surfaces_off),
            "surfaces_on": list(self.surfaces_on)
        }
        success, message = self.glm.loadFromFile(glm_filepath_abs, g2skin_definition)
        if not success:
            return False, message
        return True, NoError

    def _loadSkinPrefs(self, skin_rel: str) -> Tuple[bool, ErrorMessage]:
        """Load surfaces_on/off from .g2skin prefs block"""
        success, skin_abs = JAFilesystem.FindFile("models/characters/skins/" + skin_rel,
                                                self.basepath, ["g2skin"])
        if not success:
            return False, ErrorMessage(f"Skin file not found: {skin_rel}")

        try:
            self.surfaces_on = set()
            self.surfaces_off = set()

            with open(skin_abs, "r", encoding="utf-8", errors="ignore") as file:
                lines = file.readlines()

            stack: list[str] = []

            for raw in lines:
                line = raw.strip()
                if not line or line.startswith("//") or line.startswith("#"):
                    continue

                # Header + { auf einer Zeile
                if line.endswith("{") and not line.startswith("{"):
                    header = line.split("{", 1)[0].strip()
                    stack.append(header)
                    continue

                # Header ohne { → kommt in nächster Zeile
                if line in ("prefs", "models", "surfaces_on", "surfaces_off",
                            "material", "group"):
                    stack.append(line)
                    continue

                # Nur Klammer öffnen
                if line == "{":
                    continue

                # Blockende
                if line == "}":
                    if stack:
                        stack.pop()
                    continue

                # Namen in surfaces_on/off
                if stack and stack[-1] in ("surfaces_on", "surfaces_off") and line.startswith("name"):
                    parts = line.split()
                    if len(parts) >= 2:
                        value = parts[-1].strip('"')
                        if value:
                            if stack[-1] == "surfaces_on":
                                self.surfaces_on.add(value)
                            else:
                                self.surfaces_off.add(value)

            print(f"Loaded skin prefs: {len(self.surfaces_on)} Surfaces ON, {len(self.surfaces_off)} Surfaces OFF")
            return True, NoError

        except Exception as e:
            return False, ErrorMessage(f"Error parsing skin file: {e}")


    # Loads scene from on GLA file
    def loadFromGLA(self, gla_filepath_rel: str, loadAnimations=JAG2GLA.AnimationLoadMode.NONE, startFrame=0, numFrames=1) -> Tuple[bool, ErrorMessage]:
        # create default skeleton if necessary (doing it here is a bit of a hack)
        if gla_filepath_rel == "*default":
            self.gla = JAG2GLA.GLA()
            self.gla.header.numBones = 1
            self.gla.isDefault = True
            return True, NoError
        success, gla_filepath_abs = JAFilesystem.FindFile(
            gla_filepath_rel, self.basepath, ["gla"])
        if not success:
            print("File not found: ", self.basepath +
                  gla_filepath_rel + ".gla", sep="")
            return False, ErrorMessage(f".gla file {gla_filepath_rel} not found in basepath ({self.basepath})")
        self.gla = JAG2GLA.GLA()
        success, message = self.gla.loadFromFile(
            gla_filepath_abs, loadAnimations, startFrame, numFrames)
        if not success:
            return False, message
        return True, NoError

    # "Loads" model from Blender data
    def loadModelFromBlender(self, glm_filepath_rel, gla_filepath_rel):
        self.glm = JAG2GLM.GLM()
        success, message = self.glm.loadFromBlender(
            glm_filepath_rel, gla_filepath_rel, self.basepath)
        if not success:
            return False, message
        return True, ""

    # "Loads" skeleton & animation from Blender data
    def loadSkeletonFromBlender(self, gla_filepath_rel, gla_reference_rel):
        self.gla = JAG2GLA.GLA()
        gla_reference_abs = ""
        if gla_reference_rel != "":
            success, gla_reference_abs = JAFilesystem.FindFile(
                gla_reference_rel, self.basepath, ["gla"])
            if not success:
                return False, "Could not find reference GLA"
        success, message = self.gla.loadFromBlender(
            gla_filepath_rel, gla_reference_abs)
        if not success:
            return False, message
        return True, ""

    # saves the model to a .glm file
    def saveToGLM(self, glm_filepath_rel):
        glm_filepath_abs = JAFilesystem.AbsPath(
            glm_filepath_rel, self.basepath) + ".glm"
        success, message = optional_cast(JAG2GLM.GLM, self.glm).saveToFile(glm_filepath_abs)
        if not success:
            return False, message
        return True, ""

    # saves the skeleton & animations to a .gla file
    def saveToGLA(self, gla_filepath_rel):
        gla_filepath_abs = JAFilesystem.AbsPath(
            gla_filepath_rel, self.basepath) + ".gla"
        success, message = optional_cast(JAG2GLA.GLA, self.gla).saveToFile(gla_filepath_abs)
        if not success:
            return False, message
        return True, ""

    # "saves" the scene to blender
    # skeletonFixes is an enum with possible skeleton fixes - e.g. 'JKA' for connection- and
    def saveToBlender(self, scale, skin_rel, guessTextures: bool, useAnimation: bool, skeletonFixes: JAG2Constants.SkeletonFixes) -> Tuple[bool, ErrorMessage]:
        # is there already a scene root in blender?
        scene_root = findSceneRootObject()
        if scene_root:
            # make sure it's linked to the current scene
            if not "scene_root" in bpy.context.scene.collection.objects:
                bpy.context.scene.collection.objects.link(scene_root)
        else:
            # create it otherwise
            scene_root = bpy.data.objects.new("scene_root", None)
            scene_root.scale = (scale, scale, scale)
            bpy.context.scene.collection.objects.link(scene_root)
        # there's always a skeleton (even if it's *default)
        success, message = optional_cast(JAG2GLA.GLA, self.gla).saveToBlender(
            scene_root, useAnimation, skeletonFixes)
        if not success:
            return False, message
        if self.glm:
            success, message = self.glm.saveToBlender(
                self.basepath, optional_cast(JAG2GLA.GLA, self.gla), scene_root, skin_rel, guessTextures)
            if not success:
                return False, message
        return True, NoError

    # returns the relative path of the gla file referenced in the glm header
    def getRequestedGLA(self) -> str:
        return optional_cast(JAG2GLM.GLM, self.glm).getRequestedGLA()
