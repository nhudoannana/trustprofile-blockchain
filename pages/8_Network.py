"""Trang Network — quản lý 3 Full Node, broadcast TX, sync chain.

Mục đích: cho sinh viên thấy tính phi tập trung — mỗi node giữ
bản sao riêng, tự xác minh, giao dịch lan truyền qua toàn mạng.
"""

import time
import streamlit as st
import sys
import os
from dataclasses import asdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from state import init_state, get_network
from blockchain.wallet import Wallet, generate_wallet
from blockchain.transaction import Credential, Transaction
from blockchain.node import Network

init_state()



st.header("8️⃣ Network & Full Nodes")


# ── Khởi tạo Network (cache_resource, chia sẻ giữa các trang) ──

network = get_network()

# ══════════════════════════════════════════════
# PHẦN 1: Bảng trạng thái Node
# ══════════════════════════════════════════════
st.subheader("🔹 Trạng thái Node")

rows = []
for nid, node in network.nodes.items():
    rows.append({
        "Node": nid,
        "Địa chỉ": f"{node.host}:{node.port}",
        "Status": "🟢 ONLINE" if node.status == "ONLINE" else "🔴 OFFLINE",
        "Height": node.height,
        "Mempool TXs": len(node.mempool.get_transactions()),
        "Thread": "alive" if node._worker.is_alive() else "dead",
    })

st.table(rows)

# ══════════════════════════════════════════════
# PHẦN 2: Bật / Tắt Node
# ══════════════════════════════════════════════
st.subheader("🔹 Bật / Tắt Node")

cols = st.columns(3)
for idx, (nid, node) in enumerate(network.nodes.items()):
    with cols[idx]:
        if node.status == "ONLINE":
            if st.button(f"🔴 Tắt {nid}", key=f"btn_off_{nid}"):
                node.go_offline()
                st.rerun()
        else:
            if st.button(f"🟢 Bật {nid}", key=f"btn_on_{nid}"):
                node.go_online()
                st.rerun()

st.divider()

# ══════════════════════════════════════════════
# PHẦN 3: Gửi Transaction
# ══════════════════════════════════════════════
st.subheader("🔹 Gửi Transaction vào mạng")

wallets = st.session_state.get("wallets", [])
if not wallets:
    st.info("Chưa có wallet. Tạo nhanh bên dưới hoặc vào trang **Wallet** để tạo.")
    if st.button("⚡ Tạo wallet demo nhanh", key="btn_quick_wallet"):
        w = generate_wallet()
        st.session_state.wallets = [
            {"name": "Demo Issuer", "private_key_pem": w.private_key_pem,
             "public_key_hex": w.public_key_hex, "address": w.address}
        ]
        st.rerun()
else:
    col_form1, col_form2 = st.columns(2)
    with col_form1:
        wallet_names = [w["name"] for w in wallets]
        selected_wallet = st.selectbox("Issuer (wallet):", wallet_names, key="net_wallet")
        target_node = st.selectbox("Gửi đến node:", list(network.nodes.keys()), key="net_target")

    with col_form2:
        cred_id = st.text_input("Credential ID:", value="CRED-NET-001", key="net_cred_id")
        holder = st.text_input("Holder:", value="Alice", key="net_holder")
        title = st.text_input("Title:", value="BSc Computer Science", key="net_title")

    if st.button("📤 Tạo & Gửi Transaction", key="btn_send_tx"):
        w_dict = next(w for w in wallets if w["name"] == selected_wallet)
        wallet = Wallet(
            private_key_pem=w_dict["private_key_pem"],
            public_key_hex=w_dict["public_key_hex"],
            address=w_dict["address"],
        )

        cred = Credential(cred_id, selected_wallet, holder, title, "2026-06-01", {})
        tx = Transaction("ISSUE", wallet.public_key_hex, asdict(cred))
        tx.sign(wallet)

        node = network.nodes[target_node]
        ok, reason = node.submit_transaction(tx)

        if ok:
            with st.spinner("Đợi propagation..."):
                time.sleep(0.5)  # chờ worker thread xử lý
            st.success(f"✅ {reason}")
            st.rerun()
        else:
            st.error(f"❌ {reason}")

