from .mod_reload import reload_modules

reload_modules(
    locals(),
    __package__,
    ["", "SoF2G2Constants", "SoF2G2Math", "MrwProfiler"],
    [".casts", ".error_types"],
)  # nopep8
import os  # noqa: E402
from . import SoF2G2Constants  # noqa: E402
from . import SoF2G2Math  # noqa: E402
from . import MrwProfiler  # noqa: E402
from .casts import (  # noqa: E402
    optional_cast,
    downcast,
    bpy_generic_cast,
    matrix_getter_cast,
    matrix_overload_cast,
    vector_getter_cast,
)
from .error_types import ErrorMessage, NoError, ensureListIsGapless  # noqa: E402

from typing import BinaryIO, Dict, List, Optional, Tuple  # noqa: E402
from enum import Enum  # noqa: E402
import struct  # noqa: E402
import bpy  # noqa: E402  # pyright: ignore[reportMissingImports]
import mathutils  # noqa: E402  # pyright: ignore[reportMissingImports]

log_level = os.getenv("LOG_LEVEL", "INFO")

PROFILE = False
# show progress & remaining time every 30 seconds.
PROGRESS_UPDATE_INTERVAL = 30

def decode(bs: bytes) -> str:
    end = bs.find(b"\0")  # find null termination
    if end == -1:  # if none exists, there is no end.
        return bs.decode()
    return bs[:end].decode()  # otherwise cut it off at end


def readString(file: BinaryIO) -> str:
    return decode(struct.unpack("64s", file.read(SoF2G2Constants.MAX_QPATH))[0])


class MdxaHeader:
    def __init__(self):
        self.name = ""
        self.scale = 1  # does not seem to be used by Jedi Academy anyway - or is it? I need it in import!
        self.numFrames = -1
        self.ofsFrames = -1
        self.numBones = -1
        self.ofsCompBonePool = -1
        # this is also MdxaSkelOffsets.baseOffset + MdxaSkelOffsets.boneOffsets[0] - probably a historic leftover
        self.ofsSkel = -1
        self.ofsEnd = -1

    def loadFromFile(self, file: BinaryIO) -> Tuple[bool, ErrorMessage]:
        # check ident
        (ident,) = struct.unpack("4s", file.read(4))
        if ident != SoF2G2Constants.GLA_IDENT:
            print(
                "File does not start with ",
                SoF2G2Constants.GLA_IDENT,
                " but ",
                ident,
                " - no GLA!",
            )
            return False, ErrorMessage("Is no GLA file, incorrect file identifier!")
        (version,) = struct.unpack("i", file.read(4))
        if version != SoF2G2Constants.GLA_VERSION:
            return False, ErrorMessage(
                f"Wrong gla file version! {version} should be {SoF2G2Constants.GLA_VERSION}"
            )
        self.name = readString(file)
        (
            self.scale,
            self.numFrames,
            self.ofsFrames,
            self.numBones,
            self.ofsCompBonePool,
            self.ofsSkel,
            self.ofsEnd,
        ) = struct.unpack("f6i", file.read(7 * 4))
        print("Scale: {:.3f}".format(self.scale))
        return True, NoError

    def saveToFile(self, file: BinaryIO) -> None:
        file.write(
            struct.pack(
                "4si64sf6i",
                SoF2G2Constants.GLA_IDENT,
                SoF2G2Constants.GLA_VERSION,
                self.name.encode(),
                self.scale,
                self.numFrames,
                self.ofsFrames,
                self.numBones,
                self.ofsCompBonePool,
                self.ofsSkel,
                self.ofsEnd,
            )
        )


class MdxaBoneOffsets:
    def __init__(self):
        self.baseOffset: int = 2 * 4 + 64 + 4 * 7  # sizeof header
        self.boneOffsets: List[int] = []

    # fail-safe (except for exceptions)
    def loadFromFile(self, file: BinaryIO, numBones: int):
        assert self.baseOffset == file.tell()
        for i in range(numBones):
            self.boneOffsets.append(struct.unpack("i", file.read(4))[0])

    def saveToFile(self, file: BinaryIO) -> None:
        assert file.tell() == self.baseOffset  # must be after header
        for offset in self.boneOffsets:
            file.write(struct.pack("i", offset))


