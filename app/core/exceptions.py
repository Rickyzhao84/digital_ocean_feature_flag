"""
Custom exception classes for the feature flag service.
These exceptions are used throughout the application for proper error handling
and are mapped to appropriate HTTP status codes in the routes.
"""


class FlagException(Exception):
    """Base exception for all flag-related errors."""
    pass


class InvalidRuleDefinitionError(FlagException):
    """Raised when a rule definition is invalid (wrong type, missing parameters, etc.)."""
    pass


class InvalidContextError(FlagException):
    """Raised when the evaluation context is invalid or malformed."""
    pass


class InvalidPercentageError(FlagException):
    """Raised when a percentage value is outside the valid range (0-100)."""
    pass


class FlagNotFoundError(FlagException):
    """Raised when a requested flag does not exist."""
    pass


class DuplicateFlagError(FlagException):
    """Raised when attempting to create a flag with a name that already exists."""
    pass


class InvalidFlagNameError(FlagException):
    """Raised when a flag name is invalid (empty, too long, invalid characters)."""
    pass


class InvalidOperatorError(FlagException):
    """Raised when an unsupported operator is used in a rule."""
    pass


class DatabaseError(FlagException):
    """Raised when a database operation fails."""
    pass
