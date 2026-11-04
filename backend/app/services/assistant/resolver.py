import unicodedata


class Clarification(ValueError):
    pass


def normalized(value: str):
    return " ".join(
        "".join(c for c in unicodedata.normalize("NFKD", value) if not unicodedata.combining(c))
        .casefold()
        .split()
    )


def resolve_name(name, candidates):
    matches = [row for row in candidates if normalized(row[1]) == normalized(name)]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise Clarification(f"Hay varias coincidencias para «{name}». Indica el departamento.")
    raise Clarification(
        f"No encontré «{name}» en el catálogo. Revisa el nombre del cultivo o territorio."
    )
