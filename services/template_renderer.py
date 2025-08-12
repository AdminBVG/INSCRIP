import re
from datetime import datetime
from zoneinfo import ZoneInfo

TZ_ECUADOR = ZoneInfo('America/Guayaquil')

def normalize_var(name: str) -> str:
    """Normalize field name to variable name (A_Z_0_9)."""
    return re.sub(r'[^A-Z0-9]', '_', name.upper())


def render_text(template: str, variables: dict) -> str:
    """Replace [VARIABLE] patterns in template using provided variables.

    Supports [FECHA] with optional format e.g. [FECHA:YYYY-MM-DD HH:mm].
    Dates are rendered in Ecuador timezone.
    """
    if not template:
        return ''

    def repl(match: re.Match) -> str:
        key = match.group(1)
        if key.startswith('FECHA'):
            fmt = '%Y-%m-%d'
            if ':' in key:
                _, fmt = key.split(':', 1)
            return datetime.now(TZ_ECUADOR).strftime(fmt)
        return str(variables.get(key, match.group(0)))

    return re.sub(r'\[([A-Z0-9:_-]+)\]', repl, template)
