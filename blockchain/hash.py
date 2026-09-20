"""Module hash — cung cấp hàm băm SHA-256, so sánh bit, và brute-force demo.

Mục đích: minh hoạ tính chất một chiều và kháng va chạm của hàm băm mật mã,
giúp sinh viên hiểu vì sao blockchain dùng SHA-256.
"""

import hashlib
import itertools
import time


def sha256_hex(data: str) -> str:
    """Băm chuỗi bằng SHA-256, trả về chuỗi hex 64 ký tự.

    Vì sao tồn tại: SHA-256 là hàm băm chuẩn của blockchain,
    dùng để tạo fingerprint bất biến cho mọi dữ liệu.
    """
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def bit_difference_percent(hash_a: str, hash_b: str) -> float:
    """So sánh hai hash hex, trả về phần trăm số bit khác nhau.

    Vì sao tồn tại: minh hoạ Avalanche Effect — thay đổi 1 bit input
    khiến ~50% bit output thay đổi, chứng tỏ hash không thể đoán trước.
    """
    # Chuyển hex → số nguyên, XOR để tìm bit khác nhau
    int_a = int(hash_a, 16)
    int_b = int(hash_b, 16)
    xor = int_a ^ int_b

    # Đếm số bit 1 trong kết quả XOR = số bit khác nhau
    diff_bits = bin(xor).count("1")

    # SHA-256 luôn có 256 bit
    total_bits = 256
    return (diff_bits / total_bits) * 100.0


def bruteforce(target_hash: str, charset: str, max_len: int) -> dict:
    """Thử tất cả tổ hợp ký tự để tìm chuỗi có hash trùng target.

    Vì sao tồn tại: minh hoạ tính một chiều — tìm ngược input từ hash
    chỉ bằng cách vét cạn, chi phí tăng theo cấp số nhân với độ dài.

    Returns:
        dict với keys: attempts (int), seconds (float),
        found (str | None — chuỗi tìm được, None nếu không tìm thấy).
    """
    start = time.time()
    attempts = 0

    # Thử từng độ dài từ 1 đến max_len
    for length in range(1, max_len + 1):
        for combo in itertools.product(charset, repeat=length):
            candidate = "".join(combo)
            attempts += 1
            if sha256_hex(candidate) == target_hash:
                elapsed = time.time() - start
                return {
                    "attempts": attempts,
                    "seconds": round(elapsed, 4),
                    "found": candidate,
                }

    elapsed = time.time() - start
    return {
        "attempts": attempts,
        "seconds": round(elapsed, 4),
        "found": None,
    }
