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
        "SoF2G2NPCLoader",
        "SoF2G2Panels",
        "SoF2G2NPCPanel",
        "SoF2G2GLMLoader",
        "SoF2G2GLAOperator",
    ],
    [".SoF2G2Constants"],
)  # nopep8

import os  # noqa: E402
import bpy  # noqa: E402  # pyright: ignore[reportMissingImports]

from .SoF2G2Constants import SkeletonFixes  # noqa: E402

log_level = os.getenv("LOG_LEVEL", "INFO")

from . import SoF2G2GLA  # noqa: E402, F811
from . import SoF2G2NPCLoader  # noqa: E402
from . import SoF2G2WeaponLoader  # noqa: E402
from . import SoF2G2NPCPanel  # noqa: E402
from . import SoF2G2GLMLoader  # noqa: E402
from .SoF2G2GLAOperator import GLAImport  # noqa: E402


class GLMImport(bpy.types.Operator):
    """Import GLM Operator."""

    bl_idname = "import_scene.glm"
    bl_label = "Import SoF2 Ghoul 2 Model (.glm)"
    bl_options = {"REGISTER", "UNDO"}

    # statt EnumProperty → Search + Auswahl
    npc_search: bpy.props.StringProperty(name="Search your .npc file", default="")
    npc_selected: bpy.props.StringProperty(name="Selected NPC", default="")

    weapon_search: bpy.props.StringProperty(name="Search your .weapon file", default="")
    weapon_selected: bpy.props.StringProperty(name="Selected Weapon", default="")

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

    # load NPCs or Weapons
    loadWeapons: bpy.props.BoolProperty(
        name="Load Weapons",
        description="When check you we load the Weapons instead of NPC",
        default=False,
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

    def handle_load_glm_file(self):
        return SoF2G2GLMLoader.handle_load_glm_file(self)

    def handle_load_npc_file(self):
        return SoF2G2NPCLoader.handle_load_npc_file(self)

    def handle_load_weapon_file(self):
        return SoF2G2WeaponLoader.handle_load_weapon_file(self)

    def draw(self, context):
        SoF2G2NPCPanel.draw_glm_import_panel(self.layout, self)

    def execute(self, context):
        if not self.basepath:
            self.report({"ERROR"}, "No Base Path selected!")
            return {"CANCELLED"}

        if self.loadWeapons:
            return self.handle_load_weapon_file()
        else:
            key = self.npc_selected
            if not key:
                return self.handle_load_glm_file()
            else:
                return self.handle_load_npc_file()

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


class GLM_OT_select_npc(bpy.types.Operator):
    bl_idname = "glm.select_npc"
    bl_label = "Select NPC"
    bl_description = "Wähle diesen NPC aus"

    npc_id: bpy.props.StringProperty()

    def execute(self, context):
        op = context.active_operator
        if hasattr(op, "npc_selected"):
            op.npc_selected = self.npc_id
            self.report({"INFO"}, f"NPC gewählt: {self.npc_id}")
        return {"FINISHED"}

class GLM_OT_select_weapon(bpy.types.Operator):
    bl_idname = "glm.select_weapon"
    bl_label = "Select Weapon"
    bl_description = "Wähle diese Waffe aus"

    weapon_id: bpy.props.StringProperty()

    def execute(self, context):
        op = context.active_operator
        if hasattr(op, "weapon_selected"):
            op.weapon_selected = self.weapon_id
            self.report({"INFO"}, f"Weapon gewählt: {self.weapon_id}")
        return {"FINISHED"}

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
    bpy.utils.register_class(GLM_OT_select_npc)
    bpy.utils.register_class(GLM_OT_select_weapon)
    
    bpy.utils.register_class(GLAImport)

    bpy.utils.register_class(ObjectAddG2Properties)
    bpy.utils.register_class(ObjectRemoveG2Properties)

    bpy.types.TOPBAR_MT_file_import.append(menu_func_import_glm)


def unregister():
    bpy.utils.unregister_class(GLMImport)
    bpy.utils.unregister_class(GLM_OT_select_npc)
    bpy.utils.unregister_class(GLM_OT_select_weapon)
    
    bpy.utils.unregister_class(GLAImport)

    bpy.utils.unregister_class(ObjectAddG2Properties)
    bpy.utils.unregister_class(ObjectRemoveG2Properties)

    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import_glm)
