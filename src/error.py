class ScagDrfsError(Exception):
    """Base class for all SCAGDRFS specific errors."""

    pass


class ScagDrfsDateRangeError(ScagDrfsError):
    """This error is raised when the start date for processing is after the end date."""

    pass


class ScagDrfsFileError(ScagDrfsError):
    """This error is raised when the files detected are not expected."""

    pass
