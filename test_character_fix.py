import bpy
import bmesh
import mathutils
from mathutils import Vector, Matrix

def test_character_positioning():
    """Test function to check if character positioning is correct"""
    print("=== Character Position Test ===")
    
    issues = []
    
    # Check skeleton_root
    skeleton_root = bpy.data.objects.get('skeleton_root')
    if skeleton_root:
        print(f"Skeleton root found: {skeleton_root.name}")
        print(f"  Location: {skeleton_root.location}")
        print(f"  Scale: {skeleton_root.scale}")
        print(f"  Rotation: {skeleton_root.rotation_euler}")
        
        if skeleton_root.location != (0, 0, 0):
            issues.append(f"Skeleton root not at origin: {skeleton_root.location}")
        if skeleton_root.scale != (1, 1, 1):
            issues.append(f"Skeleton root not at unit scale: {skeleton_root.scale}")
    else:
        issues.append("No skeleton_root found")
    
    # Check scene_root
    scene_root = bpy.data.objects.get('scene_root')
    if scene_root:
        print(f"Scene root found: {scene_root.name}")
        print(f"  Location: {scene_root.location}")
        print(f"  Scale: {scene_root.scale}")
        print(f"  Rotation: {scene_root.rotation_euler}")
        
        if scene_root.location != (0, 0, 0):
            issues.append(f"Scene root not at origin: {scene_root.location}")
        if scene_root.scale != (1, 1, 1):
            issues.append(f"Scene root not at unit scale: {scene_root.scale}")
    else:
        issues.append("No scene_root found")
    
    # Check mesh objects
    mesh_objects = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
    print(f"Found {len(mesh_objects)} mesh objects")
    
    for mesh_obj in mesh_objects:
        print(f"Mesh: {mesh_obj.name}")
        print(f"  Location: {mesh_obj.location}")
        print(f"  Scale: {mesh_obj.scale}")
        print(f"  Rotation: {mesh_obj.rotation_euler}")
        
        if mesh_obj.location != (0, 0, 0):
            issues.append(f"Mesh {mesh_obj.name} not at origin: {mesh_obj.location}")
        if mesh_obj.scale != (1, 1, 1):
            issues.append(f"Mesh {mesh_obj.name} not at unit scale: {mesh_obj.scale}")
    
    # Check bones
    if skeleton_root and skeleton_root.type == 'ARMATURE':
        print(f"Checking {len(skeleton_root.data.bones)} bones...")
        
        # Check root bone
        root_bones = [bone for bone in skeleton_root.data.bones if bone.parent is None]
        if root_bones:
            root_bone = root_bones[0]
            print(f"Root bone: {root_bone.name}")
            print(f"  Head: {root_bone.head}")
            print(f"  Tail: {root_bone.tail}")
            
            if root_bone.head != (0, 0, 0):
                issues.append(f"Root bone {root_bone.name} not at origin: {root_bone.head}")
    
    # Summary
    if issues:
        print("\n❌ Issues found:")
        for issue in issues:
            print(f"  - {issue}")
        return False
    else:
        print("\n✅ Character is properly positioned!")
        return True

def quick_fix():
    """Quick fix for character positioning"""
    print("=== Quick Fix ===")
    
    # Set cursor to origin
    bpy.context.scene.cursor.location = (0, 0, 0)
    
    # Fix all objects
    for obj in bpy.context.scene.objects:
        if obj.type in ['ARMATURE', 'MESH']:
            print(f"Fixing {obj.name}...")
            
            # Set to object mode
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode='OBJECT')
            
            # Apply transformations
            bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
            
            # Set to origin
            obj.location = (0, 0, 0)
            obj.scale = (1, 1, 1)
            obj.rotation_euler = (0, 0, 0)
    
    print("Quick fix complete!")

# Run the test
if __name__ == "__main__":
    print("Testing character positioning...")
    is_ok = test_character_positioning()
    
    if not is_ok:
        print("\nRunning quick fix...")
        quick_fix()
        print("\nTesting again...")
        test_character_positioning()
