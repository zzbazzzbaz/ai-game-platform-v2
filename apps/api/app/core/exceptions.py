class AppError(Exception):
    status_code = 500


class ValidationError(AppError):
    status_code = 400


class ForbiddenError(AppError):
    status_code = 403


class NotFoundError(AppError):
    status_code = 404


class UpstreamError(AppError):
    status_code = 502
