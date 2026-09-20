"""Tests cho blockchain/block.py và blockchain/blockchain.py.

Kiểm tra: chain hợp lệ, phát hiện sửa dữ liệu đúng chỉ số,
phát hiện merkle_root không khớp giao dịch.
"""

from dataclasses import asdict

from blockchain.wallet import generate_wallet
from blockchain.transaction import Credential, Transaction
from blockchain.block import Block
from blockchain.blockchain import Blockchain
from blockchain.merkle import calculate_merkle_root
from blockchain.mining import mine_block


def _make_tx(wallet, cred_id):
    """Helper: tạo Transaction ISSUE đã ký."""
    cred = Credential(cred_id, "Uni", "Student", "BSc", "2026-01-01", {})
    tx = Transaction("ISSUE", wallet.public_key_hex, asdict(cred))
    tx.sign(wallet)
    return tx


def _build_chain(n_blocks=3):
    """Helper: tạo blockchain với n block, mỗi block 1 transaction, đã mine."""
    wallet = generate_wallet()
    bc = Blockchain()

    for i in range(n_blocks):
        tx = _make_tx(wallet, f"CRED-{i}")
        prev_hash = bc.get_latest_block().compute_hash()
        block = Block(transactions=[tx], height=i + 1, previous_hash=prev_hash, difficulty=2)
        mine_block(block)
        bc.add_block(block)

    return bc, wallet


# ── Test chain hợp lệ ──

def test_valid_chain():
    """Chain xây đúng cách phải hợp lệ."""
    bc, _ = _build_chain(3)
    ok, idx, reason = bc.is_chain_valid()
    assert ok is True
    assert idx is None
    assert "hợp lệ" in reason.lower()


def test_genesis_block():
    """Genesis block phải có previous_hash toàn 0, height 0."""
    bc = Blockchain()
    genesis = bc.chain[0]
    assert genesis.height == 0
    assert genesis.header.previous_hash == "0" * 64
    assert genesis.transaction_count == 0


# ── Test sửa dữ liệu → phát hiện đúng chỉ số ──

def test_tamper_block_detected():
    """Sửa merkle_root block 2 → is_chain_valid trả đúng chỉ số 2.

    Mô phỏng: kẻ tấn công sửa dữ liệu trong block giữa chuỗi.
    Cập nhật merkle_root để phù hợp → hash block 2 đổi →
    block 3 phát hiện previous_hash không khớp.
    """
    bc, _ = _build_chain(4)

    # Sửa merkle_root block 2 (giả lập sửa giao dịch + cập nhật root)
    bc.chain[2].header.merkle_root = "ff" * 32

    ok, idx, reason = bc.is_chain_valid()
    assert ok is False
    assert idx == 2  # phát hiện tại block 2 (merkle_root sai)
    assert "merkle_root" in reason


def test_tamper_previous_hash_detected():
    """Sửa previous_hash block 3 → phát hiện tại block 3."""
    bc, _ = _build_chain(4)

    bc.chain[3].header.previous_hash = "aa" * 32

    ok, idx, reason = bc.is_chain_valid()
    assert ok is False
    assert idx == 3
    assert "previous_hash" in reason


# ── Test merkle_root không khớp Tx ──

def test_merkle_root_mismatch():
    """Thêm tx vào block nhưng không cập nhật merkle_root → phát hiện.

    Mô phỏng: kẻ tấn công chèn thêm giao dịch giả vào block.
    """
    bc, wallet = _build_chain(2)

    # Chèn thêm 1 tx giả vào block 1 mà không cập nhật merkle_root
    fake_tx = _make_tx(wallet, "FAKE-TX")
    bc.chain[1].transactions.append(fake_tx)

    ok, idx, reason = bc.is_chain_valid()
    assert ok is False
    assert idx == 1
    assert "merkle_root" in reason


# ── Test block hash thay đổi khi header thay đổi ──

def test_block_hash_changes_with_header():
    """Thay đổi bất kỳ field nào trong header → hash block thay đổi."""
    bc, _ = _build_chain(1)
    block = bc.chain[1]

    hash_before = block.compute_hash()
    block.header.nonce = 999999
    hash_after = block.compute_hash()

    assert hash_before != hash_after
