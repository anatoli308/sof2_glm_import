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
reload_modules(locals(), __package__, ["JAMaterialmanager","JAFilesystem", "JAStringhelper"], [".casts", ".error_types"])  # nopep8

from typing import Optional, Tuple
from . import JAFilesystem
from . import JAStringhelper
from .casts import downcast
from .error_types import ErrorMessage, NoError

import bpy

class MaterialManager():
    def __init__(self):
        self.basepath = ""
        self.materials = {}
        self.guessTextures = False
        self.useSkin = False
        self.initialized = False

    def init(self, basepath: str, selected_g2skin_data: dict, guessTextures: bool):
        self.basepath = basepath
        self.guessTextures = guessTextures
        self.skin = {}

        # sicherstellen, dass wir Daten haben
        if not selected_g2skin_data or "materials" not in selected_g2skin_data:
            return False, ErrorMessage("Kein gültiges g2skin-JSON übergeben")

        for mat in selected_g2skin_data.get("materials", []):
            mat_name = mat.get("name")
            if not mat_name:
                continue

            # Falls mehrere groups existieren, nimm den ersten Treffer
            for grp in mat.get("groups", []):
                if "texture1" in grp:
                    tex = grp["texture1"].strip('"')
                    print(f"Mapping material '{mat_name}' to texture '{tex}'")
                    self.skin[mat_name] = tex
                    break
                elif "shader1" in grp:
                    shader = grp["shader1"].strip('"')
                    print(f"Mapping material '{mat_name}' to shader '{shader}'")
                    self.skin[mat_name] = shader
                    break

        self.useSkin = True
        self.initialized = True
        return True, NoError

    def getMaterial(self, name, bsShader, shader_def: str = ""):
        """
        Lädt ein Material basierend auf dem G2/G3 Shader.
        shader_def: Text der Shader-Definition (.shader)
        """
        assert self.initialized

        shader = JAStringhelper.decode(bsShader)
        if self.useSkin and shader in self.skin:
            shader = self.skin[shader]

        if shader.lower() in ["[nomaterial]", "", "*off"]:
            return

        if shader.lower() in self.materials:
            return self.materials[shader.lower()]

        # Neues Material erstellen
        mat = bpy.data.materials.new(shader)
        self.materials[shader.lower()] = mat

        # Texture suchen
        success, path = JAFilesystem.FindFile(shader, self.basepath, ["jpg", "png", "tga"])
        if not success:
            print(f"Texture not found: {shader}")
            mat.diffuse_color = (1, 0, 1, 1)  # Pink fallback
            return mat

        # Material Node Setup
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        # Vorhandene Nodes entfernen
        for node in nodes:
            nodes.remove(node)

        # Material Output
        output_node = nodes.new(type='ShaderNodeOutputMaterial')
        output_node.location = (400, 0)

        # Texture Node
        tex_node = nodes.new(type='ShaderNodeTexImage')
        tex_node.image = bpy.data.images.load(path)
        tex_node.location = (-400, 0)

        # Shader wählen je nach Shader-Definition
        shader_node = nodes.new(type='ShaderNodeBsdfDiffuse')
        shader_node.location = (0, 0)
        color_input_name = 'Color'

        links.new(tex_node.outputs['Color'], shader_node.inputs[color_input_name])
        links.new(shader_node.outputs['BSDF'], output_node.inputs['Surface'])

        return mat

