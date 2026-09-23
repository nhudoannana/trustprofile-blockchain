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

    # Tự động seed wallet 3 trường Đại học Consortium từ PoS Registry
    # (chỉ chạy 1 lần khi session_state chưa có các validator wallets)
    if not st.session_state.get("_validators_seeded", False):
        try:
            network = get_network()
            pos_reg = getattr(network, "pos_registry", None)
            if pos_reg and pos_reg.validators:
                existing_addresses = {w["address"] for w in st.session_state.wallets}
                for v in pos_reg.validators.values():
                    if v.address not in existing_addresses:
                        st.session_state.wallets.append({
                            "name": v.name,
                            "private_key_pem": v.private_key_pem,
                            "public_key_hex": v.public_key_hex,
                            "address": v.address,
                        })
                st.session_state["_validators_seeded"] = True
        except Exception:
            pass  # Bỏ qua nếu network chưa sẵn sàng


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


def get_pos_registry():
    """Lấy PoSRegistry của liên minh TrustProfile Consortium dùng chung từ Network."""
    return get_network().pos_registry
