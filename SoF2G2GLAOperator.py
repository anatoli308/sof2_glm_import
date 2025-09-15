import bpy  # pyright: ignore[reportMissingImports]

from .SoF2G2Constants import SkeletonFixes
from . import SoF2G2Scene
from . import SoF2G2GLA
from . import SoF2Filesystem


class GLAImport(bpy.types.Operator):
    """Import GLA Operator."""

    bl_idname = "import_scene.gla"
    bl_label = "Import SoF2 Ghoul 2 Skeleton (.gla)"
    bl_description = "Imports a Ghoul 2 skeleton (.gla) and optionally the animation."
    bl_options = {"REGISTER", "UNDO"}

    filename_ext = "*.gla"  # I believe this limits the shown files.

    # properties
    filepath: bpy.props.StringProperty(  # pyright: ignore [reportInvalidTypeForm]
        name="File Path",
        description="The .gla file to import",
        maxlen=1024,
        default="",
        subtype="FILE_PATH",
    )
    basepath: bpy.props.StringProperty(  # pyright: ignore [reportInvalidTypeForm]
        name="Base Path",
        description="The base folder relative to which paths should be interpreted. Leave empty to let the importer guess (needs /GameData/ in filepath).",
        default="D:/sof2/base/",
    )
    scale: bpy.props.FloatProperty(  # pyright: ignore [reportInvalidTypeForm]
        name="Scale",
        description="Scale to apply to the imported model.",
        default=10,
        min=0,
        max=1000,
        subtype="PERCENTAGE",
    )
    skeletonFixes: bpy.props.EnumProperty(  # pyright: ignore [reportInvalidTypeForm, reportArgumentType]
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
    )
    loadAnimations: bpy.props.EnumProperty(  # pyright: ignore [reportInvalidTypeForm, reportArgumentType]
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
    )
    startFrame: bpy.props.IntProperty(  # pyright: ignore [reportInvalidTypeForm]
        name="Start frame",
        description="If only a range of frames of the animation is to be imported, this is the first.",
        min=0,
    )
    numFrames: bpy.props.IntProperty(  # pyright: ignore [reportInvalidTypeForm]
        name="number of frames",
        description="If only a range of frames of the animation is to be imported, this is the total number of frames to import",
        min=1,
    )

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