# originally called MdxaSkel_t, but I find that name misleading
class MdxaBone:
    def __init__(self):
        self.name = ""
        self.flags: int = 0
        self.parent: int = -1
        self.basePoseMat = SoF2G2Math.Matrix()
        self.basePoseMatInv = SoF2G2Math.Matrix()
        self.numChildren = 0
        self.children: List[int] = []
        # not saved, filled by loadBonesFromFile() and when loaded from blender
        self.index: int = -1

    def getSize(self) -> int:
        return struct.calcsize("64sIi12f12fi{}i".format(self.numChildren))

    def loadFromFile(self, file: BinaryIO) -> None:
        self.name = readString(file)
        self.flags, self.parent = struct.unpack("Ii", file.read(2 * 4))
        self.basePoseMat.loadFromFile(file)
        self.basePoseMatInv.loadFromFile(file)
        (self.numChildren,) = struct.unpack("i", file.read(4))
        for _ in range(self.numChildren):
            self.children.append(struct.unpack("i", file.read(4))[0])

    def saveToFile(self, file: BinaryIO) -> None:
        file.write(struct.pack("64sIi", self.name.encode(), self.flags, self.parent))
        self.basePoseMat.saveToFile(file)
        self.basePoseMatInv.saveToFile(file)
        file.write(struct.pack("i", self.numChildren))
        assert len(self.children) == self.numChildren
        for child in self.children:
            file.write(struct.pack("i", child))

    def loadFromBlender(
        self,
        editbone: bpy.types.EditBone,
        boneIndicesByName: Dict[str, int],
        bones: List["MdxaBone"],
        objLocalMat: mathutils.Matrix,
    ) -> None:
        # set name
        self.name = editbone.name

        # add index to dictionary
        boneIndicesByName[self.name] = self.index

        # parent is -1 by default - change if there is one.
        if editbone.parent is not None:
            self.parent = boneIndicesByName[editbone.parent.name]
            parent = bones[self.parent]
            parent.numChildren += 1
            parent.children.append(self.index)

        # save (inverted) base pose matrix
        mat = matrix_overload_cast(objLocalMat @ matrix_getter_cast(editbone.matrix))
        # must not be used for blender-internal calculations anymore!
        SoF2G2Math.BlenderBoneRotToGLA(mat)
        matInv = mat.inverted()
        self.basePoseMat.fromBlender(mat)
        self.basePoseMatInv.fromBlender(matInv)

    # blenderBonesSoFar is a dictionary of boneIndex -> BlenderBone
    # allBones is the list of all MdxaBones
    # use it to set up hierarchy and add yourself once done.
    def saveToBlender(
        self,
        armature: bpy.types.Armature,
        blenderBonesSoFar: Dict[int, bpy.types.EditBone],
        allBones: List["MdxaBone"],
        skeletonFixes: SoF2G2Constants.SkeletonFixes,
    ) -> None:
        # create bone
        bone = armature.edit_bones.new(self.name)

        # set position
        mat = self.basePoseMat.toBlender()
        pos = mathutils.Vector(mat.translation)
        bone.head = pos
        # head is offset a bit.
        # X points towards next bone.
        x_axis = mathutils.Vector(mat.col[0][0:3])  # pyright: ignore [reportArgumentType]  # vector supports slices
        bone.tail = pos + x_axis * SoF2G2Constants.BONELENGTH
        # set roll
        y_axis = -mathutils.Vector(mat.col[1][0:3])  # pyright: ignore [reportArgumentType]  # vector supports slices
        bone.align_roll(y_axis)

        # set parent, if any, keeping in mind it might be overwritten
        parentIndex = self.parent
        parentChanges = SoF2G2Constants.PARENT_CHANGES[skeletonFixes]
        if self.index in parentChanges:
            parentIndex = parentChanges[self.index]
        if parentIndex != -1:
            blenderParent = blenderBonesSoFar[parentIndex]
            bone.parent = blenderParent

            # how many children does the parent have?
            numParentChildren = allBones[parentIndex].numChildren
            # we actually need to take into account the hierarchy changes.
            # so for any bone that used to have this parent but does not anymore, remove one
            for mdxaBone in allBones:
                # if a bone gets its parent changed, and it used to be "my" parent, my parent has one child less.
                if mdxaBone.parent == parentIndex and mdxaBone.index in parentChanges:
                    numParentChildren -= 1
            assert numParentChildren >= 0
            # and for any bone that got this as the parent, add one child.
            for _, newParentIndex in parentChanges.items():
                if newParentIndex == parentIndex:
                    numParentChildren += 1
            assert numParentChildren > 0  # at least this bone is child.

            # if this is the only child of its parent or has priority: Connect the parent to this.
            if (
                numParentChildren == 1
                or self.name in SoF2G2Constants.PRIORITY_BONES[skeletonFixes]
            ):
                # but only if that doesn't rotate the bone (much)
                # so calculate the directions...
                oldDir = vector_getter_cast(blenderParent.tail) - vector_getter_cast(
                    blenderParent.head
                )
                newDir = pos - blenderParent.head
                oldDir.normalize()
                newDir.normalize()
                dotProduct = oldDir.dot(newDir)
                # ... and compare them using the dot product, which is the cosine of the angle between two unit vectors
                if dotProduct > SoF2G2Constants.BONE_ANGLE_ERROR_MARGIN:
                    blenderParent.tail = pos
                    bone.use_connect = True

        # save to created bones
        blenderBonesSoFar[self.index] = bone


class MdxaSkel:
    def __init__(self):
        self.bones: List[MdxaBone] = []
        self.armature = None
        self.armatureObject = None

    def loadFromFile(self, file: BinaryIO, offsets: MdxaBoneOffsets):
        for i, offset in enumerate(offsets.boneOffsets):
            file.seek(offsets.baseOffset + offset)
            bone = MdxaBone()
            bone.loadFromFile(file)
            bone.index = i
            self.bones.append(bone)

    def saveToFile(self, file: BinaryIO, header: MdxaHeader):
        assert file.tell() == header.ofsSkel
        for bone in self.bones:
            bone.saveToFile(file)

    def fitsArmature(self, armature) -> Tuple[bool, ErrorMessage]:
        for bone in self.bones:
            if bone.name not in armature.bones:
                return False, ErrorMessage(
                    f"Bone {bone.name} not found in existing skeleton_root armature!"
                )
        return True, NoError

    def saveToBlender(
        self, scene_root: bpy.types.Object, skeletonFixes: SoF2G2Constants.SkeletonFixes
    ) -> Tuple[bool, ErrorMessage]:
        #  Creation
        # create armature
        self.armature = bpy.data.armatures.new("skeleton_root")
        # create object
        self.armature_object = bpy.data.objects.new("skeleton_root", self.armature)
        # set parent
        self.armature_object.parent = scene_root
        # link object to scene
        bpy.context.scene.collection.objects.link(self.armature_object)

        #  Set the armature as active and go to edit mode to add bones
        bpy.context.view_layer.objects.active = self.armature_object
        bpy.ops.object.mode_set(mode="EDIT")
        # list of indices of already created bones - only those bones with this as parent will be added
        createdBonesIndices = [-1]
        # bones yet to be created
        uncreatedBones = list(self.bones)
        parentChanges = SoF2G2Constants.PARENT_CHANGES[skeletonFixes]
        # Blender EditBones so far by index
        blenderEditBones: Dict[int, bpy.types.EditBone] = {}
        while len(uncreatedBones) > 0:
            # whether a new bone was created this time - if not, there's a hierarchy problem
            createdBone = False
            newUncreatedBones = []
            for bone in uncreatedBones:
                # only create those bones whose parent has already been created.
                if bone.index in parentChanges:
                    parent = parentChanges[bone.index]
                else:
                    parent = bone.parent
                if parent in createdBonesIndices:
                    bone.saveToBlender(
                        self.armature, blenderEditBones, self.bones, skeletonFixes
                    )
                    createdBonesIndices.append(bone.index)
                    createdBone = True
                else:
                    newUncreatedBones.append(bone)
            uncreatedBones = newUncreatedBones
            if not createdBone:
                bpy.ops.object.mode_set(mode="OBJECT")
                return False, ErrorMessage("gla has hierarchy problems!")
        # leave armature edit mode
        bpy.ops.object.mode_set(mode="OBJECT")
        return True, NoError


