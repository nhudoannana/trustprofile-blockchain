"""Trang Block & Mining — placeholder.

Mục đích: sẽ cho phép tạo block, đào bằng PoW, xem kết quả.
"""

import streamlit as st
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from state import init_state

init_state()

st.header("5️⃣ Block & Mining")
st.warning("🚧 Trang này chưa được triển khai. Chờ bước tiếp theo.")
