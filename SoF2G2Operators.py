from .mod_reload import reload_modules

reload_modules(
    locals(),
    __package__,
    [
        "SoF2G2DataCache",
        "SoF2Filesystem",
        "SoF2G2DataParser",
        "SoF2G2Operators",
        "SoF2G2Scene",
        "SoF2G2GLA",
    ],
    [".SoF2G2Constants"],
)  # nopep8

import os  # noqa: E402
import bpy  # noqa: E402  # pyright: ignore[reportMissingImports]
from typing import cast  # noqa: E402

from .SoF2G2Constants import SkeletonFixes  # noqa: E402

log_level = os.getenv("LOG_LEVEL", "INFO")

from .SoF2G2DataCache import get_npcs_folder_data_cached  # noqa: E402
from . import SoF2G2DataCache as DataCache  # noqa: E402
from . import SoF2G2Scene  # noqa: E402
from . import SoF2G2GLA  # noqa: E402, F811
from . import SoF2Filesystem  # noqa: E402


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
    for npc_filename, npc_content in npcs_data.items():
        char_templates = npc_content.get("CharacterTemplate", [])
        if not isinstance(char_templates, list):
            char_templates = [char_templates]

        for char_template in char_templates:
            if char_template.get("Name") == key:
                return {
                    "char_template": char_template,
                    "npc_filename": npc_filename,
                    "group_info": npc_content.get("GroupInfo", {}),
                }
    return None


def get_npcs_items(self, context):
    """Wrapper function for EnumProperty that returns just the items list"""
    return DataCache.get_npc_enum_items(self.basepath)


