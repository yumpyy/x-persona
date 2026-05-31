"""Custom exception hierarchy for X automation utilities.

A structured exception tree lets callers distinguish between
authentication failures, navigation issues, DOM changes, and
action errors without resorting to string-matching.
"""


class XPersonaError(Exception):
    """Base exception for all x-persona utility errors."""


class XAuthError(XPersonaError):
    """Authentication or session state error.

    Raised when auth state is missing, expired, or the session
    has been invalidated by X.
    """


class XNavigationError(XPersonaError):
    """Failed to navigate to the expected URL within the timeout.

    Usually means X redirected (e.g. to a login wall) or the
    page structure changed.
    """


class XElementNotFoundError(XPersonaError):
    """An expected DOM element was not found.

    Most likely cause: X shipped a DOM update and the selectors
    in `selectors.py` need refreshing.
    """


class XActionError(XPersonaError):
    """A high-level action (like, post, reply …) failed to complete.

    The action may have partially succeeded — callers should verify
    state before retrying.
    """


class XMediaUploadError(XActionError):
    """Failed to upload one or more media attachments.

    Could be a file-type rejection, size limit, or a transient
    upload-service failure.
    """


class XRateLimitError(XPersonaError):
    """X returned a rate-limit signal.

    Callers should back off before retrying.
    """
