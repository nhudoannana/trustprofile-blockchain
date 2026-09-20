"""Trang Mining Flow — chạy trọn luồng end-to-end.

Create TX → Sign → Broadcast → Mempool → Mine → Block →
Validate → Consensus → Chain updated.
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

st.set_page_config(page_title="Mining Flow - TrustProfile", page_icon="🔄", layout="wide")

st.header("9️⃣ Mining Flow — End to End")


# ── Network (cache_resource, chia sẻ giữa các trang) ──

network = get_network()


# ── Đảm bảo có wallet ──

wallets = st.session_state.get("wallets", [])
if not wallets:
    st.info("Cần ít nhất 1 wallet. Bấm tạo nhanh bên dưới.")
    if st.button("⚡ Tạo wallet demo", key="flow_quick_wallet"):
        w = generate_wallet()
        st.session_state.wallets = [
            {"name": "Demo Issuer", "private_key_pem": w.private_key_pem,
             "public_key_hex": w.public_key_hex, "address": w.address}
        ]
        st.rerun()
    st.stop()


# ══════════════════════════════════════════════
# Trạng thái hiện tại
# ══════════════════════════════════════════════
st.subheader("🔹 Trạng thái mạng")

status_rows = []
tip_hashes = set()
for nid, node in network.nodes.items():
    tip = node.blockchain.get_latest_block().compute_hash()
    tip_hashes.add(tip)
    status_rows.append({
        "Node": nid,
        "Status": "🟢" if node.status == "ONLINE" else "🔴",
        "Height": node.height,
        "Mempool": len(node.mempool.get_transactions()),
        "Tip Hash": tip[:16] + "…",
    })

st.table(status_rows)

if len(tip_hashes) == 1:
    st.success(f"🤝 **Consensus** — Cả 3 node cùng tip hash, height {list(network.nodes.values())[0].height}")
else:
    st.warning("⚠️ Các node chưa đồng bộ — tip hash khác nhau")

st.divider()

# ══════════════════════════════════════════════
# BƯỚC 1: Tạo & Gửi Transaction
# ══════════════════════════════════════════════
st.subheader("① Tạo & Gửi Transaction")

col1, col2 = st.columns(2)
with col1:
    wallet_names = [w["name"] for w in wallets]
    sel_wallet = st.selectbox("Issuer:", wallet_names, key="flow_wallet")
    target = st.selectbox("Gửi đến:", list(network.nodes.keys()), key="flow_target")
with col2:
    cred_id = st.text_input("Credential ID:", value=f"CRED-{int(time.time()) % 10000:04d}", key="flow_cred")
    holder = st.text_input("Holder:", value="Alice", key="flow_holder")
    title = st.text_input("Title:", value="BSc Computer Science", key="flow_title")

if st.button("📤 Create → Sign → Submit → Broadcast", key="btn_flow_submit"):
    w_dict = next(w for w in wallets if w["name"] == sel_wallet)
    wallet = Wallet(
        private_key_pem=w_dict["private_key_pem"],
        public_key_hex=w_dict["public_key_hex"],
        address=w_dict["address"],
    )

    cred = Credential(cred_id, sel_wallet, holder, title, "2026-06-01", {})
    tx = Transaction("ISSUE", wallet.public_key_hex, asdict(cred))
    tx.sign(wallet)

    network.log_event("Flow", f"① TX created: {cred_id} → signed")

    node = network.nodes[target]
    ok, reason = node.submit_transaction(tx)

    if ok:
        with st.spinner("Propagation..."):
            time.sleep(0.5)
        st.success(f"✅ TX submitted & broadcast!")
        network.log_event("Flow", f"① TX propagated to all online nodes")

        # Hiện mempool mỗi node
        st.markdown("**Mempool sau broadcast:**")
        for nid, n in network.nodes.items():
            count = len(n.mempool.get_transactions())
            st.caption(f"  {nid}: {count} TX pending")
        st.rerun()
    else:
        st.error(f"❌ {reason}")

st.divider()

# ══════════════════════════════════════════════
# BƯỚC 2: Mine
# ══════════════════════════════════════════════
st.subheader("② Mine — Lấy TX từ Mempool → Tạo Block → PoW → Broadcast")

col_m1, col_m2 = st.columns(2)
with col_m1:
    miner_node = st.selectbox("Miner:", list(network.nodes.keys()), key="flow_miner")
    difficulty = st.slider("Difficulty:", 2, 5, 3, key="flow_diff")
with col_m2:
    miner = network.nodes[miner_node]
    pending = len(miner.mempool.get_transactions())
    st.metric("TX chờ trong Mempool", pending)

if st.button("⛏️ Mine Block", key="btn_flow_mine"):
    if pending == 0:
        st.warning("Mempool trống — gửi TX trước (Bước 1).")
    else:
        network.log_event("Flow", f"② Mining started at {miner_node}")

        with st.spinner(f"⛏️ {miner_node} đang đào..."):
            block, result = miner.mine_pending(difficulty=difficulty)

        if block is not None:
            with st.spinner("Block propagation..."):
                time.sleep(0.5)

            st.success(
                f"✅ **Block mined!** Height {block.height} | "
                f"Nonce {result['nonce']:,} | "
                f"{result['attempts']:,} attempts | "
                f"{result['seconds']:.4f}s"
            )
            st.code(result["block_hash"], language="text")

            network.log_event("Flow", f"② Block propagated → consensus check")

            # Kiểm tra consensus
            st.markdown("**Kết quả sau mining:**")
            all_same = True
            results_rows = []
            for nid, n in network.nodes.items():
                tip = n.blockchain.get_latest_block().compute_hash()
                results_rows.append({
                    "Node": nid,
                    "Height": n.height,
                    "Tip": tip[:20] + "…",
                    "Mempool": len(n.mempool.get_transactions()),
                })

            st.table(results_rows)

            tips = set(r["Tip"] for r in results_rows)
            if len(tips) == 1:
                network.log_event("Flow", "② ✅ Consensus reached — all nodes agree")
                st.success("🤝 **CONSENSUS REACHED** — Cả 3 node cùng height và cùng tip hash!")
            else:
                st.warning("⚠️ Nodes chưa đồng bộ hoàn toàn.")

            st.rerun()
        else:
            st.warning(f"Không mine được: {result}")

st.divider()

# ══════════════════════════════════════════════
# BƯỚC 3: Xem chi tiết blockchain
# ══════════════════════════════════════════════
st.subheader("③ Blockchain chi tiết")

for nid, node in network.nodes.items():
    with st.expander(f"📦 {nid} — Height {node.height}"):
        for block in node.blockchain.chain:
            bh = block.compute_hash()
            st.markdown(
                f"**Block {block.height}** | "
                f"`{bh[:16]}…` | "
                f"nonce={block.header.nonce:,} | "
                f"{block.transaction_count} TXs"
            )
            for tx in block.transactions:
                cred = tx.payload.get("credential_id", "—")
                holder_name = tx.payload.get("holder_name", "—")
                st.caption(f"    📄 {tx.tx_type} {cred} → {holder_name}")

st.divider()

# ══════════════════════════════════════════════
# Event Log
# ══════════════════════════════════════════════
st.subheader("📋 Event Log")

col_l1, col_l2 = st.columns([1, 4])
with col_l1:
    if st.button("🗑️ Xoá log", key="flow_clear_log"):
        network.clear_event_log()
        st.rerun()
with col_l2:
    if st.button("🔄 Refresh", key="flow_refresh"):
        st.rerun()

log = network.get_event_log(last_n=40)
if log:
    for line in reversed(log):
        st.text(line)
else:
    st.caption("(chưa có sự kiện)")
