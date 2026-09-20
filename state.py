"""Module state — khởi tạo trạng thái dùng chung cho Streamlit.

Mục đích: tập trung quản lý session_state để tránh lặp code khởi tạo
ở nhiều trang, đảm bảo mọi trang đều thấy cùng một trạng thái.
"""

import streamlit as st


def init_state():
    """Khởi tạo các khoá mặc định trong st.session_state.

    Gọi hàm này ở đầu mỗi trang để đảm bảo session_state luôn có
    đủ các khoá cần thiết, tránh KeyError khi truy cập lần đầu.
    """
    if "wallets" not in st.session_state:
        st.session_state.wallets = []          # danh sách Wallet đã tạo

    if "event_log" not in st.session_state:
        st.session_state.event_log = []        # log sự kiện: list[str]


@st.cache_resource
def get_network():
    """Tạo Network với 3 Full Node — chia sẻ giữa mọi trang.

    cache_resource giữ nguyên đối tượng (kể cả thread) qua mọi lần rerun.
    """
    from blockchain.node import Network
    net = Network()
    net.create_node("Node-1", "127.0.0.1", 5001)
    net.create_node("Node-2", "127.0.0.1", 5002)
    net.create_node("Node-3", "127.0.0.1", 5003)
    return net
