"""
Wildcard Filter Module
Provides substring and wildcard pattern matching for layer filtering.
Supports ? (single character) wildcard and substring matching.
"""

import re


class WildcardFilter:
    """Handles pattern matching for filtering with ? wildcard support."""
    
    @staticmethod
    def matches_pattern(text, pattern):
        """
        Check if text matches the pattern.
        Uses substring matching with optional ? wildcard for single character.
        
        Args:
            text: Text to check
            pattern: Pattern with optional ? wildcards
            
        Returns:
            bool: True if text matches pattern, False otherwise
        """
        if not pattern:
            return True
        
        # Convert ? wildcard to regex . (single character)
        # Escape special regex characters first, then replace ?
        regex_pattern = re.escape(pattern.lower())
        regex_pattern = regex_pattern.replace(r'\?', '.')
        
        # Match anywhere in the string (substring matching)
        return bool(re.search(regex_pattern, text.lower()))
    
    @staticmethod
    def filter_items(items, pattern):
        """
        Filter a list of items based on pattern.
        
        Args:
            items: List of items to filter
            pattern: Pattern with optional ? wildcards
            
        Returns:
            list: Filtered items matching the pattern
        """
        if not pattern:
            return items
        return [item for item in items if WildcardFilter.matches_pattern(item, pattern)]
