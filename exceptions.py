class StatusCodeException(Exception):
    """Срабатывает при неполадках в доступе к API."""
    pass

class JSONCodeException(Exception):
    """Срабатывает при неполадках в переводе в json."""
    pass
