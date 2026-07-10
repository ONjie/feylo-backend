import base64
import cv2
import numpy as np
import pytest
from src.utils.config import settings
from src.payment.payment_service import generate_qr_code


class TestPaymentService:


    @pytest.mark.parametrize(
        'transaction_id',
        [
            pytest.param('txn_1234', id='generate_qr_code_success_one'),
            pytest.param('txn_2468', id='generate_qr_code_success_two'),
            pytest.param('txn_1357', id='generate_qr_code_success_three')
        ]
    )
    def test_generate_qr_code(self, transaction_id):
        qr_base64 = generate_qr_code(transaction_id)

        image_bytes = base64.b64decode(qr_base64)

        image = cv2.imdecode(
            np.frombuffer(image_bytes, dtype=np.uint8),
            cv2.IMREAD_COLOR,
        )

        detector = cv2.QRCodeDetector()
        data, _, _ = detector.detectAndDecode(image)

        assert data == f"{settings.BASE_URL}/checkout/{transaction_id}"