
def handle_load_weapon_file(op):
    basepath = op.basepath
    op.report({"INFO"}, f"Weapon loaded: {basepath}")
    return {"FINISHED"}