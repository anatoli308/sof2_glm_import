import bpy 
import bmesh
import mathutils
from mathutils import Vector, Matrix
import os

class SoF2UnityOptimizer:
    """Optimizes SoF2 characters for Unity export with proper positioning"""
    
    def __init__(self):
        self.scene = bpy.context.scene
        self.original_cursor_location = None
        
    def save_cursor_state(self):
        """Save current cursor position"""
        self.original_cursor_location = bpy.context.scene.cursor.location.copy()
        
    def restore_cursor_state(self):
        """Restore cursor position"""
        if self.original_cursor_location:
            bpy.context.scene.cursor.location = self.original_cursor_location
    
    def fix_sof2_character(self, target_scale=1.0, target_location=(0, 0, 0)):
        """
        Fix SoF2 character positioning issues specifically
        
        Args:
            target_scale: Target scale for Unity (default 1.0)
            target_location: Target location for Unity (default origin)
        """
        print("=== SoF2 Unity Optimizer ===")
        
        # Save cursor state
        self.save_cursor_state()
        
        # Set cursor to origin
        bpy.context.scene.cursor.location = (0, 0, 0)
        
        # Find SoF2 specific objects
        skeleton_root = None
        scene_root = None
        mesh_objects = []
        
        for obj in bpy.context.scene.objects:
            if obj.name == 'skeleton_root' and obj.type == 'ARMATURE':
                skeleton_root = obj
            elif obj.name == 'scene_root':
                scene_root = obj
            elif obj.type == 'MESH' and obj.parent == scene_root:
                mesh_objects.append(obj)
        
        print(f"Found skeleton_root: {skeleton_root is not None}")
        print(f"Found scene_root: {scene_root is not None}")
        print(f"Found {len(mesh_objects)} mesh objects")
        
        # Fix skeleton first
        if skeleton_root:
            self.fix_skeleton_root(skeleton_root, target_scale, target_location)
        
        # Fix scene root
        if scene_root:
            self.fix_scene_root(scene_root, target_scale, target_location)
        
        # Fix mesh objects
        for mesh_obj in mesh_objects:
            self.fix_mesh_object(mesh_obj, target_scale, target_location)
        
        # Apply transformations
        self.apply_all_transformations()
        
        # Restore cursor state
        self.restore_cursor_state()
        
        print("=== SoF2 character optimization complete! ===")
    
    def fix_skeleton_root(self, skeleton_obj, target_scale, target_location):
        """Fix skeleton_root armature positioning"""
        print(f"Fixing skeleton_root: {skeleton_obj.name}")
        
        # Set to object mode
        bpy.context.view_layer.objects.active = skeleton_obj
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # Apply current transformations
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        
        # Set new location and scale
        skeleton_obj.location = target_location
        skeleton_obj.scale = (target_scale, target_scale, target_scale)
        
        # Fix bone positioning in edit mode
        bpy.ops.object.mode_set(mode='EDIT')
        
        # Get edit bones
        edit_bones = skeleton_obj.data.edit_bones
        
        # Find root bone (usually the first one or one without parent)
        root_bone = None
        for bone in edit_bones:
            if bone.parent is None:
                root_bone = bone
                break
        
        if root_bone:
            # Store original bone positions
            original_positions = {}
            for bone in edit_bones:
                original_positions[bone.name] = {
                    'head': bone.head.copy(),
                    'tail': bone.tail.copy()
                }
            
            # Move root bone to origin
            root_bone.head = (0, 0, 0)
            root_bone.tail = (0, 0, 0.1)  # Small tail for visibility
            
            # Update all child bones maintaining relative positions
            self.update_bone_hierarchy_sof2(edit_bones, root_bone, original_positions)
        
        # Return to object mode
        bpy.ops.object.mode_set(mode='OBJECT')
        
        print(f"Skeleton {skeleton_obj.name} fixed")
    
    def update_bone_hierarchy_sof2(self, edit_bones, parent_bone, original_positions):
        """Update bone hierarchy maintaining SoF2 structure"""
        for bone in edit_bones:
            if bone.parent == parent_bone:
                # Calculate relative position from original
                if bone.name in original_positions:
                    orig_head = original_positions[bone.name]['head']
                    orig_tail = original_positions[bone.name]['tail']
                    
                    # Calculate relative position to parent
                    if parent_bone.name in original_positions:
                        parent_orig_head = original_positions[parent_bone.name]['head']
                        relative_head = orig_head - parent_orig_head
                        relative_tail = orig_tail - parent_orig_head
                        
                        # Apply relative position to new parent position
                        bone.head = parent_bone.head + relative_head
                        bone.tail = parent_bone.head + relative_tail
                    else:
                        # Fallback: position relative to parent
                        bone.head = parent_bone.tail
                        bone.tail = bone.head + Vector((0, 0, 0.1))
                
                # Recursively update children
                self.update_bone_hierarchy_sof2(edit_bones, bone, original_positions)
    
    def fix_scene_root(self, scene_root, target_scale, target_location):
        """Fix scene_root positioning"""
        print(f"Fixing scene_root: {scene_root.name}")
        
        # Set to object mode
        bpy.context.view_layer.objects.active = scene_root
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # Apply current transformations
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        
        # Set new location and scale
        scene_root.location = target_location
        scene_root.scale = (target_scale, target_scale, target_scale)
        
        print(f"Scene root {scene_root.name} fixed")
    
    def fix_mesh_object(self, mesh_obj, target_scale, target_location):
        """Fix mesh object positioning"""
        print(f"Fixing mesh: {mesh_obj.name}")
        
        # Set to object mode
        bpy.context.view_layer.objects.active = mesh_obj
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # Apply current transformations
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        
        # Set new location and scale
        mesh_obj.location = target_location
        mesh_obj.scale = (target_scale, target_scale, target_scale)
        
        # Fix mesh data in edit mode
        bpy.ops.object.mode_set(mode='EDIT')
        
        # Get bmesh representation
        bm = bmesh.from_mesh(mesh_obj.data)
        
        # Ensure mesh is properly centered
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        
        # Update mesh
        bm.to_mesh(mesh_obj.data)
        bm.free()
        
        # Return to object mode
        bpy.ops.object.mode_set(mode='OBJECT')
        
        print(f"Mesh {mesh_obj.name} fixed")
    
    def apply_all_transformations(self):
        """Apply all transformations to fix mode switching issues"""
        print("Applying all transformations...")
        
        # Select all objects
        bpy.ops.object.select_all(action='SELECT')
        
        # Apply transformations
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        
        # Clear selection
        bpy.ops.object.select_all(action='DESELECT')
        
        print("All transformations applied")
    
    def prepare_for_unity_export(self, export_path=None):
        """Prepare the scene for Unity export"""
        print("Preparing for Unity export...")
        
        # Set up scene for Unity
        self.scene.frame_start = 0
        self.scene.frame_end = 1
        
        # Set units to meters (Unity standard)
        self.scene.unit_settings.length_unit = 'METERS'
        self.scene.unit_settings.scale_length = 1.0
        
        # Apply all transformations
        self.apply_all_transformations()
        
        # Export to FBX if path provided
        if export_path:
            self.export_to_fbx(export_path)
        
        print("Unity export preparation complete!")
    
    def export_to_fbx(self, filepath):
        """Export to FBX format for Unity"""
        print(f"Exporting to FBX: {filepath}")
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Export settings for Unity
        bpy.ops.export_scene.fbx(
            filepath=filepath,
            use_selection=False,
            use_active_collection=False,
            global_scale=1.0,
            apply_unit_scale=True,
            apply_scale_options='FBX_SCALE_NONE',
            use_space_transform=True,
            bake_space_transform=True,
            object_types={'ARMATURE', 'MESH'},
            use_mesh_modifiers=True,
            use_mesh_modifiers_render=True,
            mesh_smooth_type='OFF',
            use_mesh_edges=False,
            use_tspace=False,
            use_custom_props=False,
            add_leaf_bones=True,
            primary_bone_axis='Y',
            secondary_bone_axis='X',
            use_armature_deform_only=False,
            armature_nodetype='NULL',
            bake_anim=True,
            bake_anim_use_all_bones=True,
            bake_anim_use_nla_strips=True,
            bake_anim_use_all_actions=True,
            bake_anim_force_startend_keying=True,
            bake_anim_step=1.0,
            bake_anim_simplify_factor=1.0,
            path_mode='AUTO',
            embed_textures=False,
            batch_mode='OFF',
            use_batch_own_dir=True,
            use_metadata=True
        )
        
        print(f"FBX export complete: {filepath}")
    
    def check_character_health(self):
        """Check if character is properly positioned"""
        print("=== Character Health Check ===")
        
        issues = []
        
        # Check skeleton_root
        skeleton_root = bpy.data.objects.get('skeleton_root')
        if skeleton_root:
            if skeleton_root.location != (0, 0, 0):
                issues.append(f"Skeleton root not at origin: {skeleton_root.location}")
            if skeleton_root.scale != (1, 1, 1):
                issues.append(f"Skeleton root not at unit scale: {skeleton_root.scale}")
        
        # Check scene_root
        scene_root = bpy.data.objects.get('scene_root')
        if scene_root:
            if scene_root.location != (0, 0, 0):
                issues.append(f"Scene root not at origin: {scene_root.location}")
            if scene_root.scale != (1, 1, 1):
                issues.append(f"Scene root not at unit scale: {scene_root.scale}")
        
        # Check mesh objects
        mesh_objects = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
        for mesh_obj in mesh_objects:
            if mesh_obj.location != (0, 0, 0):
                issues.append(f"Mesh {mesh_obj.name} not at origin: {mesh_obj.location}")
            if mesh_obj.scale != (1, 1, 1):
                issues.append(f"Mesh {mesh_obj.name} not at unit scale: {mesh_obj.scale}")
        
        if issues:
            print("Issues found:")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print("Character is properly positioned!")
        
        return len(issues) == 0

def main():
    """Main function to run the SoF2 Unity optimizer"""
    optimizer = SoF2UnityOptimizer()
    
    # Fix character positioning
    optimizer.fix_sof2_character(
        target_scale=1.0,  # Unity scale
        target_location=(0, 0, 0)  # Origin
    )
    
    # Check character health
    optimizer.check_character_health()
    
    # Prepare for Unity export
    optimizer.prepare_for_unity_export()
    
    print("SoF2 character optimization complete! Your character should now be properly positioned for Unity.")

# Run the script
if __name__ == "__main__":
    main()
