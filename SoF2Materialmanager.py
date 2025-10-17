from .mod_reload import reload_modules

reload_modules(
    locals(),
    __package__,
    ["SoF2Materialmanager", "SoF2Filesystem", "SoF2Stringhelper"],
    [".casts", ".error_types"],
)  # nopep8

from . import SoF2Filesystem  # noqa: E402
from . import SoF2Stringhelper  # noqa: E402
from .error_types import ErrorMessage, NoError  # noqa: E402

import bpy  # noqa: E402  # pyright: ignore[reportMissingImports]
import os  # noqa: E402

log_level = os.getenv("LOG_LEVEL", "INFO")


class MaterialManager:
    def __init__(self):
        self.basepath = ""
        self.materials = {}
        self.guessTextures = False
        self.useSkin = False
        self.initialized = False

    def init(self, basepath: str, selected_g2skin_data: dict, loaded_shader_data: dict, guessTextures: bool):
        self.basepath = basepath
        self.guessTextures = guessTextures
        self.skin = {}

        # sicherstellen, dass wir Daten haben
        #if not selected_g2skin_data or "materials" not in selected_g2skin_data:
        #    return False, ErrorMessage("Kein gültiges g2skin-JSON übergeben")
        materials = selected_g2skin_data.get("materials", [])
        for mat in materials:
            mat_name = mat.get("name")
            if not mat_name:
                continue

            # Falls mehrere groups existieren, nimm den ersten Treffer
            for grp in mat.get("groups", []):
                if (
                    "texture1" in grp
                ):  # TODO Mehr als texture1 - textureX möglich erweitern!
                    tex = grp["texture1"].strip('"')
                    if log_level == "DEBUG":
                        print(f"Mapping material '{mat_name}' to texture '{tex}'")
                    self.skin[mat_name] = tex
                    break
                elif "shader1" in grp:
                    shader = grp["shader1"].strip('"')
                    if log_level == "DEBUG":  # TODO analog s.o.
                        print(f"Mapping material '{mat_name}' to shader '{shader}'")
                    self.skin[mat_name] = shader
                    break

        self.useSkin = True
        self.initialized = True
        return True, NoError

    # shader_def wird derzeit nicht verwendet!
    def getMaterial(
        self, name, bsShader, loaded_shader_data: dict, selected_skin_data: dict = {}
    ):
        """
        Lädt ein Material basierend auf dem G2/G3 Shader.
        loaded_shader_data: geparste Shader-Daten aus der .shader Datei - hilft, map-Einträge zu finden.
        selected_skin_data: optionale Skin-Daten für zusätzliche Material-Informationen.
        Versucht, BaseColor, Normal, Roughness, Metallic, AO, Emission automatisch zu finden.
        """
        assert self.initialized

        shader = SoF2Stringhelper.decode(bsShader)
        if self.useSkin and shader in self.skin:
            shader = self.skin[shader]

        if shader is None:
            return None

        if shader.lower() in ["[nomaterial]", "", "*off"]:
            return None

        key = shader.lower()
        if key in self.materials:
            return self.materials[key]

        # Check if we have loaded_shader_data for this shader key
        if loaded_shader_data and key in loaded_shader_data:
            shader_entry = loaded_shader_data[key]
            if isinstance(shader_entry, dict) and "blocks" in shader_entry:
                blocks = shader_entry["blocks"]
                if isinstance(blocks, list):
                    # Create materials for each block's map value
                    for i, block in enumerate(blocks):
                        if isinstance(block, dict) and "map" in block:
                            map_value = block["map"]
                            if map_value:
                                # Create a unique material name for each block
                                material_name = f"{shader}_{i}" if i > 0 else shader
                                material_key = material_name.lower()
                                
                                if material_key not in self.materials:
                                    mat = bpy.data.materials.new(material_name)
                                    self.materials[material_key] = mat
                                    print(f"Created material from shader data: {material_name} (map: {map_value})")
                                    
                                    # Configure the material with the map value
                                    self._configure_material_with_map(mat, map_value)
                                
                                # Return the first material found (or could return all)
                                if i == 0:
                                    return self.materials[material_key]
        
        # If we reach here, no shader data was found, create default material

        # Neues Material erstellen
        mat = bpy.data.materials.new(shader)
        self.materials[key] = mat

        # Hilfsfunktionen
        def _try_find_file(name_candidate: str):
            # wrapper für SoF2Filesystem.FindFile: returns (success, abs_path) or (False, "")
            if not name_candidate:
                return False, ""
            # if candidate contains extension already, FindFile should still work; try as-is
            return SoF2Filesystem.FindFile(
                name_candidate, self.basepath, ["jpg", "png", "tga", "dds"]
            )

        def _find_sidecar_images(base_path_abs: str):
            """
            Given an absolute path to the basecolor image, look for common sidecar texture files
            in same directory sharing the basename + suffix.
            Returns dict of possible maps: normal, roughness, metallic, ao, emission
            """
            res = {
                "normal": None,
                "roughness": None,
                "metallic": None,
                "ao": None,
                "emission": None,
            }
            if not base_path_abs or not os.path.isfile(base_path_abs):
                return res
            folder = os.path.dirname(base_path_abs)
            base = os.path.splitext(os.path.basename(base_path_abs))[0]
            exts = [".png", ".tga", ".jpg", ".dds"]
            suffixes = {
                "normal": ["_n", "_normal", "_norm", "_nrml", "_normalmap", "_bump"],
                "roughness": ["_r", "_rough", "_roughness"],
                "metallic": ["_m", "_metal", "_metallic"],
                "ao": ["_ao", "_ambientocclusion"],
                "emission": ["_emit", "_emiss", "_emission"],
            }
            for typ, suffs in suffixes.items():
                for s in suffs:
                    for ext in exts:
                        cand = os.path.join(folder, base + s + ext)
                        if os.path.isfile(cand):
                            res[typ] = cand
                            break
                    if res[typ]:
                        break
            return res

        # 1) Versuche Shader-Daten zu verwenden und erste 'map' zu finden
        base_texture_path = None
        if loaded_shader_data and key in loaded_shader_data:
            shader_entry = loaded_shader_data[key]
            if isinstance(shader_entry, dict) and "blocks" in shader_entry:
                blocks = shader_entry["blocks"]
                if isinstance(blocks, list) and len(blocks) > 0:
                    first_block = blocks[0]
                    if isinstance(first_block, dict) and "map" in first_block:
                        candidate = first_block["map"]
                        success, abs_path = _try_find_file(candidate)
                        if success:
                            base_texture_path = abs_path

        # 2) Wenn kein shader-data-map, versuche shader direkt als texture-name zu finden (wie vorher)
        if not base_texture_path:
            success, abs_path = _try_find_file(shader)
            if success:
                base_texture_path = abs_path

        # 3) Wenn immer noch nichts gefunden -> Fallback (no texture)
        if not base_texture_path:
            print(f"Texture not found: {shader}")
            ##mat.diffuse_color = (1, 0, 1, 1)  # Pink fallback
            return mat

        # 4) Suche Sidecar maps (normal, roughness, metallic, ao, emission)
        sidecars = _find_sidecar_images(base_texture_path)

        # 5) Node-Setup: Principled BSDF (Unity-optimized)
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        # clear existing nodes
        for node in nodes:
            nodes.remove(node)

        output_node = nodes.new(type="ShaderNodeOutputMaterial")
        output_node.location = (400, 0)

        principled = nodes.new(type="ShaderNodeBsdfPrincipled")
        principled.location = (0, 0)

        # **UNITY OPTIMIZATION: Set default values for better Unity export**
        principled.inputs["Roughness"].default_value = 0.5  # Default roughness
        principled.inputs["Metallic"].default_value = 0.0  # Default non-metallic

        # **UNITY OPTIMIZATION: Set specular if available (Blender version dependent)**
        try:
            principled.inputs["Specular"].default_value = 0.5  # Unity standard specular
        except KeyError:
            # Specular input not available in this Blender version
            pass

        # helper to create image texture node (Unity-optimized)
        def _create_image_node(
            abs_path: str, label: str, colorspace: str = "Non-Color", location=(-600, 0)
        ):
            try:
                img = bpy.data.images.load(abs_path, check_existing=True)

                # **UNITY OPTIMIZATION: Set texture settings for better Unity export**
                img.use_fake_user = True  # Prevent texture deletion
                img.pack()  # Pack texture into .blend file for Unity

                # **UNITY OPTIMIZATION: Set texture compression settings**
                if img.size[0] > 1024 or img.size[1] > 1024:
                    # Large textures - suggest compression
                    img.use_alpha = False  # Disable alpha if not needed

            except Exception as e:
                if log_level == "DEBUG":
                    print(f"Could not load image {abs_path}: {e}")
                return None
            tex = nodes.new(type="ShaderNodeTexImage")
            tex.image = img
            tex.label = label
            tex.location = location

            # **UNITY OPTIMIZATION: Set interpolation for better quality**
            tex.interpolation = "Linear"  # Better quality than "Closest"

            # set colorspace
            try:
                tex.image.colorspace_settings.name = colorspace
            except Exception:
                pass
            return tex

        # BASE COLOR (sRGB)
        base_tex_node = _create_image_node(
            base_texture_path, "BaseColor", colorspace="sRGB", location=(-600, 300)
        )
        if base_tex_node:
            links.new(base_tex_node.outputs["Color"], principled.inputs["Base Color"])

        # NORMAL
        if sidecars.get("normal"):
            n_tex = _create_image_node(
                sidecars["normal"], "Normal", colorspace="Non-Color", location=(-600, 0)
            )
            if n_tex:
                normal_map = nodes.new(type="ShaderNodeNormalMap")
                normal_map.location = (-300, 0)
                links.new(n_tex.outputs["Color"], normal_map.inputs["Color"])
                links.new(normal_map.outputs["Normal"], principled.inputs["Normal"])

        # ROUGHNESS
        if sidecars.get("roughness"):
            r_tex = _create_image_node(
                sidecars["roughness"],
                "Roughness",
                colorspace="Non-Color",
                location=(-600, -150),
            )
            if r_tex:
                links.new(r_tex.outputs["Color"], principled.inputs["Roughness"])

        # METALLIC
        if sidecars.get("metallic"):
            m_tex = _create_image_node(
                sidecars["metallic"],
                "Metallic",
                colorspace="Non-Color",
                location=(-600, -300),
            )
            if m_tex:
                links.new(m_tex.outputs["Color"], principled.inputs["Metallic"])

        # AO -> multiply with base color (if both present)
        if sidecars.get("ao") and base_tex_node:
            ao_tex = _create_image_node(
                sidecars["ao"], "AO", colorspace="Non-Color", location=(-600, 450)
            )
            if ao_tex:
                mix = nodes.new(type="ShaderNodeMixRGB")
                mix.blend_type = "MULTIPLY"
                mix.inputs["Fac"].default_value = 1.0
                mix.location = (-300, 250)
                # connect base -> mix Color1, AO -> Color2
                links.new(base_tex_node.outputs["Color"], mix.inputs["Color1"])
                links.new(ao_tex.outputs["Color"], mix.inputs["Color2"])
                links.new(mix.outputs["Color"], principled.inputs["Base Color"])

        # EMISSION (optional)
        if sidecars.get("emission"):
            e_tex = _create_image_node(
                sidecars["emission"],
                "Emission",
                colorspace="sRGB",
                location=(-600, 600),
            )
            if e_tex:
                emit_node = nodes.new(type="ShaderNodeEmission")
                emit_node.location = (-300, 600)
                links.new(e_tex.outputs["Color"], emit_node.inputs["Color"])
                # combine emission and principled via Add Shader
                add = nodes.new(type="ShaderNodeAddShader")
                add.location = (200, 100)
                links.new(principled.outputs["BSDF"], add.inputs[0])
                links.new(emit_node.outputs["Emission"], add.inputs[1])
                links.new(add.outputs["Shader"], output_node.inputs["Surface"])
        else:
            # standard connection
            links.new(principled.outputs["BSDF"], output_node.inputs["Surface"])

        # **UNITY OPTIMIZATION: Set material properties for Unity export**
        mat.use_fake_user = True  # Prevent material deletion
        mat.blend_method = "OPAQUE"  # Unity standard blend method

        # **SOF2 SHADER SUPPORT: Handle cull disable (two-sided materials)**
        if (
            loaded_shader_data
            and key in loaded_shader_data
            and isinstance(loaded_shader_data[key], dict)
            and "cull" in str(loaded_shader_data[key]).lower()
            and "disable" in str(loaded_shader_data[key]).lower()
        ):
            mat.use_backface_culling = False
            mat["unity_two_sided"] = True
            if log_level == "DEBUG":
                print(f"Material '{shader}' set to two-sided (cull disable)")

        # **UNITY OPTIMIZATION: Add custom properties for Unity**
        mat["unity_export_ready"] = True
        mat["shader_name"] = shader  # Store original shader name

        # done
        return mat

    def _configure_material_with_map(self, mat, map_value):
        """
        Configure a material with the given map value (texture path).
        This is a simplified version of the main material configuration.
        """
        if not map_value:
            return
        
        # Try to find the texture file
        def _try_find_file(name_candidate: str):
            if not name_candidate:
                return False, ""
            return SoF2Filesystem.FindFile(
                name_candidate, self.basepath, ["jpg", "png", "tga", "dds"]
            )
        
        success, abs_path = _try_find_file(map_value)
        if not success:
            print(f"Texture not found: {map_value}")
            mat.diffuse_color = (1, 0, 1, 1)  # Pink fallback
            return
        
        # Basic material setup with the found texture
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        
        # Clear existing nodes
        for node in nodes:
            nodes.remove(node)
        
        # Create basic nodes
        output_node = nodes.new(type='ShaderNodeOutputMaterial')
        output_node.location = (400, 0)
        
        principled = nodes.new(type='ShaderNodeBsdfPrincipled')
        principled.location = (0, 0)
        
        # Create image texture node
        image_node = nodes.new(type='ShaderNodeTexImage')
        image_node.location = (-400, 0)
        
        # Load the texture
        try:
            image = bpy.data.images.load(abs_path)
            image_node.image = image
        except Exception as e:
            print(f"Error loading texture {abs_path}: {e}")
            mat.diffuse_color = (1, 0, 1, 1)  # Pink fallback
            return
        
        # Connect nodes
        links.new(image_node.outputs['Color'], principled.inputs['Base Color'])
        links.new(principled.outputs['BSDF'], output_node.inputs['Surface'])
        
        print(f"Configured material with texture: {map_value}")
