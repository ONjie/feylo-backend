from qrcode import QRCode, constants
import base64
from io import BytesIO
from src.utils.config import settings


def generate_qr_code(transaction_id: str) -> str:
    checkout_url = f"{settings.BASE_URL}/api/v1/checkout/{transaction_id}"

    qr = QRCode(
        error_correction=constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(checkout_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")

    return base64.b64encode(buf.getvalue()).decode()
