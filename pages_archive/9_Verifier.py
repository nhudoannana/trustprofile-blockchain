"""Trang Verifier — placeholder.

Mục đích: sẽ cho phép nhập Credential ID để kiểm tra trạng thái trên blockchain.
"""

import streamlit as st
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from state import init_state

init_state()

st.header("9️⃣ Verifier")
st.warning("🚧 Trang này chưa được triển khai. Chờ bước tiếp theo.")
