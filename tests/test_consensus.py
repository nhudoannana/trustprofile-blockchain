"""Tests consensus end-to-end: TX → Mempool → Mine → Block accepted.

Kiểm tra: cả 3 node cùng height và tip, TX đã vào block không còn
trong Mempool, block sai PoW bị reject.
"""

import time
from dataclasses import asdict

from blockchain.wallet import generate_wallet
from blockchain.transaction import Credential, Transaction
from blockchain.block import Block
from blockchain.mining import mine_block, is_valid_pow
from blockchain.node import Network, Message


def _wait(network, timeout=2.0):
    """Chờ tất cả inbox trống."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if all(n.inbox.empty() for n in network.nodes.values()):
            time.sleep(0.15)
            return True
        time.sleep(0.05)
    return False


def _make_network():
    net = Network()
    net.create_node("Node-1", "127.0.0.1", 5001)
    net.create_node("Node-2", "127.0.0.1", 5002)
    net.create_node("Node-3", "127.0.0.1", 5003)
    return net


def _make_tx(wallet, cred_id):
    cred = Credential(cred_id, "Uni", "Student", "BSc", "2026-01-01", {})
    tx = Transaction("ISSUE", wallet.public_key_hex, asdict(cred))
    tx.sign(wallet)
    return tx


# ── Test 1: trọn luồng, 3 node cùng height và tip ──

def test_full_flow_consensus():
    """TX → Mempool → Mine → Block accepted → 3 node cùng height, cùng tip hash."""
    net = _make_network()
    wallet = generate_wallet()
    tx = _make_tx(wallet, "CRED-E2E-001")

    # 1. Submit TX vào Node-1
    ok, _ = net.nodes["Node-1"].submit_transaction(tx)
    assert ok is True
    _wait(net)

    # 2. Mine tại Node-1
    block, result = net.nodes["Node-1"].mine_pending(difficulty=2)
    assert block is not None
    _wait(net)

    # 3. Kiểm tra cả 3 node cùng height và cùng tip
    heights = {nid: n.height for nid, n in net.nodes.items()}
    tips = {nid: n.blockchain.get_latest_block().compute_hash()
            for nid, n in net.nodes.items()}

    assert len(set(heights.values())) == 1, f"Heights differ: {heights}"
    assert len(set(tips.values())) == 1, f"Tips differ: {tips}"
    assert list(heights.values())[0] == 1  # genesis + 1 block

    for n in net.nodes.values():
        n._running = False


# ── Test 2: TX đã vào block không còn trong Mempool ──

def test_tx_removed_from_mempool_after_mining():
    """Sau khi mine, TX đã đóng gói phải bị xoá khỏi Mempool của mọi node."""
    net = _make_network()
    wallet = generate_wallet()

    # Submit 2 TX
    tx1 = _make_tx(wallet, "CRED-RM-001")
    tx2 = _make_tx(wallet, "CRED-RM-002")
    net.nodes["Node-1"].submit_transaction(tx1)
    net.nodes["Node-1"].submit_transaction(tx2)
    _wait(net)

    # Mine cả 2 tại Node-1
    net.nodes["Node-1"].mine_pending(difficulty=2)
    _wait(net)

    # Mempool của cả 3 node phải trống
    for nid, node in net.nodes.items():
        txs = node.mempool.get_transactions()
        assert len(txs) == 0, f"{nid} mempool still has {len(txs)} TXs"

    for n in net.nodes.values():
        n._running = False


# ── Test 3: block sai PoW bị cả 3 node reject ──

def test_invalid_pow_block_rejected_by_all():
    """Block chưa mine (PoW sai) bị cả 3 node từ chối.

    Mô phỏng: miner gian lận gửi block không thoả difficulty.
    """
    net = _make_network()

    genesis_hash = net.nodes["Node-1"].blockchain.get_latest_block().compute_hash()

    # Tạo block KHÔNG mine (nonce=0, difficulty=4 → hash gần như chắc chắn sai)
    fake_block = Block(
        transactions=[], height=1,
        previous_hash=genesis_hash, difficulty=4,
    )
    assert not is_valid_pow(fake_block), "Edge case: nonce=0 passed PoW"

    # Gửi trực tiếp vào inbox mỗi node
    for nid, node in net.nodes.items():
        msg = Message("BLOCK", "fake-miner", fake_block)
        node.inbox.put(msg)

    _wait(net)

    # Cả 3 node vẫn height 0 — block bị reject
    for nid, node in net.nodes.items():
        assert node.height == 0, f"{nid} accepted fake block!"

    # Log phải chứa "REJECTED" + "PoW"
    log_text = "\n".join(net.get_event_log())
    assert "REJECTED" in log_text
    assert "PoW" in log_text

    for n in net.nodes.values():
        n._running = False
