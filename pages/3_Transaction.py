"""Trang Credential & Transaction — tạo chứng nhận, ký thành giao dịch.

Mục đích: cho sinh viên trải nghiệm luồng Issuer tạo credential,
đóng gói thành transaction có chữ ký, và xác minh tính hợp lệ.
"""

import json
import streamlit as st
import sys
import os
from dataclasses import asdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from state import init_state
from blockchain.wallet import Wallet
from blockchain.transaction import Credential, Transaction, verify_transaction

init_state()

st.set_page_config(page_title="Transaction - TrustProfile", page_icon="🔗")

st.header("3️⃣ Credential & Transaction")

# ══════════════════════════════════════════════
# PHẦN 1: Tạo Credential & Transaction
# ══════════════════════════════════════════════
st.subheader("🔹 Phát hành Credential")

if not st.session_state.wallets:
    st.warning("⚠️ Chưa có wallet. Vào trang **Wallet** tạo ít nhất 1 ví trước.")
else:
    # Chọn Issuer wallet
    wallet_names = [w["name"] for w in st.session_state.wallets]
    issuer_idx = st.selectbox(
        "Chọn Issuer (wallet ký):",
        range(len(wallet_names)),
        format_func=lambda i: wallet_names[i],
        key="issuer_select",
    )

    st.markdown("---")
    st.markdown("**Thông tin Credential:**")

    col1, col2 = st.columns(2)
    with col1:
        cred_id = st.text_input("Credential ID:", value="CRED-001", key="cred_id")
        holder_name = st.text_input("Holder (người nhận):", value="Alice Nguyen", key="holder")
        issue_date = st.date_input("Ngày cấp:", key="issue_date")
    with col2:
        title = st.text_input("Tiêu đề chứng nhận:", value="BSc Computer Science", key="title")
        claim_key = st.text_input("Claim key:", value="gpa", key="claim_key")
        claim_val = st.text_input("Claim value:", value="3.8", key="claim_val")

    if st.button("📜 Tạo Transaction & Ký", key="btn_create_tx"):
        issuer_wal = st.session_state.wallets[issuer_idx]

        # Tạo Credential
        cred = Credential(
            credential_id=cred_id,
            issuer_name=issuer_wal["name"],
            holder_name=holder_name,
            title=title,
            issue_date=str(issue_date),
            claims={claim_key: claim_val} if claim_key else {},
        )

        # Tạo Transaction
        tx = Transaction(
            tx_type="ISSUE",
            sender_public_key=issuer_wal["public_key_hex"],
            payload=asdict(cred),
        )

        # Ký bằng wallet Issuer
        wallet_obj = Wallet(
            private_key_pem=issuer_wal["private_key_pem"],
            public_key_hex=issuer_wal["public_key_hex"],
            address=issuer_wal["address"],
        )
        tx.sign(wallet_obj)

        # Lưu vào session_state để dùng lại
        if "transactions" not in st.session_state:
            st.session_state.transactions = []
        st.session_state.transactions.append(tx.to_dict())

        # Ghi log
        st.session_state.event_log.append(
            f"ISSUE credential '{cred_id}' cho {holder_name} bởi {issuer_wal['name']}"
        )

        # Hiển thị kết quả
        st.success(f"✅ Transaction đã tạo và ký thành công!")

        st.markdown("**Transaction ID (tx_id):**")
        st.code(tx.tx_id, language="text")

        st.markdown("**Chữ ký (hex):**")
        st.code(tx.signature[:80] + "…", language="text")

        # Verify ngay
        ok, reason = verify_transaction(tx)
        if ok:
            st.success(f"🔍 Verify: ✅ {reason}")
        else:
            st.error(f"🔍 Verify: ❌ {reason}")

        # JSON đầy đủ
        with st.expander("📋 Xem JSON transaction đầy đủ"):
            st.json(tx.to_dict())

    st.divider()

    # ══════════════════════════════════════════════
    # PHẦN 2: Danh sách Transaction đã tạo
    # ══════════════════════════════════════════════
    if st.session_state.get("transactions"):
        st.subheader("🔹 Danh sách Transaction đã tạo")
        for i, tx_dict in enumerate(st.session_state.transactions):
            cred_info = tx_dict["payload"]
            label = (
                f"{tx_dict['tx_type']} — "
                f"{cred_info.get('credential_id', 'N/A')} — "
                f"{cred_info.get('holder_name', 'N/A')}"
            )
            with st.expander(f"📄 {label}"):
                st.markdown(f"**tx_id:** `{tx_dict['tx_id']}`")
                st.markdown(f"**tx_type:** `{tx_dict['tx_type']}`")
                st.markdown(f"**Timestamp:** `{tx_dict['timestamp']}`")
                st.json(tx_dict["payload"])

    st.divider()

    # ══════════════════════════════════════════════
    # PHẦN 3: Demo thu hồi (REVOKE)
    # ══════════════════════════════════════════════
    st.subheader("🔹 Thu hồi Credential (REVOKE)")
    st.caption("Tạo transaction REVOKE cho một credential đã phát hành.")

    revoke_cred_id = st.text_input("Credential ID cần thu hồi:", key="revoke_cred_id")
    revoke_reason = st.text_input("Lý do thu hồi:", value="Phát hiện sai sót", key="revoke_reason")

    if st.button("🚫 Tạo REVOKE Transaction", key="btn_revoke"):
        if not revoke_cred_id:
            st.error("❌ Nhập Credential ID cần thu hồi.")
        else:
            issuer_wal = st.session_state.wallets[issuer_idx]
            tx = Transaction(
                tx_type="REVOKE",
                sender_public_key=issuer_wal["public_key_hex"],
                payload={"credential_id": revoke_cred_id, "reason": revoke_reason},
            )
            wallet_obj = Wallet(
                private_key_pem=issuer_wal["private_key_pem"],
                public_key_hex=issuer_wal["public_key_hex"],
                address=issuer_wal["address"],
            )
            tx.sign(wallet_obj)

            if "transactions" not in st.session_state:
                st.session_state.transactions = []
            st.session_state.transactions.append(tx.to_dict())

            st.session_state.event_log.append(
                f"REVOKE credential '{revoke_cred_id}': {revoke_reason}"
            )

            ok, reason = verify_transaction(tx)
            st.success(f"✅ REVOKE transaction đã tạo — tx_id: `{tx.tx_id[:32]}…`")
            if ok:
                st.success(f"🔍 Verify: ✅ {reason}")
            else:
                st.error(f"🔍 Verify: ❌ {reason}")

st.divider()

# ══════════════════════════════════════════════
# PHẦN 4: Câu hỏi thảo luận
# ══════════════════════════════════════════════
with st.expander("💬 Câu hỏi thảo luận"):
    st.markdown(
        """
        **1. Vì sao compute_hash() không gồm signature?**

        Vì signature được tạo *từ* hash — nếu gồm signature trong hash thì tạo
        vòng lặp: hash phụ thuộc signature, signature phụ thuộc hash.

        ---

        **2. Nonce dùng để làm gì?**

        Đảm bảo hai transaction cùng nội dung (ví dụ cấp lại credential)
        vẫn có tx_id khác nhau, tránh bị coi là trùng lặp.

        ---

        **3. Kẻ tấn công sửa payload rồi tính lại hash thì sao?**

        Hash mới sẽ khác hash cũ → chữ ký không còn khớp.
        Muốn ký lại cần private key của Issuer — kẻ tấn công không có.
        Đây là lý do blockchain kết hợp **hash + chữ ký** chứ không chỉ dùng một trong hai.
        """
    )
