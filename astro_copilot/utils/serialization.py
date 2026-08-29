"""
JSON serialization utilities for astronomical data structures.
Ensures full compatibility with standard JSON serializers and LLM context formatters.
"""

from typing import Any
import math
import numpy as np


def clean_for_json(obj: Any) -> Any:
    """
    Recursively converts numpy types, astropy types, NaNs, and infinities
    into standard Python JSON-serializable structures.
    """
    if obj is None:
        return None

    # Handle float / numeric NaNs and Infs
    if isinstance(obj, (float, np.floating)):
        if math.isnan(obj) or np.isnan(obj):
            return None
        if math.isinf(obj) or np.isinf(obj):
            return None
        return float(obj)

    # Handle boolean types before integer types (since bool is a subclass of int in Python)
    if isinstance(obj, (bool, np.bool_)):
        return bool(obj)
    if isinstance(obj, (int, np.integer)):
        return int(obj)

    # Handle numpy arrays
    if isinstance(obj, np.ndarray):
        if obj.ndim == 0:
            return clean_for_json(obj.item())
        return [clean_for_json(item) for item in obj.tolist()]

    # Handle Astropy Quantity
    if hasattr(obj, "unit") and hasattr(obj, "value"):
        return clean_for_json(obj.value)

    # Handle Astropy Table or Table Row
    if hasattr(obj, "as_array"):
        return clean_for_json(dict(zip(obj.colnames, [list(obj[col]) for col in obj.colnames])))

    # Handle dictionaries
    if isinstance(obj, dict):
        return {str(k): clean_for_json(v) for k, v in obj.items()}

    # Handle lists, tuples, sets
    if isinstance(obj, (list, tuple, set)):
        return [clean_for_json(item) for item in obj]

    # Handle strings and basic types
    if isinstance(obj, (str, bytes)):
        if isinstance(obj, bytes):
            return obj.decode("utf-8", errors="replace")
        return str(obj)

    # Fallback to string representation if unknown
    try:
        return str(obj)
    except Exception:
        return None