st.divider()

# ══════════════════════════════════════════════
# PHẦN 4: Demo tấn công — TX giả mạo
# ══════════════════════════════════════════════
st.subheader("🔹 Demo: TX giả mạo bị cả mạng từ chối")

if wallets:
    if st.button("🔴 Gửi TX giả mạo (sửa payload sau khi ký)", key="btn_fake_tx"):
        w_dict = wallets[0]
        wallet = Wallet(
            private_key_pem=w_dict["private_key_pem"],
            public_key_hex=w_dict["public_key_hex"],
            address=w_dict["address"],
        )

        cred = Credential("CRED-FAKE", w_dict["name"], "Hacker", "Fake PhD", "2026-01-01", {})
        tx = Transaction("ISSUE", wallet.public_key_hex, asdict(cred))
        tx.sign(wallet)

        # Giả mạo payload sau khi ký
        tx.payload["title"] = "Fake PhD in Everything"

        node1 = network.nodes["Node-1"]
        ok, reason = node1.submit_transaction(tx)
        st.error(f"❌ Node-1 từ chối: {reason}")
        st.info("TX không được broadcast → không node nào nhận.")

st.divider()

# ══════════════════════════════════════════════
# PHẦN 5: Sync Chain
# ══════════════════════════════════════════════
st.subheader("🔹 Đồng bộ Chain (Sync)")
st.caption(
    "Node OFFLINE bỏ lỡ block mới. Khi online lại, Sync lấy chain dài nhất "
    "hợp lệ từ peer. (Hữu ích khi có mining/consensus tạo block mới.)"
)

sync_node = st.selectbox("Chọn node cần sync:", list(network.nodes.keys()), key="sync_node")
if st.button("🔄 Sync ngay", key="btn_sync"):
    node = network.nodes[sync_node]
    if node.status != "ONLINE":
        st.warning(f"{sync_node} đang OFFLINE — bật lên trước.")
    else:
        node.request_sync()
        with st.spinner("Đợi sync response..."):
            time.sleep(0.5)
        st.success(f"✅ {sync_node} height = {node.height}")
        st.rerun()

st.divider()

# ══════════════════════════════════════════════
# PHẦN 6: Chi tiết từng Node
# ══════════════════════════════════════════════
st.subheader("🔹 Chi tiết Node")

for nid, node in network.nodes.items():
    with st.expander(f"📦 {nid} — Height {node.height} — "
                     f"{len(node.mempool.get_transactions())} TX pending"):
        # Blockchain
        st.markdown("**Blockchain:**")
        for block in node.blockchain.chain:
            st.caption(
                f"  Block {block.height} | "
                f"hash: `{block.compute_hash()[:20]}…` | "
                f"prev: `{block.header.previous_hash[:20]}…` | "
                f"txs: {block.transaction_count}"
            )

        # Mempool
        st.markdown("**Mempool:**")
        txs = node.mempool.get_transactions()
        if txs:
            for tx in txs:
                cred_id = tx.payload.get("credential_id", "—")
                st.caption(f"  📄 {tx.tx_type} | {cred_id} | `{tx.tx_id[:20]}…`")
        else:
            st.caption("  (trống)")

st.divider()

# ══════════════════════════════════════════════
# PHẦN 7: Event Log
# ══════════════════════════════════════════════
st.subheader("🔹 Event Log (thread-safe)")

col_log1, col_log2 = st.columns([1, 4])
with col_log1:
    if st.button("🗑️ Xoá log", key="btn_clear_log"):
        network.clear_event_log()
        st.rerun()

with col_log2:
    if st.button("🔄 Refresh", key="btn_refresh_log"):
        st.rerun()

log = network.get_event_log(last_n=30)
if log:
    for line in reversed(log):  # mới nhất ở trên
        st.text(line)
else:
    st.caption("(chưa có sự kiện)")
