import bpy
import bmesh
import mathutils
from mathutils import Vector, Matrix
import os

class UnityCharacterFixer:
    """Fixes character positioning issues and prepares for Unity export"""
    
    def __init__(self):
        self.scene = bpy.context.scene
        self.original_cursor_location = None
        self.original_3d_cursor_location = None
        
    def save_cursor_state(self):
        """Save current cursor and 3D cursor positions"""
        self.original_cursor_location = bpy.context.scene.cursor.location.copy()
        self.original_3d_cursor_location = bpy.context.scene.cursor.location.copy()
        
    def restore_cursor_state(self):
        """Restore cursor positions"""
        if self.original_cursor_location:
            bpy.context.scene.cursor.location = self.original_cursor_location
        if self.original_3d_cursor_location:
            bpy.context.scene.cursor.location = self.original_3d_cursor_location
    
    def fix_character_positioning(self, target_scale=1.0, target_location=(0, 0, 0)):
        """
        Fix character positioning issues between Edit and Object modes
        and prepare for Unity export
        
        Args:
            target_scale: Target scale for Unity (default 1.0)
            target_location: Target location for Unity (default origin)
        """
        print("=== Unity Character Fixer ===")
        
        # Save cursor state
        self.save_cursor_state()
        
        # Set cursor to origin
        bpy.context.scene.cursor.location = (0, 0, 0)
        
        # Find all relevant objects
        armature_objects = []
        mesh_objects = []
        scene_root = None
        
        for obj in bpy.context.scene.objects:
            if obj.type == 'ARMATURE':
                if 'skeleton_root' in obj.name or 'armature' in obj.name.lower():
                    armature_objects.append(obj)
            elif obj.type == 'MESH':
                mesh_objects.append(obj)
            elif obj.name == 'scene_root':
                scene_root = obj
        
        print(f"Found {len(armature_objects)} armature(s), {len(mesh_objects)} mesh(es)")
        
        # Process each armature
        for armature_obj in armature_objects:
            self.fix_armature_positioning(armature_obj, target_scale, target_location)
        
        # Process mesh objects
        for mesh_obj in mesh_objects:
            self.fix_mesh_positioning(mesh_obj, target_scale, target_location)
        
        # Fix scene root if it exists
        if scene_root:
            self.fix_scene_root_positioning(scene_root, target_scale, target_location)
        
        # Apply transformations and clean up
        self.apply_transformations()
        
        # Restore cursor state
        self.restore_cursor_state()
        
        print("=== Character positioning fixed! ===")
    
    def fix_armature_positioning(self, armature_obj, target_scale, target_location):
        """Fix armature positioning and scaling"""
        print(f"Fixing armature: {armature_obj.name}")
        
        # Store original transform
        original_matrix = armature_obj.matrix_world.copy()
        
        # Set to object mode
        bpy.context.view_layer.objects.active = armature_obj
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # Apply current transformations
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        
        # Set new location and scale
        armature_obj.location = target_location
        armature_obj.scale = (target_scale, target_scale, target_scale)
        
        # Fix bone positioning in edit mode
        bpy.ops.object.mode_set(mode='EDIT')
        
        # Get edit bones
        edit_bones = armature_obj.data.edit_bones
        
        # Find root bone (usually the first one or one without parent)
        root_bone = None
        for bone in edit_bones:
            if bone.parent is None:
                root_bone = bone
                break
        
        if root_bone:
            # Move root bone to origin
            root_bone.head = (0, 0, 0)
            root_bone.tail = (0, 0, 0.1)  # Small tail for visibility
            
            # Update all child bones
            self.update_bone_hierarchy(edit_bones, root_bone)
        
        # Return to object mode
        bpy.ops.object.mode_set(mode='OBJECT')
        
        print(f"Armature {armature_obj.name} fixed")
    
    def update_bone_hierarchy(self, edit_bones, parent_bone):
        """Recursively update bone hierarchy positioning"""
        for bone in edit_bones:
            if bone.parent == parent_bone:
                # Calculate relative position
                if parent_bone.head != parent_bone.tail:
                    # Parent has a direction, calculate relative position
                    parent_direction = (parent_bone.tail - parent_bone.head).normalized()
                    bone.head = parent_bone.tail
                    bone.tail = bone.head + parent_direction * 0.1
                else:
                    # Parent is at origin, position child relative to it
                    bone.head = parent_bone.head + Vector((0, 0, 0.1))
                    bone.tail = bone.head + Vector((0, 0, 0.1))
                
                # Recursively update children
                self.update_bone_hierarchy(edit_bones, bone)
    
    def fix_mesh_positioning(self, mesh_obj, target_scale, target_location):
        """Fix mesh positioning and scaling"""
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
        
        # Ensure mesh is centered
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        
        # Update mesh
        bm.to_mesh(mesh_obj.data)
        bm.free()
        
        # Return to object mode
        bpy.ops.object.mode_set(mode='OBJECT')
        
        print(f"Mesh {mesh_obj.name} fixed")
    
    def fix_scene_root_positioning(self, scene_root, target_scale, target_location):
        """Fix scene root positioning"""
        print(f"Fixing scene root: {scene_root.name}")
        
        # Set to object mode
        bpy.context.view_layer.objects.active = scene_root
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # Apply current transformations
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        
        # Set new location and scale
        scene_root.location = target_location
        scene_root.scale = (target_scale, target_scale, target_scale)
        
        print(f"Scene root {scene_root.name} fixed")
    
    def apply_transformations(self):
        """Apply all transformations to fix mode switching issues"""
        print("Applying transformations...")
        
        # Select all objects
        bpy.ops.object.select_all(action='SELECT')
        
        # Apply transformations
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        
        # Clear selection
        bpy.ops.object.select_all(action='DESELECT')
        
        print("Transformations applied")
    
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
        self.apply_transformations()
        
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

def main():
    """Main function to run the character fixer"""
    fixer = UnityCharacterFixer()
    
    # Fix character positioning
    fixer.fix_character_positioning(
        target_scale=1.0,  # Unity scale
        target_location=(0, 0, 0)  # Origin
    )
    
    # Prepare for Unity export
    fixer.prepare_for_unity_export()
    
    print("Character fix complete! Your character should now be properly positioned for Unity.")

# Run the script
if __name__ == "__main__":
    main()
