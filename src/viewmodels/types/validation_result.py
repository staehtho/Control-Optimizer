from dataclasses import dataclass


@dataclass
class ValidationResult:
    valid: bool
    message: str | None = None
