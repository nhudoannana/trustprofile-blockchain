"""TrustProfile — trang chủ ứng dụng Streamlit.

Mục đích: giới thiệu project, hiển thị danh sách module,
và cung cấp sidebar điều hướng đến các trang chức năng.
"""

import streamlit as st
from state import init_state

# ── Khởi tạo trạng thái ──
init_state()

# ── Cấu hình trang ──
st.set_page_config(
    page_title="TrustProfile",
    page_icon="🔗",
    layout="wide",
)

# ── Sidebar ──
st.sidebar.title("📌 Điều hướng")

PAGES = [
    ("1️⃣", "Hash Demo",        "Chưa làm"),
    ("2️⃣", "Wallet",           "Chưa làm"),
    ("3️⃣", "Transaction",      "Chưa làm"),
    ("4️⃣", "Merkle Tree",      "Chưa làm"),
    ("5️⃣", "Block & Mining",   "Chưa làm"),
    ("6️⃣", "Blockchain",       "Chưa làm"),
    ("7️⃣", "Mempool",          "Chưa làm"),
    ("8️⃣", "Network & Nodes",  "Chưa làm"),
    ("9️⃣", "Verifier",         "Chưa làm"),
]

for icon, name, status in PAGES:
    st.sidebar.markdown(f"{icon} **{name}** — _{status}_")

st.sidebar.divider()
st.sidebar.caption("Đồ án môn Blockchain — Nhóm 7 người")

# ── Nội dung trang chủ ──
st.title("🔗 TrustProfile")
st.subheader("Hệ thống xác thực chứng nhận số bằng Blockchain")

st.markdown(
    """
    **TrustProfile** mô phỏng quy trình phát hành và xác minh chứng nhận số
    (digital credential) trên một blockchain đơn giản.
    Dự án phục vụ mục đích học tập, **không** sử dụng blockchain hay tiền mã hoá thật.
    """
)

st.divider()

st.markdown("### 📦 Các module trong hệ thống")

modules = {
    "hash.py":        "Hàm băm SHA-256, so sánh bit, brute-force demo",
    "wallet.py":      "Tạo cặp khoá ECDSA (SECP256K1), ký và xác minh chữ ký",
    "transaction.py": "Credential và Transaction có chữ ký số",
    "merkle.py":      "Merkle Tree — xây dựng, sinh proof, xác minh",
    "block.py":       "BlockHeader và Block — đóng gói giao dịch",
    "blockchain.py":  "Chuỗi block — thêm block, kiểm tra tính hợp lệ",
    "mining.py":      "Proof of Work — tìm nonce thoả mãn difficulty",
    "mempool.py":     "Hàng chờ giao dịch chưa đóng block",
    "node.py":        "Full Node và Network — mô phỏng mạng ngang hàng",
}

for filename, desc in modules.items():
    st.markdown(f"- `blockchain/{filename}` — {desc}")

st.divider()
st.info("👈 Chọn trang ở sidebar để bắt đầu khám phá từng module.")
