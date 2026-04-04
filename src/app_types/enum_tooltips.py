from enum import Enum

from app_domain.controlsys import PerformanceIndex


class PerformanceIndexDescription(Enum):
    ITAE = "Integral of Time-weighted Absolute Error"
    IAE = "Integral of Absolute Error"
    ITSE = "Integral of Time-weighted Squared Error"
    ISE = "Integral of Squared Error"


def get_performance_tooltip(value: PerformanceIndex) -> PerformanceIndexDescription:
    """Map a PerformanceIndex value to its corresponding tooltip enum.

    This function converts a PerformanceIndex enum member into the
    matching PerformanceIndexDescription enum member by using the
    shared enum name.

    Args:
        value: The PerformanceIndex enum value for which the tooltip
            description is requested.

    Returns:
        The corresponding PerformanceIndexDescription enum member.

    Raises:
        KeyError: If no matching member exists in PerformanceIndexDescription.
    """
    return PerformanceIndexDescription[value.name]


def validate_enum_mapping(
        base_enum: type[Enum],
        description_enum: type[Enum]
) -> None:
    """Ensure both enums have identical member names.

    Args:
        base_enum: Primary enum (e.g., PerformanceIndex).
        description_enum: Secondary enum with matching members.

    Raises:
        ValueError: If enum members do not match.
    """
    base_names = {e.name for e in base_enum}
    desc_names = {e.name for e in description_enum}

    if base_names != desc_names:
        raise ValueError(
            f"Enum mismatch:\n"
            f"{base_enum.__name__}: {base_names}\n"
            f"{description_enum.__name__}: {desc_names}"
        )
