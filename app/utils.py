from urllib.parse import quote
from flask import current_app

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
