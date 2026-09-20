"""Tests cho module blockchain/hash.py.

Kiểm tra tính đúng đắn của hàm băm, avalanche effect,
và khả năng brute-force tìm ngược chuỗi ngắn.
"""

from blockchain.hash import sha256_hex, bit_difference_percent, bruteforce


# ── Test sha256_hex ──

def test_sha256_hex_known_value():
    """Hash của chuỗi rỗng phải khớp giá trị chuẩn đã biết."""
    # SHA-256("") là hằng số nổi tiếng
    expected = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert sha256_hex("") == expected


def test_sha256_hex_deterministic():
    """Cùng input luôn cho cùng output — tính tất định."""
    assert sha256_hex("hello") == sha256_hex("hello")


def test_sha256_hex_different_inputs():
    """Hai input khác nhau phải cho hash khác nhau (kháng va chạm)."""
    assert sha256_hex("hello") != sha256_hex("Hello")


def test_sha256_hex_length():
    """Output luôn 64 ký tự hex = 256 bit."""
    assert len(sha256_hex("bất kỳ chuỗi nào")) == 64


# ── Test bit_difference_percent ──

def test_bit_difference_identical():
    """Hai hash giống nhau → 0% bit khác."""
    h = sha256_hex("same")
    assert bit_difference_percent(h, h) == 0.0


def test_bit_difference_avalanche():
    """Thay đổi 1 ký tự → khoảng 50% bit khác (Avalanche Effect).

    Cho phép sai số ±15% vì giá trị chính xác phụ thuộc input cụ thể.
    """
    h1 = sha256_hex("hello")
    h2 = sha256_hex("hallo")  # chỉ đổi 'e' → 'a'
    diff = bit_difference_percent(h1, h2)
    assert 35.0 <= diff <= 65.0, f"Expected ~50%, got {diff:.1f}%"


# ── Test bruteforce ──

def test_bruteforce_found():
    """Brute-force phải tìm được chuỗi ngắn trong bảng ký tự nhỏ."""
    target = sha256_hex("ab")
    result = bruteforce(target, charset="abc", max_len=3)
    assert result["found"] == "ab"
    assert result["attempts"] > 0
    assert result["seconds"] >= 0


def test_bruteforce_not_found():
    """Nếu chuỗi gốc dài hơn max_len, brute-force không tìm được."""
    target = sha256_hex("abcdef")
    result = bruteforce(target, charset="abcdef", max_len=2)
    assert result["found"] is None
    assert result["attempts"] > 0


def test_bruteforce_tampered_hash():
    """Hash bị sửa 1 ký tự → brute-force không tìm được kết quả.

    Mô phỏng tấn công: kẻ tấn công sửa hash, hệ thống không khớp.
    """
    real_hash = sha256_hex("a")
    # Sửa ký tự đầu tiên của hash
    tampered = ("0" if real_hash[0] != "0" else "1") + real_hash[1:]
    result = bruteforce(tampered, charset="abcdefghijklmnopqrstuvwxyz", max_len=1)
    assert result["found"] is None