class MdxaFrame:
    def __init__(self):
        self.boneIndices: List[int] = []

    # returns the highest referenced index - not nice from a design standpoint but saves space, which is probably good.
    def loadFromFile(self, file, numBones):
        maxIndex = 0
        for i in range(numBones):
            # bone indices are only 3 bytes long - with 20k+ frames 25% less is quite a bit, reportedly.
            (index,) = struct.unpack("I", file.read(3) + b"\0")
            maxIndex = max(maxIndex, index)
            self.boneIndices.append(index)
        return maxIndex

    def saveToFile(self, file):
        for index in self.boneIndices:
            # only write the first 3 bytes of the packed number
            file.write(struct.pack("I", index)[:3])


class MdxaBonePool:
    def __init__(self):
        # during import, this is a list of CompBone objects
        # during exports, it's a list of 14-byte-objects (compressed bones)
        self.bones: List[SoF2G2Math.CompBone] | List[bytes] = []

    def loadFromFile(self, file, numCompBones):
        for i in range(numCompBones):
            compBone = SoF2G2Math.CompBone.loadFromFile(file)
            downcast(List[SoF2G2Math.CompBone], self.bones).append(compBone)

    def saveToFile(self, file: BinaryIO) -> None:
        for bone in downcast(List[bytes], self.bones):
            file.write(bone)


