from .mod_reload import reload_modules
reload_modules(locals(), __package__, ["SoFG2Panels", "SoFG2Operators"], [])  # nopep8

#  Blender
import bpy

#  Local
import os
from dotenv import load_dotenv

# Ghoul 2
from . import SoF2G2Panels
from . import SoF2G2Operators

bl_info = {
    "name": "SoF2 Import/Export Tools",
    "author": "anatoli",
    "description": "Soldier of Fortune 2 GLA, GLM importer",
    "blender": (4, 5, 3),
    "location": "File > Import-Export",
    "category": "Import-Export"
}

# there must be at least one operator in the locals for Blender to reload correctly.

def register():
    load_dotenv()  # .env einlesen
    
    attach_to_vscode = os.getenv("ATTACH_VSCODE_DEBUG", "false").lower() == "true"
    if attach_to_vscode:
        import debugpy
        debugpy.listen(("localhost", 5678))
        print("Waiting for VSCode debugger...")
        debugpy.wait_for_client()
        print("Debugger attached")
    bpy.utils.register_class(SoF2G2Panels.G2PropertiesPanel)

    SoF2G2Panels.initG2Properties()
    SoF2G2Operators.register()


def unregister():
    bpy.utils.unregister_class(SoF2G2Panels.G2PropertiesPanel)
    SoF2G2Operators.unregister()

if __name__ == "__main__":
    register()