class GLMImport(bpy.types.Operator):
    """Import GLM Operator."""

    bl_idname = "import_scene.glm"
    bl_label = "Import SoF2 Ghoul 2 Model (.glm)"
    bl_options = {"REGISTER", "UNDO"}

    npc_files: bpy.props.EnumProperty(
        name="NPC", description="All .npc files", items=get_npcs_items
    )  # pyright: ignore [reportInvalidTypeForm]

    # Explorer zeigt Datei-Auswahl an (z.B. glm)
    filepath: bpy.props.StringProperty(
        name="File Path",
        description="Select any .glm file in your SoF2 base folder",
        default="",
        subtype="FILE_PATH",
    )
    # tatsächlicher Basepath (nur Ordner)
    basepath: bpy.props.StringProperty(
        name="Base Path",
        description="Extracted base path from chosen file",
        default="",
        subtype="DIR_PATH",
    )

    scale: bpy.props.FloatProperty(
        name="Scale",
        description="Scale to apply to the imported model.",
        default=10,
        min=0,
        max=1000,
        subtype="PERCENTAGE",
    )

    skeletonFixes: bpy.props.EnumProperty(
        name="skeleton changes",
        description="You can select a preset for automatic skeleton changes which result in a nicer imported skeleton.",
        default="NONE",
        items=[
            (
                SkeletonFixes.NONE.value,
                "None",
                "Don't change the skeleton in any way.",
                0,
            ),
            (
                SkeletonFixes.JKA_HUMANOID.value,
                "Jedi Academy _humanoid",
                "Fixes for the default humanoid Jedi Academy skeleton",
                1,
            ),
        ],
    )  # pyright: ignore [reportInvalidTypeForm, reportArgumentType]

    loadAnimations: bpy.props.EnumProperty(
        name="animations",
        description="Whether to import all animations, some animations or only a range from the .gla. (Importing huge animations takes forever.)",
        default="NONE",
        items=[
            (
                SoF2G2GLA.AnimationLoadMode.NONE.value,
                "None",
                "Don't import animations.",
                0,
            ),
            (SoF2G2GLA.AnimationLoadMode.ALL.value, "All", "Import all animations", 1),
            (
                SoF2G2GLA.AnimationLoadMode.RANGE.value,
                "Range",
                "Import a certain range of frames",
                2,
            ),
        ],
    )  # pyright: ignore [reportInvalidTypeForm, reportArgumentType]

    startFrame: bpy.props.IntProperty(
        name="Start frame",
        description="If only a range of frames of the animation is to be imported, this is the first.",
        min=0,
    )  # pyright: ignore [reportInvalidTypeForm]

    numFrames: bpy.props.IntProperty(
        name="number of frames",
        description="If only a range of frames of the animation is to be imported, this is the total number of frames to import",
        min=1,
    )  # pyright: ignore [reportInvalidTypeForm]

    def draw(self, context):
        layout = self.layout
        layout.label(text="Bitte wähle dein SoF2 Basepath:", icon="FILE_FOLDER")
        layout.prop(self, "basepath")  # zeigt den aktuellen Ordner

        if self.basepath and os.path.normpath(self.basepath).endswith(
            os.path.normpath("/base")
        ):
            box = layout.box()
            box.label(text="Basepath OK!", icon="CHECKMARK")
            layout.prop(self, "npc_files")
            layout.prop(self, "scale")
            layout.prop(self, "skeletonFixes")
            layout.prop(self, "loadAnimations")
            layout.prop(self, "startFrame")
            layout.prop(self, "numFrames")
        else:
            row = layout.row()
            row.alert = True
            row.label(text="Base folder not found!", icon="ERROR")

    def execute(self, context):
        if not self.basepath:
            self.report({"ERROR"}, "No Base Path selected!")
            return {"CANCELLED"}

        key = self.npc_files
        if not key:
            self.report({"ERROR"}, "No NPC selected!")
            return {"CANCELLED"}

        _, npcs_files_data = get_npcs_folder_data_cached(self.basepath)

        # Find the character template for the selected NPC
        # {"char_template": char_template, "npc_filename": npc_filename, "group_info": npc_content.get("GroupInfo", {})}
        character_template = find_character_template_by_key(npcs_files_data, key)

        if character_template:
            print(f"Found character template for {key}:")
            character_model = character_template.get("char_template", {}).get(
                "Model", None
            )

            skin_files = character_template.get("char_template", {}).get("Skin", {})
            if isinstance(skin_files, dict):
                print("skin_files ist ein dict")
                skin_file_data = skin_files
            elif isinstance(skin_files, list):
                print("skin_files ist eine Liste")
                # TODO make user pick one for now we just choose first
                skin_file_data = skin_files[0] if skin_files else None
            else:
                print("skin_files ist etwas anderes:", type(skin_files))
                return {"CANCELLED"}

            _, skin_data = DataCache.get_skins(
                getattr(self, "basepath", ""), character_model
            )

            selected_skin_data = find_skin_data_by_file_value(
                skin_data, skin_file_data.get("File")
            )
            if not selected_skin_data:
                self.report({"ERROR"}, "No NPC selected!")
                return {"CANCELLED"}

            print(f"Loading Model: {character_model}")

            # de-percentagionise scale
            scale = self.scale / 100

            # load GLM
            scene = SoF2G2Scene.Scene(self.basepath)
            success, message = scene.loadFromGLM(character_model, selected_skin_data)
            if not success:
                self.report({"ERROR"}, message)
                return {"FINISHED"}

            glafile = scene.getRequestedGLA()
            loadAnimations = SoF2G2GLA.AnimationLoadMode[self.loadAnimations]
            success, message = scene.loadFromGLA(
                glafile,
                loadAnimations,
                cast(int, self.startFrame),
                cast(int, self.numFrames),
            )
            if not success:
                self.report({"ERROR"}, message)
                return {"FINISHED"}

            guessTextures = True  # Anatoli - True for now dont need that in SoF2 idk what it does right now
            success, message = scene.saveToBlender(
                scale,
                selected_skin_data,
                guessTextures,
                loadAnimations != SoF2G2GLA.AnimationLoadMode.NONE,
                SkeletonFixes[self.skeletonFixes],
            )
            if not success:
                self.report({"ERROR"}, message)
            return {"FINISHED"}

        else:
            print(f"No character template found for key: {key}")
            return {"CANCELLED"}

    def invoke(self, context, event):
        wm = context.window_manager
        wm.fileselect_add(self)  # File-Explorer öffnen
        return {"RUNNING_MODAL"}

    def check(self, context):
        """called automatically when props update"""
        if self.filepath:
            # bei Datei-Auswahl basepath extrahieren
            self.basepath = os.path.dirname(self.filepath)
        return True


