def wiki_name(name):
    """Converts a name to a wiki name.

    Args:
        name (str): The name to convert.
    """
    new_name = name.replace("_", " ")
    new_name = new_name[0].upper() + new_name[1:]
    new_name = new_name.strip()
    return new_name

def wiki_location(name):
    """Converts a name to a wiki location, as in what the URL would be.

    Args:
        name (str): The name to convert.
    """
    new_name = name.replace(" ", "_")
    return new_name[0].upper() + new_name[1:]

def cacao_property(name):
    """Converts a name to a cacao property name. Lowercase and underscores.

    Args:
        name (str): The name to convert.
    """
    new_name = name.replace(" ", "_")
    return new_name.lower()

def sappan_property(name):
    """Converts a name to a sappan property name. Lowercase first letter and snake case.

    Args:
        name (str): The name to convert.
    """
    new_name = name.replace(" ", "")
    return new_name[0].lower() + new_name[1:]