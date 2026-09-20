"""Trang Blockchain — placeholder.

Mục đích: sẽ hiển thị chuỗi block, kiểm tra tính hợp lệ toàn chuỗi.
"""

import streamlit as st
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from state import init_state

init_state()

st.header("6️⃣ Blockchain")
st.warning("🚧 Trang này chưa được triển khai. Chờ bước tiếp theo.")