class GLAImport(bpy.types.Operator):
    """Import GLA Operator."""

    bl_idname = "import_scene.gla"
    bl_label = "Import SoF2 Ghoul 2 Skeleton (.gla)"
    bl_description = "Imports a Ghoul 2 skeleton (.gla) and optionally the animation."
    bl_options = {"REGISTER", "UNDO"}

    filename_ext = "*.gla"  # I believe this limits the shown files.

    # properties
    filepath: bpy.props.StringProperty(
        name="File Path",
        description="The .gla file to import",
        maxlen=1024,
        default="",
        subtype="FILE_PATH",
    )  # pyright: ignore [reportInvalidTypeForm]
    basepath: bpy.props.StringProperty(
        name="Base Path",
        description="The base folder relative to which paths should be interpreted. Leave empty to let the importer guess (needs /GameData/ in filepath).",
        default="D:/sof2/base/",
    )  # pyright: ignore [reportInvalidTypeForm]
    scale: bpy.props.FloatProperty(
        name="Scale",
        description="Scale to apply to the imported model.",
        default=10,
        min=0,
        max=1000,
        subtype="PERCENTAGE",
    )  # pyright: ignore [reportInvalidTypeForm]
    skeletonFixes: bpy.props.EnumProperty(
        name="skeleton changes",
        description="You can select a preset for automatic skeleton changes which result in a nicer imported skeleton.",
        default="NONE",
        items=[
            (
                SkeletonFixes.NONE.value,
                "None",
                "Don't change the skeleton in any way.",
                0,
            ),
            (
                SkeletonFixes.JKA_HUMANOID.value,
                "Jedi Academy _humanoid",
                "Fixes for the default humanoid Jedi Academy skeleton",
                1,
            ),
        ],
    )  # pyright: ignore [reportInvalidTypeForm, reportArgumentType]
    loadAnimations: bpy.props.EnumProperty(
        name="animations",
        description="Whether to import all animations, some animations or only a range from the .gla. (Importing huge animations takes forever.)",
        default="NONE",
        items=[
            (
                SoF2G2GLA.AnimationLoadMode.NONE.value,
                "None",
                "Don't import animations.",
                0,
            ),
            (SoF2G2GLA.AnimationLoadMode.ALL.value, "All", "Import all animations", 1),
            (
                SoF2G2GLA.AnimationLoadMode.RANGE.value,
                "Range",
                "Import a certain range of frames",
                2,
            ),
        ],
    )  # pyright: ignore [reportInvalidTypeForm, reportArgumentType]
    startFrame: bpy.props.IntProperty(
        name="Start frame",
        description="If only a range of frames of the animation is to be imported, this is the first.",
        min=0,
    )  # pyright: ignore [reportInvalidTypeForm]
    numFrames: bpy.props.IntProperty(
        name="number of frames",
        description="If only a range of frames of the animation is to be imported, this is the total number of frames to import",
        min=1,
    )  # pyright: ignore [reportInvalidTypeForm]

    def execute(self, context):
        print("\n== GLA Import ==\n")
        # de-percentagionise scale
        scale = self.scale / 100
        # initialize paths
        basepath, filepath = self.basepath, self.filepath  # GetPaths(
        if (
            self.basepath != ""
            and SoF2Filesystem.RemoveExtension(self.filepath) == filepath
        ):
            self.report({"ERROR"}, "Invalid Base Path")
            return {"FINISHED"}
        # load GLA
        scene = SoF2G2Scene.Scene(basepath)
        loadAnimations = SoF2G2GLA.AnimationLoadMode[self.loadAnimations]
        success, message = scene.loadFromGLA(
            filepath, loadAnimations, self.startFrame, self.numFrames
        )
        if not success:
            self.report({"ERROR"}, message)
            return {"FINISHED"}
        # output to blender
        success, message = scene.saveToBlender(
            scale,
            "",
            False,
            loadAnimations != SoF2G2GLA.AnimationLoadMode.NONE,
            SkeletonFixes[self.skeletonFixes],
        )
        if not success:
            self.report({"ERROR"}, message)
        return {"FINISHED"}

    def invoke(self, context, event):
        wm = context.window_manager
        wm.fileselect_add(self)
        return {"RUNNING_MODAL"}


