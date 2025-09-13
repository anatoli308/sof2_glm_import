"""
SOF2 Path Mapper - Clean refactored approach for mapping SKL and Frames data
"""
import os
from typing import Dict, Any, Optional, List, Tuple
from copy import deepcopy


class PathMapper:
    """
    Clean, refactored path mapper for SOF2 SKL and Frames data.
    Handles different path formats and provides robust matching.
    """
    
    def __init__(self):
        self.debug = True
    
    def normalize_path(self, path: str) -> str:
        """
        Normalize a path for matching by:
        - Converting backslashes to forward slashes
        - Converting to lowercase
        - Removing drive letters (m:, c:, etc.)
        - Removing common prefixes (_animation/xsi/, animation/xsi/, etc.)
        - Cleaning up repeated slashes
        """
        if not isinstance(path, str) or not path.strip():
            return ""
        
        # Convert backslashes to forward slashes and lowercase
        normalized = path.replace("\\", "/").lower().strip()
        
        # Remove drive letters (m:, c:, etc.)
        if len(normalized) >= 2 and normalized[1] == ":":
            normalized = normalized[2:]
        
        # Remove leading slash if present
        if normalized.startswith("/"):
            normalized = normalized[1:]
        
        # Remove common prefixes
        prefixes_to_remove = [
            "_animation/xsi/",
            "animation/xsi/", 
            "_animation/",
            "animation/"
        ]
        
        for prefix in prefixes_to_remove:
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):]
                break
        
        # Clean up repeated slashes
        while "//" in normalized:
            normalized = normalized.replace("//", "/")
        
        # Remove leading/trailing slashes
        normalized = normalized.strip("/")
        
        return normalized
    
    def find_best_match(self, skl_path: str, frames_keys: List[str]) -> Optional[str]:
        """
        Find the best matching frame key for a given SKL path.
        Returns the original frame key (not normalized) if found.
        """
        if not skl_path or not frames_keys:
            return None
        
        skl_normalized = self.normalize_path(skl_path)
        if not skl_normalized:
            return None
        
        # Create list of (original_key, normalized_key) tuples
        frame_candidates = []
        for frame_key in frames_keys:
            frame_normalized = self.normalize_path(frame_key)
            if frame_normalized:
                frame_candidates.append((frame_key, frame_normalized))
        
        if not frame_candidates:
            return None
        
        # 1. Exact match
        for orig_key, norm_key in frame_candidates:
            if norm_key == skl_normalized:
                if self.debug:
                    print(f"✓ EXACT MATCH: '{skl_path}' -> '{orig_key}'")
                return orig_key
        
        # 2. SKL path is contained in frame path
        contains_matches = [orig_key for orig_key, norm_key in frame_candidates 
                          if skl_normalized in norm_key]
        if len(contains_matches) == 1:
            if self.debug:
                print(f"✓ CONTAINS MATCH: '{skl_path}' -> '{contains_matches[0]}'")
            return contains_matches[0]
        elif len(contains_matches) > 1:
            if self.debug:
                print(f"⚠ MULTIPLE CONTAINS MATCHES for '{skl_path}': {contains_matches}")
            return contains_matches[0]  # Return first match
        
        # 3. Frame path is contained in SKL path
        reverse_matches = [orig_key for orig_key, norm_key in frame_candidates 
                          if norm_key in skl_normalized]
        if len(reverse_matches) == 1:
            if self.debug:
                print(f"✓ REVERSE MATCH: '{skl_path}' -> '{reverse_matches[0]}'")
            return reverse_matches[0]
        elif len(reverse_matches) > 1:
            if self.debug:
                print(f"⚠ MULTIPLE REVERSE MATCHES for '{skl_path}': {reverse_matches}")
            return reverse_matches[0]
        
        # 4. Ends with match
        ends_matches = [orig_key for orig_key, norm_key in frame_candidates 
                       if norm_key.endswith(skl_normalized)]
        if len(ends_matches) == 1:
            if self.debug:
                print(f"✓ ENDS WITH MATCH: '{skl_path}' -> '{ends_matches[0]}'")
            return ends_matches[0]
        elif len(ends_matches) > 1:
            if self.debug:
                print(f"⚠ MULTIPLE ENDS WITH MATCHES for '{skl_path}': {ends_matches}")
            return ends_matches[0]
        
        # 5. Starts with match
        starts_matches = [orig_key for orig_key, norm_key in frame_candidates 
                         if skl_normalized.startswith(norm_key)]
        if len(starts_matches) == 1:
            if self.debug:
                print(f"✓ STARTS WITH MATCH: '{skl_path}' -> '{starts_matches[0]}'")
            return starts_matches[0]
        elif len(starts_matches) > 1:
            if self.debug:
                print(f"⚠ MULTIPLE STARTS WITH MATCHES for '{skl_path}': {starts_matches}")
            return starts_matches[0]
        
        # 6. Basename match
        skl_basename = os.path.basename(skl_normalized)
        basename_matches = [orig_key for orig_key, norm_key in frame_candidates 
                           if os.path.basename(norm_key) == skl_basename]
        if len(basename_matches) == 1:
            if self.debug:
                print(f"✓ BASENAME MATCH: '{skl_path}' -> '{basename_matches[0]}'")
            return basename_matches[0]
        elif len(basename_matches) > 1:
            if self.debug:
                print(f"⚠ MULTIPLE BASENAME MATCHES for '{skl_path}': {basename_matches}")
            return basename_matches[0]
        
        # 7. Fuzzy basename match (without extension)
        skl_name_no_ext = os.path.splitext(skl_basename)[0]
        fuzzy_matches = [orig_key for orig_key, norm_key in frame_candidates 
                        if os.path.splitext(os.path.basename(norm_key))[0] == skl_name_no_ext]
        if len(fuzzy_matches) == 1:
            if self.debug:
                print(f"✓ FUZZY MATCH: '{skl_path}' -> '{fuzzy_matches[0]}'")
            return fuzzy_matches[0]
        elif len(fuzzy_matches) > 1:
            if self.debug:
                print(f"⚠ MULTIPLE FUZZY MATCHES for '{skl_path}': {fuzzy_matches}")
            return fuzzy_matches[0]
        
        if self.debug:
            print(f"✗ NO MATCH FOUND for '{skl_path}'")
        return None
    
    def map_frames_into_skl(self, data_skl: Dict[str, Any], data_frames: Dict[str, Any], 
                           inplace: bool = False) -> Dict[str, Any]:
        """
        Main mapping function that replaces .xsi file paths in SKL data with 
        mapped frame data from the frames dictionary.
        
        Args:
            data_skl: Parsed SKL data (nested dicts/lists)
            data_frames: Parsed frames data (dict with .xsi paths as keys)
            inplace: If True, modify data_skl in place; if False, work on a copy
            
        Returns:
            Mapped SKL data with frame information
        """
        if not inplace:
            data_skl = deepcopy(data_skl)
        
        # Extract all frame keys for matching
        frames_keys = list(data_frames.keys())
        
        if self.debug:
            print(f"Mapping {len(frames_keys)} frame keys into SKL data...")
            print(f"Sample frame keys: {frames_keys[:3]}")
        
        # Walk through the SKL data and replace .xsi paths
        def walk_and_map(obj, path=""):
            if isinstance(obj, dict):
                for key, value in list(obj.items()):
                    current_path = f"{path}.{key}" if path else key
                    if self._is_xsi_string(value):
                        matched_key = self.find_best_match(value, frames_keys)
                        if matched_key:
                            obj[key] = {
                                "file": value,
                                "frames": data_frames[matched_key]
                            }
                            if self.debug:
                                print(f"Mapped at {current_path}: '{value}' -> frames data")
                        else:
                            if self.debug:
                                print(f"No match at {current_path}: '{value}'")
                    elif isinstance(value, (dict, list)):
                        walk_and_map(value, current_path)
                    elif isinstance(value, str) and ".xsi" in value.lower():
                        # Try to extract .xsi path from string
                        xsi_paths = self._extract_xsi_paths(value)
                        for xsi_path in xsi_paths:
                            matched_key = self.find_best_match(xsi_path, frames_keys)
                            if matched_key:
                                obj[key] = {
                                    "file": value,
                                    "frames": data_frames[matched_key]
                                }
                                if self.debug:
                                    print(f"Mapped embedded at {current_path}: '{xsi_path}' -> frames data")
                                break
                        else:
                            if self.debug:
                                print(f"No match for embedded paths at {current_path}: {xsi_paths}")
            
            elif isinstance(obj, list):
                for idx, item in enumerate(obj):
                    current_path = f"{path}[{idx}]" if path else f"[{idx}]"
                    if self._is_xsi_string(item):
                        matched_key = self.find_best_match(item, frames_keys)
                        if matched_key:
                            obj[idx] = {
                                "file": item,
                                "frames": data_frames[matched_key]
                            }
                            if self.debug:
                                print(f"Mapped at {current_path}: '{item}' -> frames data")
                        else:
                            if self.debug:
                                print(f"No match at {current_path}: '{item}'")
                    elif isinstance(item, (dict, list)):
                        walk_and_map(item, current_path)
                    elif isinstance(item, str) and ".xsi" in item.lower():
                        xsi_paths = self._extract_xsi_paths(item)
                        for xsi_path in xsi_paths:
                            matched_key = self.find_best_match(xsi_path, frames_keys)
                            if matched_key:
                                obj[idx] = {
                                    "file": item,
                                    "frames": data_frames[matched_key]
                                }
                                if self.debug:
                                    print(f"Mapped embedded at {current_path}: '{xsi_path}' -> frames data")
                                break
                        else:
                            if self.debug:
                                print(f"No match for embedded paths at {current_path}: {xsi_paths}")
        
        walk_and_map(data_skl)
        return data_skl
    
    def _is_xsi_string(self, value: Any) -> bool:
        """Check if a value is a string ending with .xsi"""
        return isinstance(value, str) and value.lower().strip().endswith(".xsi")
    
    def _extract_xsi_paths(self, text: str) -> List[str]:
        """Extract .xsi file paths from a string"""
        if not isinstance(text, str):
            return []
        
        # Split on whitespace and find tokens ending with .xsi
        tokens = [token for token in text.replace("\\", "/").split() 
                 if token.lower().endswith(".xsi")]
        return tokens


# Convenience function for easy usage
def map_frames_into_skl(data_skl: Dict[str, Any], data_frames: Dict[str, Any], 
                       inplace: bool = False, debug: bool = True) -> Dict[str, Any]:
    """
    Convenience function to map frames into SKL data.
    
    Args:
        data_skl: Parsed SKL data
        data_frames: Parsed frames data  
        inplace: If True, modify data_skl in place
        debug: If True, print debug information
        
    Returns:
        Mapped SKL data
    """
    mapper = PathMapper()
    mapper.debug = debug
    return mapper.map_frames_into_skl(data_skl, data_frames, inplace)