# Frames & Compressed Bone Pool
class MdxaAnimation:
    def __init__(self):
        self.frames: List[MdxaFrame] = []
        self.bonePool = MdxaBonePool()

    def loadFromFile(
        self, file: BinaryIO, header: MdxaHeader, startFrame: int, numFrames: int, data_frames_file: dict
    ) -> Tuple[bool, ErrorMessage]:
        # **NEW: Filter animations based on data_frames_file clips AND range parameters**
        animation_clips = []
        if data_frames_file:
            for xsi_path, frame_data in data_frames_file.items():
                if isinstance(frame_data, dict) and "startframe" in frame_data and "duration" in frame_data:
                    try:
                        clip_start_frame = int(frame_data["startframe"])
                        duration = int(frame_data["duration"])
                        fps = int(frame_data.get("fps", 20))  # Default 20 FPS
                        
                        # Calculate end frame
                        clip_end_frame = clip_start_frame + duration - 1
                        
                        # **NEW: Check if clip is within the specified range**
                        # If range is specified (numFrames != -1), only include clips that overlap with the range
                        if numFrames != -1:
                            range_start = startFrame
                            range_end = startFrame + numFrames - 1
                            
                            # Check if clip overlaps with the specified range
                            # Clip overlaps if: clip_start <= range_end AND clip_end >= range_start
                            if clip_start_frame > range_end or clip_end_frame < range_start:
                                #print(f"Skipping clip {os.path.basename(xsi_path)} (frames {clip_start_frame}-{clip_end_frame}) - outside range {range_start}-{range_end}")
                                continue
                        
                        # Create clip info
                        clip_name = os.path.splitext(os.path.basename(xsi_path))[0]
                        animation_clips.append({
                            "name": clip_name,
                            "start_frame": clip_start_frame,
                            "end_frame": clip_end_frame,
                            "duration": duration,
                            "fps": fps,
                            "xsi_path": xsi_path
                        })
                        print(f"Found animation clip: {clip_name} (frames {clip_start_frame}-{clip_end_frame})")
                    except (ValueError, KeyError) as e:
                        print(f"Warning: Could not parse frame data for {xsi_path}: {e}")
                        continue

        # If no clips defined, use original behavior
        if not animation_clips:
            print("No animation clips defined, loading all frames")
            return self._loadAllFrames(file, header, startFrame, numFrames)
        
        # **NEW: Load only the frames needed for the clips**
        print(f"Loading {len(animation_clips)} animation clips...")
        
        # Calculate frame range needed
        min_frame = min(clip["start_frame"] for clip in animation_clips)
        max_frame = max(clip["end_frame"] for clip in animation_clips)
        
        # Ensure we don't exceed available frames
        min_frame = max(0, min_frame)
        max_frame = min(header.numFrames - 1, max_frame)
        
        print(f"Loading frames {min_frame} to {max_frame} (total: {max_frame - min_frame + 1} frames)")
        
        # Store clip info for later use
        self.animation_clips = animation_clips
        
        # Load the filtered frame range
        return self._loadFrameRange(file, header, min_frame, max_frame - min_frame + 1)
    
    def _loadAllFrames(self, file: BinaryIO, header: MdxaHeader, startFrame: int, numFrames: int) -> Tuple[bool, ErrorMessage]:
        """Load all frames (original behavior)"""
        # read frames
        if file.tell() != header.ofsFrames:
            print(
                "Info: Frames in .gla not encountered when expected (at ",
                file.tell(),
                " instead of ",
                header.ofsFrames,
                "), seeking correct position. There could be a bug in the importer (bad) or the file could be unusual - but not necessarily wrong (no problem).",
                sep="",
            )
            file.seek(header.ofsFrames)

        # prepare frame start/end settings
        if numFrames == -1:
            assert startFrame == 0
            numFrames = header.numFrames
        else:
            print("Reading {} frames, starting at {}".format(numFrames, startFrame))
        if startFrame >= header.numFrames:
            print("Warning: StartFrame beyond existing frames, using last one")
            startFrame = header.numFrames - 1
            numFrames = 1
        if startFrame + numFrames > header.numFrames:
            print("Warning: Trying to import more frames than there are, fixing")
            numFrames = header.numFrames - startFrame
        # skip first startFrame frames
        # 1 = from current position
        file.seek(startFrame * 3 * header.numBones, 1)

        # read (remaining) frames
        maxIndex = -1
        for i in range(numFrames):
            frame = MdxaFrame()
            # loadFromFile returns highest read index
            maxIndex = max(maxIndex, frame.loadFromFile(file, header.numBones))
            self.frames.append(frame)

        # read compressed bone pool
        # see if we reached it yet
        curPos = file.tell()
        if curPos != header.ofsCompBonePool:
            # we're not yet there. If we're off by 0-3 bytes, it's because 32-bit-alignment is forced. Silently seek correct position. Otherwise: warn (and seek correct position, too)
            # if we're only importing some frames, we may or may not be there yet, of course, so don't warn.
            if curPos > header.ofsCompBonePool or (
                header.ofsCompBonePool > curPos + 3 and numFrames == header.numFrames
            ):
                print(
                    "Info: Bone Pool in .gla not encountered when expected (at ",
                    file.tell(),
                    " instead of ",
                    header.ofsCompBonePool,
                    "), seeking correct position. There could be a bug in the importer (bad) or the file could be unusual - but not necessarily wrong (no problem).",
                    sep="",
                )
            file.seek(header.ofsCompBonePool)
        # there's one more object than the highest index since those start at 0
        self.bonePool.loadFromFile(file, maxIndex + 1)

        # file should be over now, bone pool is usually the last thing. I'm not sure it has to be, but so far it has always been.
        if file.tell() != header.ofsEnd and numFrames == header.numFrames:
            print(
                "Info: .gla Bone Pool read but file not over yet - this likely indicates a problem."
            )
        return True, NoError
    
    def _loadFrameRange(self, file: BinaryIO, header: MdxaHeader, startFrame: int, numFrames: int) -> Tuple[bool, ErrorMessage]:
        """Load a specific range of frames"""
        # read frames
        if file.tell() != header.ofsFrames:
            print(
                "Info: Frames in .gla not encountered when expected (at ",
                file.tell(),
                " instead of ",
                header.ofsFrames,
                "), seeking correct position. There could be a bug in the importer (bad) or the file could be unusual - but not necessarily wrong (no problem).",
                sep="",
            )
            file.seek(header.ofsFrames)

        # prepare frame start/end settings
        print("Reading {} frames, starting at {}".format(numFrames, startFrame))
        if startFrame >= header.numFrames:
            print("Warning: StartFrame beyond existing frames, using last one")
            startFrame = header.numFrames - 1
            numFrames = 1
        if startFrame + numFrames > header.numFrames:
            print("Warning: Trying to import more frames than there are, fixing")
            numFrames = header.numFrames - startFrame
        # skip first startFrame frames
        # 1 = from current position
        file.seek(startFrame * 3 * header.numBones, 1)

        # read (remaining) frames
        maxIndex = -1
        for i in range(numFrames):
            frame = MdxaFrame()
            # loadFromFile returns highest read index
            maxIndex = max(maxIndex, frame.loadFromFile(file, header.numBones))
            self.frames.append(frame)

        # read compressed bone pool
        # see if we reached it yet
        curPos = file.tell()
        if curPos != header.ofsCompBonePool:
            # we're not yet there. If we're off by 0-3 bytes, it's because 32-bit-alignment is forced. Silently seek correct position. Otherwise: warn (and seek correct position, too)
            # if we're only importing some frames, we may or may not be there yet, of course, so don't warn.
            if curPos > header.ofsCompBonePool or (
                header.ofsCompBonePool > curPos + 3 and numFrames == header.numFrames
            ):
                print(
                    "Info: Bone Pool in .gla not encountered when expected (at ",
                    file.tell(),
                    " instead of ",
                    header.ofsCompBonePool,
                    "), seeking correct position. There could be a bug in the importer (bad) or the file could be unusual - but not necessarily wrong (no problem).",
                    sep="",
                )
            file.seek(header.ofsCompBonePool)
        # there's one more object than the highest index since those start at 0
        self.bonePool.loadFromFile(file, maxIndex + 1)

        # file should be over now, bone pool is usually the last thing. I'm not sure it has to be, but so far it has always been.
        if file.tell() != header.ofsEnd and numFrames == header.numFrames:
            print(
                "Info: .gla Bone Pool read but file not over yet - this likely indicates a problem."
            )
        return True, NoError

    def saveToFile(self, file: BinaryIO, header: MdxaHeader):
        assert file.tell() == header.ofsFrames
        for frame in self.frames:
            frame.saveToFile(file)
        # add padding if not 32 bit aligned (due to 3-byte-indices)
        if file.tell() % 4 != 0:
            # from_what = 1 -> from current position
            file.seek(4 - (file.tell() % 4), 1)
        assert file.tell() == header.ofsCompBonePool
        self.bonePool.saveToFile(file)

    def saveToBlender(
        self,
        skeleton: MdxaSkel,
        armature: bpy.types.Object,
        scale,
        data_frames_file: dict,
    ):
        import time

        startTime = time.time()
        print("Starting SAFE animation import with filtering...")
        
        # **PROFILING: Track detailed timing**
        import time
        timing_stats = {
            'mode_switches': 0,
            'keyframe_inserts': 0,
            'matrix_calculations': 0,
            'bone_transformations': 0
        }
        
        #   Bone Position Set Order
        # bones have to be set in hierarchical order - their position depends on their parent's absolute position, after all.
        # so this is the order in which bones have to be processed.
        hierarchyOrder: List[int] = []
        while len(hierarchyOrder) < len(skeleton.bones):
            # make sure we add something each frame (infinite loop otherwise)
            addedSomething = False
            # I could copy skeleton.bones for minor speed boost, imho not necessary.
            for bone in skeleton.bones:
                if bone.index in hierarchyOrder:
                    continue  # we already have this one.
                if bone.parent != -1 and bone.parent not in hierarchyOrder:
                    # we don't have the parent yet, so this cannot come yet.
                    continue
                hierarchyOrder.append(bone.index)
                addedSomething = True
            assert addedSomething
        # for going leaf to root

        #   Blender PoseBones list
        bones: List[bpy.types.PoseBone] = []
        for info in skeleton.bones:  # is ordered by index
            bones.append(armature.pose.bones[info.name])

        basePoses: List[mathutils.Matrix] = []
        for bone in skeleton.bones:
            basePoses.append(bone.basePoseMat.toBlender())

        #   Prepare animation
        scene = bpy.context.scene
        scene.frame_start = 0
        numFrames = len(self.frames)
        scene.frame_end = numFrames - 1

        if scale == 0:
            # if True:
            scale = 1
        else:
            scale = 1 / scale
        scaleMatrix = mathutils.Matrix(
            [[scale, 0, 0, 0], [0, scale, 0, 0], [0, 0, scale, 0], [0, 0, 0, 1]]
        )

        # **NEW: Show filtered animation info**
        if hasattr(self, 'animation_clips') and self.animation_clips:
            print(f"Using {len(self.animation_clips)} filtered animation clips:")
            for clip in self.animation_clips:
                print(f"  - {clip['name']}: frames {clip['start_frame']}-{clip['end_frame']} ({clip['duration']} frames)")
        else:
            print(f"No clips defined, using all {numFrames} frames")

        # **NEW: Create separate actions for each clip OR use original logic**
        if hasattr(self, 'animation_clips') and self.animation_clips:
            print("Creating separate Blender actions for each clip...")
            
            # Create animation data
            if not armature.animation_data:
                armature.animation_data_create()
            
            # Process each clip separately
            for clip in self.animation_clips:
                clip_name = clip["name"]
                start_frame = clip["start_frame"]
                end_frame = clip["end_frame"]
                duration = clip["duration"]
                
                print(f"Processing clip: {clip_name} (frames {start_frame}-{end_frame})")
                
                # Create action for this clip
                action = bpy.data.actions.new(name=clip_name)
                armature.animation_data.action = action
                
                # **Set action frame range directly (0 to duration) for Unity compatibility**
                action.frame_range = (0, duration) # TODO anatoli still not sure if unity need -1 or not 0based keep this for now
                
                #TODO default FPS Anatoli wechselbar machen??
                # **Set FPS for this specific clip**
                clip_fps = clip.get("fps", 20)  # Get FPS from clip data
                scene.render.fps = clip_fps
                
                # **Set scene frame range for this clip (0 to duration)**
                scene.frame_start = 0
                scene.frame_end = duration
                #print(f"  DEBUG: Set action frame range to 0-{duration} and FPS to {clip_fps} for clip {clip_name}")
                
                # Process frames for this clip
                for local_frame_num in range(duration):
                    global_frame_num = start_frame + local_frame_num
                    
                    if global_frame_num >= len(self.frames):
                        break
                        
                    frame = self.frames[global_frame_num]
                    
                    # Set current frame (local frame number 0 to duration-1)
                    scene.frame_set(local_frame_num)
                    
                    # Process bone transformations (same as original)
                    offsets: Dict[int, mathutils.Matrix] = {}
                    for index in hierarchyOrder:
                        mode_start = time.time()
                        bpy.ops.object.mode_set(mode="POSE", toggle=False)
                        timing_stats['mode_switches'] += time.time() - mode_start
                        
                        mdxaBone = skeleton.bones[index]
                        assert mdxaBone.index == index
                        bonePoolIndex = frame.boneIndices[index]
                        
                        # **PROFILING: Time matrix calculations**
                        matrix_start = time.time()
                        # get offset transformation matrix, relative to parent
                        offset = downcast(List[SoF2G2Math.CompBone], self.bonePool.bones)[
                            bonePoolIndex
                        ].matrix
                        # turn into absolute offset matrix (already is if this is top level bone)
                        if mdxaBone.parent != -1:
                            offset = matrix_overload_cast(offsets[mdxaBone.parent] @ offset)
                        # save this absolute offset for use by children
                        offsets[index] = offset
                        # calculate the actual position
                        transformation = matrix_overload_cast(offset @ basePoses[index])
                        # flip axes as required for blender bone
                        SoF2G2Math.GLABoneRotToBlender(transformation)
                        timing_stats['matrix_calculations'] += time.time() - matrix_start

                        # **PROFILING: Time bone transformations**
                        bone_start = time.time()
                        pose_bone = bones[index]
                        pose_bone.matrix = transformation
                        pose_bone.scale = [1, 1, 1]
                        timing_stats['bone_transformations'] += time.time() - bone_start
                        
                        # **PROFILING: Time keyframe inserts**
                        keyframe_start = time.time()
                        pose_bone.keyframe_insert("location")
                        pose_bone.keyframe_insert("rotation_quaternion")
                        timing_stats['keyframe_inserts'] += time.time() - keyframe_start
                        
                        # **PROFILING: Time mode switches**
                        mode_start = time.time()
                        bpy.ops.object.mode_set(mode="OBJECT", toggle=False)
                        timing_stats['mode_switches'] += time.time() - mode_start
                
                
                
                print(f"Created action: {clip_name} with {duration} frames")
            
            # **Restore original FPS and set scene back to first frame**
            scene.render.fps = 24  # Restore default FPS #TODO default FPS Anatoli wechselbar machen??
            scene.frame_current = 0
            
        else:
            # **FALLBACK: Original behavior for all frames**
            print("Processing all frames as single animation...")
            
            # show progress every 1000 steps, but at least 10 times)
            progressStep = min(1000, round(numFrames / 10))
            nextProgressDisplayTime = time.time() + PROGRESS_UPDATE_INTERVAL
            lastFrameNum = 0

            #   Export animation (ORIGINAL WORKING CODE)
            for frameNum, frame in enumerate(self.frames):
                # show progress bar / remaining time
                if time.time() >= nextProgressDisplayTime:
                    numProcessedFrames = frameNum - lastFrameNum
                    framesRemaining = numFrames - frameNum
                    # only take the frames since the last update into account since the speed varies.
                    # speed's roughly inversely proportional to the current frame number so I could use that to predict remaining time...
                    timeRemaining = (
                        PROGRESS_UPDATE_INTERVAL * framesRemaining / numProcessedFrames
                    )

                    print(
                        "Frame {}/{} - {:.2%} - remaining time: ca. {:.0f}m {:.0f}s".format(
                            frameNum,
                            numFrames,
                            frameNum / numFrames,
                            timeRemaining // 60,
                            timeRemaining % 60,
                        )
                    )

                    lastFrameNum = frameNum
                    nextProgressDisplayTime = time.time() + PROGRESS_UPDATE_INTERVAL

                # set current frame
                scene.frame_set(frameNum)

                # absolute offset matrices by bone index
                offsets: Dict[int, mathutils.Matrix] = {}
                for index in hierarchyOrder:
                    bpy.ops.object.mode_set(mode="POSE", toggle=False)
                    mdxaBone = skeleton.bones[index]
                    assert mdxaBone.index == index
                    bonePoolIndex = frame.boneIndices[index]
                    # get offset transformation matrix, relative to parent
                    offset = downcast(List[SoF2G2Math.CompBone], self.bonePool.bones)[
                        bonePoolIndex
                    ].matrix
                    # turn into absolute offset matrix (already is if this is top level bone)
                    if mdxaBone.parent != -1:
                        offset = matrix_overload_cast(offsets[mdxaBone.parent] @ offset)
                    # save this absolute offset for use by children
                    offsets[index] = offset
                    # calculate the actual position
                    transformation = matrix_overload_cast(offset @ basePoses[index])
                    # flip axes as required for blender bone
                    SoF2G2Math.GLABoneRotToBlender(transformation)

                    pose_bone = bones[index]
                    # pose_bone.matrix = transformation * scaleMatrix
                    pose_bone.matrix = transformation
                    # in the _humanoid face, the scale gets changed. that messes the re-export up. FIXME: understand why. Is there a problem?
                    pose_bone.scale = [1, 1, 1]
                    pose_bone.keyframe_insert("location")
                    pose_bone.keyframe_insert("rotation_quaternion")
                    # hackish way to force the matrix to update. FIXME: this seems to slow the process down a lot
                    bpy.ops.object.mode_set(mode="OBJECT", toggle=False)

            scene.frame_current = 1

        endTime = time.time()
        print(f"SAFE Animation import completed in {endTime - startTime:.2f} seconds")
        print(f"Processed {numFrames} frames with {len(bones)} bones")
        
        # **PROFILING: Print detailed timing breakdown**
        total_time = endTime - startTime
        print("\n=== PERFORMANCE BREAKDOWN ===")
        print(f"Mode Switches: {timing_stats['mode_switches']:.2f}s ({timing_stats['mode_switches']/total_time*100:.1f}%)")
        print(f"Keyframe Inserts: {timing_stats['keyframe_inserts']:.2f}s ({timing_stats['keyframe_inserts']/total_time*100:.1f}%)")
        print(f"Matrix Calculations: {timing_stats['matrix_calculations']:.2f}s ({timing_stats['matrix_calculations']/total_time*100:.1f}%)")
        print(f"Bone Transformations: {timing_stats['bone_transformations']:.2f}s ({timing_stats['bone_transformations']/total_time*100:.1f}%)")
        print(f"Other Operations: {total_time - sum(timing_stats.values()):.2f}s ({(total_time - sum(timing_stats.values()))/total_time*100:.1f}%)")
        print("=============================")


