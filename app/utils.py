import re
import secrets
import string
from urllib.parse import quote
from flask import current_app
from app.models.user import User

REGISTER_MESSAGE = (
    "Halo Admin Siwaruk,\n\n"
    "Saya ingin mengajukan pembuatan akun Siwaruk.\n\n"
    "Nama:\n"
    "Nama Usaha:\n"
    "Nomor WhatsApp:\n\n"
    "Terima kasih."
)

FORGOT_PASSWORD_MESSAGE = (
    "Halo Admin Siwaruk,\n\n"
    "Saya mengalami kendala login dan ingin melakukan reset password.\n\n"
    "Username:\n"
    "Nama Usaha:\n\n"
    "Terima kasih."
)


def get_whatsapp_link(message_type: str) -> str:
    """
    Generate an encoded WhatsApp URL for contacting admin.

    :param message_type: 'register' or 'forgot_password'
    :return: Full WhatsApp URL string with pre-filled encoded text message.
    """
    wa_number = current_app.config.get("WHATSAPP_ADMIN", "628xxxxxxxxxx")

    if message_type == "register":
        message_text = REGISTER_MESSAGE
    elif message_type == "forgot_password":
        message_text = FORGOT_PASSWORD_MESSAGE
    else:
        message_text = ""

    encoded_text = quote(message_text)
    return f"https://wa.me/{wa_number}?text={encoded_text}"


def generate_unique_username(business_name: str) -> str:
    """
    Generate a clean, unique username derived from the business name.
    Example: 'Warung Berkah' -> 'warungberkah'.
    Appends incremental numbers if username exists ('warungberkah2', etc.).
    """
    base_username = re.sub(r'[^a-zA-Z0-9]', '', business_name.lower())
    if not base_username:
        base_username = "user"

    candidate = base_username
    counter = 2
    while User.query.filter_by(username=candidate).first() is not None:
        candidate = f"{base_username}{counter}"
        counter += 1

    return candidate


def generate_secure_password(length: int = 12) -> str:
    """
    Generate a random password using secrets module.
    Guarantees at least 1 uppercase letter, 1 lowercase letter, and 1 digit.
    Minimum length: 10.
    """
    if length < 10:
        length = 10

    uppercase = string.ascii_uppercase
    lowercase = string.ascii_lowercase
    digits = string.digits
    alphabet = uppercase + lowercase + digits

    while True:
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
        if (any(c in uppercase for c in password) and
            any(c in lowercase for c in password) and
            any(c in digits for c in password)):
            return password
