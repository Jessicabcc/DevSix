import re


_EMAIL_RE = re.compile(
    r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$"
)


def is_valid_email(email):
    """Retorna True quando o e-mail possui um formato válido para cadastro."""
    email = str(email or "").strip()
    if not email or len(email) > 254:
        return False
    return bool(_EMAIL_RE.fullmatch(email))