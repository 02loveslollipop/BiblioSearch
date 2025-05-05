from typing import Any

class ScopusSearchEquation(str):
    """
    String wrapper for Scopus search equations. Validates basic structure.
    """
    BOOLEAN_OPERATORS = {'AND', 'OR', 'NOT'}

    def __new__(cls, value: Any) -> 'ScopusSearchEquation':
        obj = str.__new__(cls, value)
        obj._validate()
        return obj

    def _validate(self) -> None:
        if not self or not self.strip():
            raise ValueError("Search equation cannot be empty.")
        # Basic check: must contain at least one boolean operator or field()
        if not any(op in self.upper() for op in self.BOOLEAN_OPERATORS) and '()' not in self:
            raise ValueError("Search equation must contain at least one boolean operator or field().")

