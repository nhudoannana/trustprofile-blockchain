"""Module wallet — tạo cặp khoá ECDSA, ký và xác minh chữ ký số.

Mục đích: mô phỏng ví blockchain, cho phép Issuer ký credential
và Verifier kiểm chứng tính toàn vẹn mà không cần bên thứ ba.
"""

from dataclasses import dataclass

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.exceptions import InvalidSignature

from blockchain.hash import sha256_hex


@dataclass
class Wallet:
    """Ví chứa cặp khoá ECDSA và địa chỉ dẫn xuất.

    Vì sao tồn tại: mỗi người dùng cần một danh tính mật mã —
    private key để ký, public key để người khác xác minh, address để nhận dạng ngắn gọn.
    """
    private_key_pem: str
    public_key_hex: str
    address: str


def generate_wallet() -> Wallet:
    """Tạo ví mới: sinh cặp khoá ECDSA trên curve SECP256K1.

    Vì sao tồn tại: SECP256K1 là curve mà Bitcoin dùng,
    cho phép sinh khoá nhanh và chữ ký nhỏ gọn.
    """
    # Sinh khoá riêng ngẫu nhiên
    private_key = ec.generate_private_key(ec.SECP256K1())

    # Xuất khoá riêng dạng PEM (để lưu trữ và ký sau)
    private_key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    # Xuất khoá công dạng uncompressed point → hex
    public_key_hex = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint,
    ).hex()

    # Địa chỉ = 40 ký tự đầu của SHA-256(public_key_hex)
    address = sha256_hex(public_key_hex)[:40]

    return Wallet(
        private_key_pem=private_key_pem,
        public_key_hex=public_key_hex,
        address=address,
    )


def sign_message(message: str, private_key_pem: str) -> str:
    """Ký message bằng ECDSA, trả về chữ ký dạng hex.

    Vì sao tồn tại: chữ ký số chứng minh chủ sở hữu private key
    đã phê duyệt nội dung message, không ai khác giả mạo được.
    """
    private_key = serialization.load_pem_private_key(
        private_key_pem.encode("utf-8"),
        password=None,
    )
    # Thư viện tự hash message bằng SHA-256 rồi ký
    signature_bytes = private_key.sign(
        message.encode("utf-8"),
        ec.ECDSA(hashes.SHA256()),
    )
    return signature_bytes.hex()


def verify_signature(message: str, signature_hex: str, public_key_hex: str) -> bool:
    """Xác minh chữ ký: message có đúng do chủ public key ký không.

    Vì sao tồn tại: bất kỳ ai có public key đều kiểm tra được
    tính toàn vẹn và nguồn gốc của message mà không cần bên thứ ba.
    """
    try:
        public_key = ec.EllipticCurvePublicKey.from_encoded_point(
            ec.SECP256K1(),
            bytes.fromhex(public_key_hex),
        )
        public_key.verify(
            bytes.fromhex(signature_hex),
            message.encode("utf-8"),
            ec.ECDSA(hashes.SHA256()),
        )
        return True
    except (InvalidSignature, ValueError):
        return False
