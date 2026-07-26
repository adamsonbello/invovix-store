"""2FA TOTP helpers (pyotp + QR code data URL)."""
import io
import base64
import pyotp
import qrcode


def new_secret() -> str:
    return pyotp.random_base32()


def provisioning_uri(secret: str, email: str, issuer: str = "Invovix") -> str:
    return pyotp.totp.TOTP(secret).provisioning_uri(name=email, issuer_name=issuer)


def qr_data_url(uri: str) -> str:
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("utf-8")


def verify_code(secret: str, code: str) -> bool:
    if not secret or not code:
        return False
    try:
        return pyotp.TOTP(secret).verify(str(code).strip(), valid_window=1)
    except Exception:
        return False
