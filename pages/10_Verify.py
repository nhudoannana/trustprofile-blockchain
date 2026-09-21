"""Trang Verify — xác minh và thu hồi credential.

Mục đích: Verifier nhập Credential ID, hệ thống kiểm tra 12 bước
từ TX đến Block đến Chain, hiển thị từng bước PASS/FAIL.
Issuer có thể thu hồi credential bằng REVOKE transaction.
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

init_state()



st.header("🔟 Verify Credential")

network = get_network()

# Dùng blockchain của Node-1 (tất cả node có cùng chain sau consensus)
node = network.nodes["Node-1"]
bc = node.blockchain

# ══════════════════════════════════════════════
# PHẦN 1: Xác minh Credential
# ══════════════════════════════════════════════
st.subheader("🔹 Xác minh Credential")

cred_id = st.text_input("Nhập Credential ID:", value="", key="verify_cred_id",
                         placeholder="Ví dụ: CRED-0001")

if st.button("🔍 Verify", key="btn_verify") and cred_id.strip():
    cred_id = cred_id.strip()
    steps, final_status, info = bc.verify_credential(cred_id)

    # Hiển thị từng bước
    st.markdown("#### Kết quả kiểm tra 12 bước:")
    for i, (name, passed, detail) in enumerate(steps, 1):
        icon = "✅" if passed else "❌"
        st.markdown(f"**{i}. {icon} {name}** — {detail}")

    # Kết quả cuối
    st.markdown("---")
    if final_status == "VERIFIED":
        st.success("### ✅ VERIFIED — Credential hợp lệ và đang ACTIVE")
    elif final_status == "REVOKED":
        st.warning("### 🔴 REVOKED — Credential đã bị thu hồi")
    elif final_status == "NOT_FOUND":
        st.error(f"### ❌ NOT FOUND — Credential '{cred_id}' không tồn tại trong blockchain")
    else:
        fail_step = next((name for name, ok, _ in steps if not ok), "Unknown")
        st.error(f"### ❌ INVALID — Thất bại tại bước: {fail_step}")

    # Thông tin credential (nếu tìm thấy)
    if info:
        st.markdown("---")
        st.markdown("#### 📋 Thông tin Credential")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Credential ID:** `{info.get('credential_id', '—')}`")
            st.markdown(f"**Issuer:** {info.get('issuer_name', '—')}")
            st.markdown(f"**Holder:** {info.get('holder_name', '—')}")
            st.markdown(f"**Title:** {info.get('title', '—')}")
            st.markdown(f"**Issue Date:** {info.get('issue_date', '—')}")
        with col2:
            st.markdown(f"**Issue TX:** `{info.get('issue_tx_id', '—')[:24]}…`")
            st.markdown(f"**Block Height:** {info.get('issue_block_height', '—')}")
            st.markdown(f"**Block Hash:** `{info.get('issue_block_hash', '—')[:24]}…`")
            st.markdown(f"**Merkle Root:** `{info.get('issue_merkle_root', '—')[:24]}…`")

        # Lịch sử
        st.markdown("#### 📜 Lịch sử")
        st.markdown(f"📗 **Cấp:** Block {info.get('issue_block_height', '—')}")
        if "revoke_block_height" in info:
            st.markdown(
                f"📕 **Thu hồi:** Block {info['revoke_block_height']} "
                f"— Lý do: {info.get('revoke_reason', '—')}"
            )

st.divider()

# ══════════════════════════════════════════════
# PHẦN 2: Thu hồi Credential (REVOKE)
# ══════════════════════════════════════════════
st.subheader("🔹 Thu hồi Credential (REVOKE)")
st.caption("Issuer gửi REVOKE TX → Mempool → Mine → Credential chuyển sang REVOKED.")

wallets = st.session_state.get("wallets", [])
if not wallets:
    st.info("Chưa có wallet. Vào trang **Wallet** hoặc **Network** để tạo.")
else:
    col_r1, col_r2 = st.columns(2)
    with col_r1:
        wallet_names = [w["name"] for w in wallets]
        rev_wallet = st.selectbox("Issuer (wallet):", wallet_names, key="rev_wallet")
        rev_cred_id = st.text_input("Credential ID cần thu hồi:", key="rev_cred_id",
                                     placeholder="CRED-xxxx")
    with col_r2:
        rev_reason = st.text_input("Lý do thu hồi:", value="Expired", key="rev_reason")
        rev_node = st.selectbox("Gửi đến node:", list(network.nodes.keys()), key="rev_node")

    if st.button("🔴 Gửi REVOKE Transaction", key="btn_revoke"):
        if not rev_cred_id.strip():
            st.warning("Nhập Credential ID.")
        else:
            w_dict = next(w for w in wallets if w["name"] == rev_wallet)
            wallet = Wallet(
                private_key_pem=w_dict["private_key_pem"],
                public_key_hex=w_dict["public_key_hex"],
                address=w_dict["address"],
            )

            payload = {
                "credential_id": rev_cred_id.strip(),
                "reason": rev_reason,
            }
            tx = Transaction("REVOKE", wallet.public_key_hex, payload)
            tx.sign(wallet)

            target = network.nodes[rev_node]
            ok, reason = target.submit_transaction(tx)

            if ok:
                with st.spinner("Propagation..."):
                    time.sleep(0.5)
                st.success(f"✅ REVOKE TX submitted & broadcast!")
                st.info("Bấm **Mine** bên dưới để đưa TX vào block.")
            else:
                st.error(f"❌ {reason}")

    # Nút mine nhanh
    st.markdown("---")
    mine_node = st.selectbox("Mine tại:", list(network.nodes.keys()), key="rev_mine_node")
    if st.button("⛏️ Mine (xử lý REVOKE)", key="btn_rev_mine"):
        miner = network.nodes[mine_node]
        pending = len(miner.mempool.get_transactions())
        if pending == 0:
            st.warning("Mempool trống. Gửi REVOKE TX trước.")
        else:
            with st.spinner("Mining..."):
                block, result = miner.mine_pending(difficulty=2)
            if block:
                with st.spinner("Block propagation..."):
                    time.sleep(0.5)
                st.success(
                    f"✅ Block mined! Height {block.height}, "
                    f"{result['attempts']:,} attempts"
                )
                st.info("Quay lại phần Verify ở trên để kiểm tra trạng thái REVOKED.")
                st.rerun()

st.divider()

# ══════════════════════════════════════════════
# PHẦN 3: Danh sách credential trong chain
# ══════════════════════════════════════════════
with st.expander("📋 Danh sách credential trong blockchain"):
    found = False
    for block in bc.chain:
        for tx in block.transactions:
            cid = tx.payload.get("credential_id")
            if cid:
                status = bc.credential_status(cid)
                icon = "🟢" if status == "ACTIVE" else "🔴"
                found = True
                st.caption(
                    f"{icon} `{cid}` | {tx.tx_type} | "
                    f"{tx.payload.get('holder_name', '—')} | "
                    f"Block {block.height} | Status: {status}"
                )
    if not found:
        st.caption("Chưa có credential nào. Vào trang **Mining Flow** để tạo.")
