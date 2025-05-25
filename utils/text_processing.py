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

    name_with_hyphens = unidecode.unidecode(name.lower().replace(".", " ").strip())
    name_with_hyphens = " ".join(name_with_hyphens.split())

    return name_with_hyphens
