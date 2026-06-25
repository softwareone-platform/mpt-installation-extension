from http import HTTPStatus

from mpt_api_client.exceptions import MPTError, MPTHttpError, MPTMaxRetryError


def is_deferrable_error(error: MPTError) -> bool:
    """Return whether an MPT error should defer the pipeline."""
    if isinstance(error, MPTMaxRetryError):
        return True

    if not isinstance(error, MPTHttpError):
        return False

    return (
        error.status_code
        in {
            HTTPStatus.REQUEST_TIMEOUT,
            HTTPStatus.TOO_MANY_REQUESTS,
        }
        or error.status_code >= HTTPStatus.INTERNAL_SERVER_ERROR
    )


class RecoverableInstallationError(Exception):
    """Recoverable installation failure that should defer the pipeline."""

    def __init__(self, extension_id: str, error: MPTError) -> None:
        self.extension_id = extension_id
        super().__init__(str(error))