class ObjectAddG2Properties(bpy.types.Operator):
    bl_idname = "object.add_g2_properties"
    bl_label = "Add G2 properties"
    bl_description = "Adds Ghoul 2 properties"

    @classmethod
    def poll(cls, context):
        return (
            context.active_object
            and context.active_object.type in ["MESH", "ARMATURE"]
            or False
        )

    def execute(self, context):
        obj = context.active_object
        if obj.type == "MESH":
            # don't overwrite those that already exist
            if "g2_prop_off" not in obj:
                obj.g2_prop_off = False  # pyright: ignore [reportAttributeAccessIssue]
            if "g2_prop_tag" not in obj:
                obj.g2_prop_tag = False  # pyright: ignore [reportAttributeAccessIssue]
            if "g2_prop_name" not in obj:
                obj.g2_prop_name = ""  # pyright: ignore [reportAttributeAccessIssue]
            if "g2_prop_shader" not in obj:
                obj.g2_prop_shader = ""  # pyright: ignore [reportAttributeAccessIssue]
        else:
            assert obj.type == "ARMATURE"
            if "g2_prop_scale" not in obj:
                obj.g2_prop_scale = 100  # pyright: ignore [reportAttributeAccessIssue]
        return {"FINISHED"}


class ObjectRemoveG2Properties(bpy.types.Operator):
    bl_idname = "object.remove_g2_properties"
    bl_label = "Remove G2 properties"
    bl_description = "Removes Ghoul 2 properties"

    @classmethod
    def poll(cls, context):
        return (
            context.active_object
            and context.active_object.type in ["MESH", "ARMATURE"]
            or False
        )

    def execute(self, context):
        obj = context.active_object
        if obj.type == "MESH":
            bpy.types.Object.__delitem__(obj, "g2_prop_off")
            bpy.types.Object.__delitem__(obj, "g2_prop_tag")
            bpy.types.Object.__delitem__(obj, "g2_prop_name")
            bpy.types.Object.__delitem__(obj, "g2_prop_shader")
        else:
            assert obj.type == "ARMATURE"
            bpy.types.Object.__delitem__(obj, "g2_prop_scale")
        return {"FINISHED"}


# menu button callback functions
def menu_func_import_glm(self, context):
    self.layout.operator(GLMImport.bl_idname, text="SoF2 Ghoul 2 model (.glm)")


# menu button init/destroy
def register():
    bpy.utils.register_class(GLMImport)

    bpy.utils.register_class(ObjectAddG2Properties)
    bpy.utils.register_class(ObjectRemoveG2Properties)

    bpy.types.TOPBAR_MT_file_import.append(menu_func_import_glm)


def unregister():
    bpy.utils.unregister_class(GLMImport)

    bpy.utils.unregister_class(ObjectAddG2Properties)
    bpy.utils.unregister_class(ObjectRemoveG2Properties)

    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import_glm)
