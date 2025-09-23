# Pelvis Root Bone Implementation

## Overview
This implementation modifies the SOF2 GLM import addon to make the pelvis bone the skeleton root instead of the model_root. This ensures Unity recognizes the pelvis as the skinned mesh renderer root, which is important for proper character animation and rigging in Unity.

## Changes Made

### 1. Added Pelvis Detection Logic
- Added `_make_pelvis_root_bone()` method to the `MdxaSkel` class
- Detects pelvis bone using common naming conventions:
  - `pelvis`, `pelvis_root`, `hip`, `hips`
  - `pelvis_bone`, `pelvisbone`, `pelvis_root_bone`, `pelvisroot`
  - `hip_bone`, `hipbone`, `hips_bone`, `hipsbone`

### 2. Bone Hierarchy Modification
- Finds the current root bone (parent = -1)
- Makes the pelvis bone the new root (parent = -1)
- Makes the current root bone a child of the pelvis
- Updates parent-child relationships and children lists

### 3. Integration Points
- Applied during skeleton creation in `saveToBlender()` method
- Applied when using existing armatures in `saveToBlender()` method
- Works for both new skeleton creation and existing skeleton usage

### 4. Validation and Debugging
- Added `_verify_bone_hierarchy()` method to validate the bone hierarchy after modification
- Added detailed logging to help with troubleshooting
- Lists available bones if pelvis bone is not found

## Benefits for Unity
- Unity's SkinnedMeshRenderer will use the pelvis as the root bone
- Better compatibility with Unity's humanoid animation system
- Proper bone hierarchy for character animation
- Improved rigging workflow in Unity

## Usage
The functionality is automatically applied when importing SOF2 GLM files. No additional configuration is required. The system will:

1. Look for a pelvis bone in the skeleton
2. If found, make it the root bone
3. If not found, display a warning with available bone names
4. Validate the hierarchy after modification

## Technical Details
- The pelvis bone becomes the root bone (parent = -1)
- The original root bone becomes a child of the pelvis
- All other bone relationships remain unchanged
- The modification is applied before Blender bone creation
- Works with both new and existing armatures
