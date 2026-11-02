class EmployeeNotFound(Exception):
    """Raised when no employee has the requested id (-> 404)."""


class DuplicateEmail(Exception):
    """Raised when another employee already uses the email (-> 409)."""