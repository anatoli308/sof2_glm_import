import os
from . import SoF2G2DataCache as DataCache
from . import SoF2G2WeaponPanel


def draw_glm_import_panel(layout, operator):
    """Draw the GLM import panel UI"""
    layout.label(text="Bitte wähle dein SoF2 Basepath:", icon="FILE_FOLDER")
    layout.prop(operator, "basepath")

    if operator.basepath and os.path.normpath(operator.basepath).endswith(
        os.path.normpath("/base")
    ):
        layout.prop(operator, "loadWeapons")
        box = layout.box()
        box.label(text="Basepath OK!", icon="CHECKMARK")

        if operator.loadWeapons:
            SoF2G2WeaponPanel.draw_weapon_import_panel(layout, operator)
        else:
            # --- Neuer NPC-Browser ---
            layout.prop(operator, "npc_search", text="", icon="VIEWZOOM")

            items = DataCache.get_npc_enum_items(operator.basepath)
            items.sort(
                key=lambda x: x[0]
            )  # Sort by first tuple element (identifier) ascending
            search = operator.npc_search.strip().lower()
            shown = 0
            max_show = 30  # Limit, damit das Panel nicht explodiert

            for ident, name, desc in items:
                if search and search not in name.lower() and search not in desc.lower():
                    continue
                if shown >= max_show:
                    layout.label(
                        text=f"... {len(items) - shown} weitere NPCs ausgeblendet ..."
                    )
                    break

                row = layout.row(align=True)
                # if no model: found in description mark alert!
                no_model = False
                if "model:" not in desc.lower():
                    row.alert = True
                    no_model = True

                no_deathmatch = False
                if "deathmatch: no" in desc.lower():
                    no_deathmatch = True

                op = row.operator(
                    "glm.select_npc",
                    text=name,
                    emboss=True,
                )
                op.npc_id = ident
                short_desc = ("(SP) " if no_deathmatch else "(MP)") + (
                    " (No Model)" if no_model else ""
                )
                row.label(text=short_desc)
                shown += 1

            if not shown:
                layout.label(text="Keine NPCs gefunden", icon="ERROR")

            layout.separator()

            if operator.npc_selected:
                box = layout.box()
                row = box.row()
                row.label(text=f"{operator.npc_selected} selected", icon="CHECKMARK")

                # restliche Optionen
                layout.prop(operator, "scale")
                layout.prop(operator, "loadAnimations")
                if operator.loadAnimations == "RANGE":
                    layout.prop(operator, "startFrame")
                    layout.prop(operator, "numFrames")
                #layout.prop(operator, "skeletonFixes")

            else:
                row = layout.row()
                row.alert = True
                row.label(text="Please select an NPC!", icon="ERROR")
    else:
        row = layout.row()
        row.alert = True
        row.label(text="Base folder not detected!", icon="ERROR")
        row = layout.row()
        row.label(text="Please select your base folder")
        row = layout.row()
        row.label(text="e.g. C:\\SoF2\\base")
        row = layout.row()
        row.label(text=f"{operator.basepath}", icon="CHECKMARK")
        row = layout.row()
        row.label(text="or any .glm in your SoF2 base path!")

        # restliche Optionen
        layout.prop(operator, "scale")
        layout.prop(operator, "loadAnimations")
        if operator.loadAnimations == "RANGE":
            layout.prop(operator, "startFrame")
            layout.prop(operator, "numFrames")

