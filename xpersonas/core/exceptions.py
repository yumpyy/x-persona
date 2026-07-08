"""Custom exception hierarchy for xpersonas."""


class xpersonasError(Exception):
    """Base exception for all xpersonas errors."""


class ConfigError(xpersonasError):
    """Configuration loading or validation error."""


class StorageError(xpersonasError):
    """Database or storage error."""


class PlatformError(xpersonasError):
    """Platform adapter error."""


class AuthenticationError(PlatformError):
    """Platform authentication failed."""


class ActionError(PlatformError):
    """Platform action (like, reply, etc.) failed."""


class RateLimitError(PlatformError):
    """Platform rate limit exceeded."""


class PersonaError(xpersonasError):
    """Persona loading or validation error."""


class AgentError(xpersonasError):
    """Agent runtime error."""


class AdapterNotAvailable(PlatformError):
    """Requested platform adapter is not registered."""