class AnimationLoadMode(Enum):
    NONE = "NONE"
    ALL = "ALL"
    RANGE = "RANGE"


class GLA:
    def __init__(self):
        # whether this is the automatic default skeleton
        self.isDefault = False  # TODO replace with `skeleton_object is None`
        self.header = MdxaHeader()
        self.boneOffsets = MdxaBoneOffsets()
        self.skeleton = MdxaSkel()
        self.boneIndexByName: Dict[str, int] = {}
        # boneNameByIndex = {} #just use bones[index].name
        # the Blender Armature / Object
        self.skeleton_armature: Optional[bpy.types.Armature] = None
        self.skeleton_object: Optional[bpy.types.Object] = None
        self.animation = MdxaAnimation()

    def loadFromFile(
        self,
        filepath_abs: str,
        loadAnimation: AnimationLoadMode,
        startFrame: int,
        numFrames: int,
        data_frames_file: dict,
    ) -> Tuple[bool, ErrorMessage]:
        if log_level == "DEBUG":
            print("Loading {}...".format(filepath_abs))
        try:
            file: BinaryIO = open(filepath_abs, mode="rb")
        except IOError:
            print("Could not open file: {}".format(filepath_abs))
            return False, ErrorMessage("Could not open file!")
        profiler = MrwProfiler.SimpleProfiler(True)
        # load header
        profiler.start("reading header")
        success, message = self.header.loadFromFile(file)
        if not success:
            return False, message
        profiler.stop("reading header")
        # load offsets (directly after header, always)
        profiler.start("reading bone hierarchy")
        self.boneOffsets.loadFromFile(file, self.header.numBones)
        # load bones
        self.skeleton.loadFromFile(file, self.boneOffsets)
        # build lookup map
        for bone in self.skeleton.bones:
            self.boneIndexByName[bone.name] = bone.index
        profiler.stop("reading bone hierarchy")
        if loadAnimation != AnimationLoadMode.NONE:
            profiler.start("reading animations")
            if loadAnimation == AnimationLoadMode.ALL:
                success, message = self.animation.loadFromFile(file, self.header, 0, -1, data_frames_file)
            else:
                assert loadAnimation == AnimationLoadMode.RANGE
                success, message = self.animation.loadFromFile(
                    file, self.header, startFrame, numFrames, data_frames_file
                )
            if not success:
                return False, message
            profiler.stop("reading animations")
        return True, NoError

    def loadFromBlender(
        self, gla_filepath_rel: str, gla_reference_abs: str
    ) -> Tuple[bool, ErrorMessage]:
        # fill out header name
        self.header.name = gla_filepath_rel

        # find skeleton_root
        if "skeleton_root" not in bpy.data.objects:
            return False, ErrorMessage("No skeleton_root object found!")
        skeleton_object = bpy_generic_cast(
            bpy.types.Object, bpy.data.objects["skeleton_root"]
        )
        self.skeleton_object = skeleton_object
        if self.skeleton_object.type != "ARMATURE":
            return False, ErrorMessage("skeleton_root is no Armature!")
        self.skeleton_armature = downcast(
            bpy.types.Armature,
            optional_cast(bpy.types.Object, self.skeleton_object).data,
        )
        self.header.scale = self.skeleton_object.g2_prop_scale / 100  # pyright: ignore [reportAttributeAccessIssue]

        # make skeleton_root the active object
        bpy.context.view_layer.objects.active = self.skeleton_object
        self.skeleton_object.select_set(True)
        self.skeleton_object.hide_viewport = False

        # in case of rescaled/moved skeleton object: get transformation (assuming we're a child of scene_root)
        localMat = matrix_getter_cast(self.skeleton_object.matrix_local)

        # if there's a reference GLA (for bone indices), load that
        if gla_reference_abs != "":
            print(
                "Using reference GLA skeleton - warning: there's no check beyond bone names (hierarchy, base pose etc.)"
            )

            # load reference GLA
            referenceGLA = GLA()
            success, message = referenceGLA.loadFromFile(
                gla_reference_abs, AnimationLoadMode.NONE, 0, 0
            )
            if not success:
                return False, ErrorMessage(f"Could not load reference GLA: {message}")

            # copy relevant data from reference
            self.boneIndexByName = referenceGLA.boneIndexByName
            # will be changed, but reference is discarded later anyway
            self.skeleton = referenceGLA.skeleton
            self.boneOffsets = referenceGLA.boneOffsets
            self.header.ofsFrames = referenceGLA.header.ofsFrames
            self.header.ofsSkel = referenceGLA.header.ofsSkel
            self.header.numBones = referenceGLA.header.numBones

            # verify all bones exist
            success, message = self.skeleton.fitsArmature(self.skeleton_armature)
            if not success:
                return False, ErrorMessage(
                    f"Armature does not fit reference: {message}"
                )

        # or no reference GLA? build new skeleton then.
        else:
            # enter edit mode so we can access editbones
            bpy.ops.object.mode_set(mode="EDIT")

            # populate bone hierarchy
            bonesToAdd = [
                bpy_generic_cast(bpy.types.EditBone, bone)
                for bone in self.skeleton_armature.edit_bones
            ]
            while len(bonesToAdd) > 0:
                addedSomething = False
                newBonesToAdd = []
                for bone in bonesToAdd:
                    # add bones whose parents have already been added
                    if bone.parent is None or bone.parent.name in self.boneIndexByName:
                        # create this bone
                        newBone = MdxaBone()

                        # set its index (will be appended, hence the size)
                        newBone.index = len(self.skeleton.bones)

                        # read the rest from the editbone
                        newBone.loadFromBlender(
                            bone, self.boneIndexByName, self.skeleton.bones, localMat
                        )

                        # append bone
                        self.skeleton.bones.append(newBone)
                        addedSomething = True
                    else:
                        newBonesToAdd.append(bone)
                bonesToAdd = newBonesToAdd
                if not addedSomething:
                    return False, ErrorMessage(
                        "Hierarchy error, failed to find bone parent (most likely a bug, actually)"
                    )

            # calculate bone file position offsets
            # first bone starts after the bone offsets
            offset = 4 * len(self.skeleton.bones)
            self.header.ofsSkel = (
                offset + self.boneOffsets.baseOffset
            )  # save first bones position
            for bone in self.skeleton.bones:
                self.boneOffsets.boneOffsets.append(offset)
                offset += bone.getSize()

            self.header.ofsFrames = (
                self.boneOffsets.baseOffset + offset
            )  # frames start after last bone
            self.header.numBones = len(self.skeleton.bones)

        #   retrieve animations

        print("Compressing animation...")

        # enter pose mode
        bpy.ops.object.mode_set(mode="POSE")

        # create a dictionary containing the indices of already added compressed bones - lookup should be faster than a linear search through the existing compressed bones (at the cost of more RAM usage - that's ok)
        compBoneIndices = {}

        # for each frame:
        for curFrame in range(
            bpy.context.scene.frame_start, bpy.context.scene.frame_end + 1
        ):
            # progress bar-ish thing
            if curFrame % 10 == 0:
                print("Compressing frame {}...".format(curFrame))

            frame = MdxaFrame()
            bpy.context.scene.frame_set(curFrame)
            # bpy.context.scene.frame_current = curFrame

            # bone offsets need to be calculated in hierarchical order, but written in index order
            # so calculate first:
            # these get written to the GLA
            relativeBoneOffsets: List[Optional[mathutils.Matrix]] = [
                None
            ] * self.header.numBones

            # these are for calculating
            absoluteBoneOffsets: List[Optional[mathutils.Matrix]] = [
                None
            ] * self.header.numBones

            unprocessed = list(range(self.header.numBones))
            # FIXME: instead of doing this once per frame, cache the correct processing order
            while len(unprocessed) > 0:
                # make sure we're not looping infinitely (shouldn't be possible)
                progressed = False

                newUnprocessed: List[int] = []
                for index in unprocessed:
                    bone = self.skeleton.bones[index]
                    basebone = bpy_generic_cast(
                        bpy.types.Bone, self.skeleton_armature.bones[bone.name]
                    )
                    posebone = bpy_generic_cast(
                        bpy.types.PoseBone, self.skeleton_object.pose.bones[bone.name]
                    )

                    basePoseMat = matrix_overload_cast(
                        localMat @ matrix_getter_cast(basebone.matrix_local)
                    )
                    poseMat = matrix_overload_cast(
                        localMat @ matrix_getter_cast(posebone.matrix)
                    )

                    # change rotation axes from blender style to gla style
                    SoF2G2Math.BlenderBoneRotToGLA(basePoseMat)
                    SoF2G2Math.BlenderBoneRotToGLA(poseMat)
                    if bone.parent == -1:
                        relativeBoneOffsets[index] = absoluteBoneOffsets[index] = (
                            matrix_overload_cast(poseMat @ basePoseMat.inverted())
                        )

                        progressed = True

                    elif bone.parent not in unprocessed:
                        # just what the if checks
                        assert absoluteBoneOffsets[bone.parent] is not None
                        # each offset should only be calculated once.
                        assert absoluteBoneOffsets[index] is None

                        relativeBoneOffsets[index] = matrix_overload_cast(
                            optional_cast(
                                mathutils.Matrix, absoluteBoneOffsets[bone.parent]
                            ).inverted()
                            @ matrix_overload_cast(poseMat @ basePoseMat.inverted())
                        )
                        absoluteBoneOffsets[index] = matrix_overload_cast(
                            optional_cast(
                                mathutils.Matrix, absoluteBoneOffsets[bone.parent]
                            )
                            @ optional_cast(
                                mathutils.Matrix, relativeBoneOffsets[index]
                            )
                        )

                        progressed = True

                    else:
                        newUnprocessed.append(index)
                unprocessed = newUnprocessed

                assert progressed

            gaplessRelativeBoneOffsets, err = ensureListIsGapless(relativeBoneOffsets)
            if gaplessRelativeBoneOffsets is None:
                return False, ErrorMessage(
                    f"internal error: did not calculate all bone transformations: {err}"
                )
            # then write precalculated offsets:
            for offset in gaplessRelativeBoneOffsets:
                # compress that offset
                compOffset = SoF2G2Math.CompBone.compress(offset)

                try:
                    # try to use existing compressed bone offset
                    index = compBoneIndices[compOffset]
                    frame.boneIndices.append(index)
                except KeyError:
                    # if this offset is not yet part of the pool, add it
                    index = len(self.animation.bonePool.bones)
                    downcast(List[bytes], self.animation.bonePool.bones).append(
                        compOffset
                    )
                    frame.boneIndices.append(index)
                    compBoneIndices[compOffset] = index

            self.animation.frames.append(frame)

        self.header.numFrames = (
            bpy.context.scene.frame_end - bpy.context.scene.frame_start + 1
        )
        # enforce 32 bit alignment after 3-byte-indices
        framesSize = 3 * self.header.numFrames * self.header.numBones
        if framesSize % 4 != 0:
            framesSize += 4 - (framesSize % 4)
        self.header.ofsCompBonePool = self.header.ofsFrames + framesSize
        self.header.ofsEnd = (
            self.header.ofsCompBonePool + len(self.animation.bonePool.bones) * 14
        )

        return True, NoError

    def saveToFile(self, filepath_abs: str) -> Tuple[bool, ErrorMessage]:
        try:
            file = open(filepath_abs, mode="wb")
        except IOError:
            print("Could not open file: ", filepath_abs, sep="")
            return False, ErrorMessage("Could not open file!")
        self.header.saveToFile(file)
        self.boneOffsets.saveToFile(file)
        self.skeleton.saveToFile(file, self.header)
        self.animation.saveToFile(file, self.header)
        assert file.tell() == self.header.ofsEnd
        return True, NoError

    def saveToBlender(
        self,
        scene_root: bpy.types.Object,
        useAnimation: bool,
        skeletonFixes: SoF2G2Constants.SkeletonFixes,
        data_frames_file: dict,
    ) -> Tuple[bool, ErrorMessage]:
        print("Applying skeleton/skeleton to Blender")
        profiler = MrwProfiler.SimpleProfiler(True)
        # default skeleton = no skeleton.
        if self.isDefault:
            return True, NoError

        #  try using existing skeletons
        # first check if there's already an armature object called skeleton_root. Try using that.
        if "skeleton_root" in bpy.data.objects:
            print("Found a skeleton_root object, trying to use it.")
            self.skeleton_object = bpy.data.objects["skeleton_root"]
            if self.skeleton_object.type != "ARMATURE":
                return False, ErrorMessage(
                    "Existing skeleton_root object is no armature!"
                )
            self.skeleton_armature = downcast(
                bpy.types.Armature,
                optional_cast(bpy.types.Object, self.skeleton_object).data,
            )
            self.skeleton_object.g2_prop_scale = self.header.scale * 100  # pyright: ignore [reportAttributeAccessIssue]
        # If there's no skeleton, there may yet still be an armature. Use that.
        elif "skeleton_root" in bpy.data.armatures:
            print("Found skeleton_root armature, trying to use it.")
            self.skeleton_armature = bpy.data.armatures["skeleton_root"]

        # for profiling, possibly
        global g_temp
        # if we found an existing armature, we need to make sure it's linked to an object and valid
        if self.skeleton_armature:
            # see if the armature fits
            success, message = self.skeleton.fitsArmature(self.skeleton_armature)
            if not success:
                return False, message

            # this armature would work, add it to an object if necessary
            if not self.skeleton_object:
                self.skeleton_object = bpy.data.objects.new(
                    "skeleton_root", self.skeleton_armature
                )
                self.skeleton_object.g2_prop_scale = self.header.scale * 100  # pyright: ignore [reportAttributeAccessIssue]

            # link the object to the current scene if necessary
            if self.skeleton_object.name not in bpy.context.scene.collection.objects:
                bpy.context.scene.collection.objects.link(self.skeleton_object)

            # set its parent to the scene_root (not strictly speaking necessary but keeps output consistent)
            self.skeleton_object.parent = scene_root

            # add animations, if any
            if useAnimation:
                profiler.start("applying animations")
                # go to object mode
                bpy.context.view_layer.objects.active = self.skeleton_object
                bpy.ops.object.mode_set(mode="OBJECT", toggle=False)
                if PROFILE:
                    import cProfile

                    print("=== Profile start ===")
                    cProfile.runctx(
                        "self.animation.saveToBlender(self.skeleton, self.skeleton_object, self.header.scale)",
                        globals(),
                        locals(),
                    )
                    print("=== Profile stop ===")
                else:
                    self.animation.saveToBlender(
                        self.skeleton, self.skeleton_object, self.header.scale, data_frames_file    
                    )
                profiler.stop("applying animations")

            # that's all
            return True, NoError

        # no existing Armature found, create a new one.

        # create armature
        profiler.start("creating armature")
        success, message = self.skeleton.saveToBlender(scene_root, skeletonFixes)
        if not success:
            return False, message
        self.skeleton_armature = self.skeleton.armature
        self.skeleton_object = self.skeleton.armature_object
        self.skeleton_object.g2_prop_scale = self.header.scale * 100  # pyright: ignore [reportAttributeAccessIssue]
        profiler.stop("creating armature")

        # add animations, if any
        if useAnimation:
            profiler.start("applying animations")
            # go to object mode
            bpy.context.view_layer.objects.active = self.skeleton_object
            bpy.ops.object.mode_set(mode="OBJECT", toggle=False)
            if PROFILE:
                import cProfile

                print("=== Profile start ===")
                cProfile.runctx(
                    "self.animation.saveToBlender(self.skeleton, self.skeleton_object, self.header.scale, data_frames_file)",
                    globals(),
                    locals(),
                )
                print("=== Profile stop ===")
            else:
                self.animation.saveToBlender(
                    self.skeleton,
                    self.skeleton_object,
                    self.header.scale,
                    data_frames_file,
                )
            profiler.stop("applying animations")
        return True, NoError
