"""JSON merge utility for handling partial updates."""

from typing import Dict, Any


def merge_json(existing_data: Dict[str, Any], new_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge new data into existing JSON, handling field mapping.
    
    Maps fields with 'new_' prefix to corresponding fields without prefix.
    For example: 'new_price' -> 'price'
    
    Args:
        existing_data: Existing JSON data
        new_data: New data to merge (may contain 'new_*' fields)
        
    Returns:
        Merged JSON data
    """
    # Create a copy of existing data
    merged = existing_data.copy()
    
    # Process new_data fields
    for key, value in new_data.items():
        # Map 'new_*' fields to corresponding fields without prefix
        if key.startswith('new_'):
            # Remove 'new_' prefix
            mapped_key = key[4:]  # Remove 'new_' (4 characters)
            merged[mapped_key] = value
        else:
            # Regular field, update directly
            merged[key] = value
    
    return merged


def map_new_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map all 'new_*' fields to corresponding fields without prefix.
    
    This is useful when processing change_type: "changed" updates.
    
    Args:
        data: Data dictionary that may contain 'new_*' fields
        
    Returns:
        Dictionary with mapped fields
    """
    mapped = {}
    
    for key, value in data.items():
        if key.startswith('new_'):
            # Map 'new_*' to field without prefix
            mapped_key = key[4:]  # Remove 'new_' (4 characters)
            mapped[mapped_key] = value
        else:
            # Keep original field
            mapped[key] = value
    
    return mapped
