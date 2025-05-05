import unidecode


def normalize_name(name: str) -> str:
    """Normalizes author names for exact comparison.

    Args:
        name: The author name to normalize

    Returns:
        Normalized name string with consistent formatting
    """
    if not isinstance(name, str):
        return ""
    name = unidecode.unidecode(name.lower().replace("-", " ").replace(".", " ").strip())
    return " ".join(name.split())
