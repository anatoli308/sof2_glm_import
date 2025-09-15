from . import SoF2G2DataCache as DataCache


def draw_weapon_import_panel(layout, operator):
    """Draw the Weapon import panel UI"""
    layout.prop(operator, "weapon_search", text="", icon="VIEWZOOM")

    items = DataCache.get_weapon_enum_items(operator.basepath)
    items.sort(key=lambda x: x[0])  # Sort by first tuple element (identifier) ascending
    search = operator.weapon_search.strip().lower()
    shown = 0
    max_show = 10  # Limit, damit das Panel nicht explodiert

    for ident, name, desc in items:
        if search and search not in name.lower() and search not in desc.lower():
            continue
        if shown >= max_show:
            layout.label(
                text=f"... {len(items) - shown} weitere Waffen ausgeblendet ..."
            )
            break

        row = layout.row(align=True)
        op = row.operator(
            "glm.select_weapon",
            text=name,
            emboss=True,
        )
        op.weapon_id = ident
        row.label(text=desc)
        shown += 1

    if not shown:
        layout.label(text="Keine Waffen gefunden", icon="ERROR")

    layout.separator()

    if operator.weapon_selected:
        box = layout.box()
        row = box.row()
        row.label(text=f"{operator.weapon_selected} selected", icon="CHECKMARK")

        layout.prop(operator, "scale")
        layout.prop(operator, "loadAnimations")
        if operator.loadAnimations == "RANGE":
            layout.prop(operator, "startFrame")
            layout.prop(operator, "numFrames")
        # layout.prop(operator, "skeletonFixes")

    else:
        row = layout.row()
        row.alert = True
        row.label(text="Please select a Weapon!", icon="ERROR")
