import hashlib
import hmac
import secrets


def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("ascii"), 600_000)
    return f"pbkdf2:sha256:600000${salt}${digest.hex()}"


def verify_password(password, stored):
    if not stored:
        return False
    if stored.startswith("scrypt:"):
        try:
            method, salt, expected = stored.split("$", 2)
            _, n, r, p = method.split(":")
            digest = hashlib.scrypt(
                password.encode("utf-8"),
                salt=salt.encode("utf-8"),
                n=int(n),
                r=int(r),
                p=int(p),
                dklen=len(bytes.fromhex(expected)),
                maxmem=128 * 1024 * 1024,
            )
            return hmac.compare_digest(digest.hex(), expected)
        except (ValueError, TypeError):
            return False
    if stored.startswith("pbkdf2:"):
        try:
            method, salt, expected = stored.split("$", 2)
            _, algorithm, iterations = method.split(":")
            digest = hashlib.pbkdf2_hmac(
                algorithm,
                password.encode("utf-8"),
                salt.encode("utf-8"),
                int(iterations),
                dklen=len(bytes.fromhex(expected)),
            )
            return hmac.compare_digest(digest.hex(), expected)
        except (ValueError, TypeError):
            return False
    return hmac.compare_digest(password, stored)