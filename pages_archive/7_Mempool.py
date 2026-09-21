"""Trang Mempool — placeholder.

Mục đích: sẽ hiển thị hàng chờ giao dịch, thêm/xoá transaction.
"""

import streamlit as st
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from state import init_state

init_state()

st.header("7️⃣ Mempool")
st.warning("🚧 Trang này chưa được triển khai. Chờ bước tiếp theo.")
