import os
import json
from typing import Tuple

from . import SoF2G2DataCache as DataCache
from . import skl_parser
from .SoF2G2DataParser import parse_g2skin_to_json


def _load_all_skl_data(basepath: str):
    """Parse all .skl files under basepath/skeletons and return a list of dicts."""
    all_skl_data = []
    skeletons_dir = os.path.join(basepath, "skeletons")
    if not os.path.isdir(skeletons_dir):
        return all_skl_data
    for skl_file in os.listdir(skeletons_dir):
        if not skl_file.endswith(".skl"):
            continue
        try:
            with open(
                os.path.join(skeletons_dir, skl_file), "r", encoding="utf-8"
            ) as f:
                parsed = skl_parser.parse_skl(f.read())
            if isinstance(parsed, dict):
                parsed["filename"] = skl_file
            all_skl_data.append(parsed)
        except Exception as e:
            print(f"Error parsing SKL file {skl_file}: {e}")
    return all_skl_data


def export_all_data(
    basepath: str, *, generate_separate: bool = True
) -> Tuple[bool, str, dict]:
    """
    Export a single combined JSON file containing weapons, items, NPCs, and skeletons.
    Creates exported_json_data/SoF2_All.json in the given basepath.
    """
    try:
        # Clear the exported_json_data folder before exporting again
        export_dir = os.path.join(basepath, "exported_json_data")
        if os.path.isdir(export_dir):
            for filename in os.listdir(export_dir):
                file_path = os.path.join(export_dir, filename)
                try:
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                    elif os.path.isdir(file_path):
                        # Remove all files in subdirectory, then the subdirectory itself
                        for subfile in os.listdir(file_path):
                            subfile_path = os.path.join(file_path, subfile)
                            if os.path.isfile(subfile_path):
                                os.remove(subfile_path)
                        os.rmdir(file_path)
                except Exception as e:
                    print(f"Error clearing {file_path}: {e}")

        # Ensure export directory exists
        os.makedirs(export_dir, exist_ok=True)

        # Weapons and items
        _, weapons = DataCache.get_weapon_enum_items(basepath)
        _, items_data = DataCache.get_default_item_file(basepath, "ext_data/SOF2.item")

        # NPCs
        _, npcs_data = DataCache.get_npcs_folder_data_cached(basepath)

        # Prepare skin_data export directory
        skin_data_dir = os.path.join(export_dir, "skin_data")
        os.makedirs(skin_data_dir, exist_ok=True)

        # Enrich each CharacterTemplate's Skin in npcs_data with skin_data by reading .g2skin files directly
        for _npc_filename, npc_content in (npcs_data or {}).items():
            char_templates = npc_content.get("CharacterTemplate", [])
            if not isinstance(char_templates, list):
                char_templates = [char_templates]
            for ct in char_templates:
                try:
                    skin_field = ct.get("Skin", None)

                    def resolve_skin_data(file_value: str):
                        if not file_value:
                            return None
                        # Try both common locations
                        candidates = [
                            os.path.join(
                                basepath,
                                "models",
                                "characters",
                                "skins",
                                f"{file_value}.g2skin",
                            ),
                            os.path.join(
                                basepath, "characters", "skins", f"{file_value}.g2skin"
                            ),
                        ]
                        for path in candidates:
                            if os.path.isfile(path):
                                try:
                                    with open(
                                        path, "r", encoding="utf-8", errors="ignore"
                                    ) as f:
                                        return parse_g2skin_to_json(f.read())
                                except Exception:
                                    return None
                        return None

                    if isinstance(skin_field, dict):
                        fv = skin_field.get("File")
                        resolved = resolve_skin_data(fv)
                        if resolved is not None and fv:
                            out_path = os.path.join(skin_data_dir, f"{fv}.json")
                            with open(out_path, "w", encoding="utf-8") as f:
                                json.dump(resolved, f, indent=2, ensure_ascii=False)
                    elif isinstance(skin_field, list):
                        for skin_entry in skin_field:
                            if isinstance(skin_entry, dict):
                                fv = skin_entry.get("File")
                                resolved = resolve_skin_data(fv)
                                if resolved is not None and fv:
                                    out_path = os.path.join(skin_data_dir, f"{fv}.json")
                                    with open(out_path, "w", encoding="utf-8") as f:
                                        json.dump(
                                            resolved, f, indent=2, ensure_ascii=False
                                        )
                except Exception:
                    # fail-soft; do not attach at ct level
                    pass

        # Skeletons from parsing .skl files
        skl_data = _load_all_skl_data(basepath)

        # Use existing generators for legacy exports only
        if generate_separate:
            DataCache.generate_json_results(weapons, items_data, basepath)
            DataCache.generate_npc_json_results(npcs_data, basepath)
            if skl_data:
                DataCache.generate_individual_skl_files(skl_data, basepath)

        skl_count = len(skl_data or [])

        msg = (
            f"Successfully exported legacy JSONs: "
            f"weapons={len(weapons)}, items={len(items_data.get('items', []))}, "
            f"npcs={len(npcs_data)}, skeletons={skl_count}"
        )
        return (
            True,
            msg,
            {
                "weapons": weapons,
                "items": items_data,
                "npcs": npcs_data,
                "skeletons": skl_data,
            },
        )

    except Exception as e:
        err = f"Error exporting combined JSON: {str(e)}"
        print(err)
        return False, err, {}
