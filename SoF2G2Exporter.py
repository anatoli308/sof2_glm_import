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

def _find_character_templates_using_skin(skin_name: str, npcs_data: dict) -> list:
    """Find all CharacterTemplates that use the given skin_name."""
    found_templates = []
    for _npc_filename, npc_content in (npcs_data or {}).items():
        char_templates = npc_content.get("CharacterTemplate", [])
        if not isinstance(char_templates, list):
            char_templates = [char_templates]
        for ct in char_templates:
            skin_field = ct.get("Skin", None)
            if isinstance(skin_field, dict):
                fv = skin_field.get("File")
                if fv == skin_name:
                    found_templates.append(ct)
            elif isinstance(skin_field, list):
                for skin_entry in skin_field:
                    if isinstance(skin_entry, dict):
                        fv = skin_entry.get("File")
                        if fv == skin_name:
                            found_templates.append(ct)
    return found_templates

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

        # get all files from basepath/models/characters/skins
        skin_source_dir = os.path.join(basepath, "models", "characters", "skins")
        skin_data_files = os.listdir(skin_source_dir)
        #for each file in skin_data_files, use parse_g2skin_to_json to parse and save as json inside skin_data_dir
        for skin_file in skin_data_files:
            if not skin_file.endswith(".g2skin"):
                continue
            skin_name = os.path.splitext(skin_file)[0]
            skin_file_path = os.path.join(skin_source_dir, skin_file)
            try:
                with open(skin_file_path, "r", encoding="utf-8", errors="ignore") as f:
                    parsed_skin = parse_g2skin_to_json(f.read())

                    found_character_templates = _find_character_templates_using_skin(skin_name, npcs_data)
                    #das sind skin varianten (NPC_NOitems , NPC_withItems, NPC_Elite etc)
                    found_inventory = {
                        "ct_inventory": None,
                        "skin_inventory": None,
                    }
                    for ct in found_character_templates:
                        ct_inventory = ct.get("Inventory", None)
                        #print(f"Found ct-inventory for skin {skin_name}: {ct_inventory}")
                        found_inventory["ct_inventory"] = ct_inventory
                        # for each skin in ct get the "Skin" Inventories
                        ct_skins = ct.get("Skin", [])
                        if isinstance(ct_skins, list):
                            #get the skin for this skin_name
                            for skin_entry in ct_skins:
                                fv = skin_entry.get("File")
                                if fv == skin_name:
                                    skin_inventory = skin_entry.get("Inventory", None)
                                    #print(f"Found skin-inventory for skin {skin_name}: {skin_inventory}")
                                    found_inventory["skin_inventory"] = skin_inventory
                        elif isinstance(ct_skins, dict):
                            fv = ct_skins.get("File")
                            if fv == skin_name:
                                skin_inventory = ct_skins.get("Inventory", None)
                                #print(f"Found skin-inventory for skin {skin_name}: {skin_inventory}")
                                found_inventory["skin_inventory"] = skin_inventory
                        else:
                            print(f"ct_skins is neither list nor dict for skin {skin_name}: {ct_skins}")
                        break  # only need the first matching CharacterTemplate
                    parsed_skin["found_inventories"] = found_inventory
                    print(f"template length for skin {skin_name}: {len(found_character_templates)}")
                out_path = os.path.join(skin_data_dir, f"{skin_name}.json")
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(parsed_skin, f, indent=2, ensure_ascii=False)
            except Exception:
                # fail-soft; do not stop processing other skins
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
