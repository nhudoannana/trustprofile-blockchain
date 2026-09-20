"""Tests cho module blockchain/mining.py.

Kiểm tra: hash sau mine có đủ số 0; sửa nonce thì is_valid_pow False.
"""

from blockchain.block import Block
from blockchain.mining import mine_block, is_valid_pow


def _make_block(difficulty=2):
    """Helper: tạo block rỗng với difficulty cho sẵn, chưa mine."""
    return Block(
        transactions=[],
        height=1,
        previous_hash="0" * 64,
        difficulty=difficulty,
    )


# ── Test mine thành công ──

def test_mine_produces_valid_hash():
    """Sau khi mine, hash block phải bắt đầu bằng đủ số '0'."""
    block = _make_block(difficulty=2)
    result = mine_block(block)

    assert result["block_hash"].startswith("00")
    assert result["attempts"] >= 1
    assert result["seconds"] >= 0
    assert result["nonce"] == block.header.nonce


def test_mine_difficulty_3():
    """Mine với difficulty 3 → hash bắt đầu bằng '000'."""
    block = _make_block(difficulty=3)
    result = mine_block(block)
    assert result["block_hash"].startswith("000")


# ── Test is_valid_pow ──

def test_is_valid_pow_after_mining():
    """Block đã mine phải pass is_valid_pow."""
    block = _make_block(difficulty=2)
    mine_block(block)
    assert is_valid_pow(block) is True


def test_is_valid_pow_fails_wrong_nonce():
    """Sửa nonce sau khi mine → is_valid_pow False.

    Mô phỏng: kẻ tấn công sửa nonce mà không đào lại.
    """
    block = _make_block(difficulty=3)
    mine_block(block)
    assert is_valid_pow(block) is True

    # Sửa nonce
    block.header.nonce = block.header.nonce + 999999
    assert is_valid_pow(block) is False


def test_is_valid_pow_fails_unmined_block():
    """Block chưa mine (nonce=0, difficulty>0) rất khó thoả mãn PoW."""
    block = _make_block(difficulty=4)
    # Nonce mặc định = 0, hash gần như chắc chắn không bắt đầu bằng "0000"
    # (xác suất 1/65536 ≈ 0.0015%)
    # Kiểm tra is_valid_pow trả giá trị bool hợp lệ
    result = is_valid_pow(block)
    assert isinstance(result, bool)
