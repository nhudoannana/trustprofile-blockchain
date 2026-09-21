"""Trang Mining — mô phỏng Proof of Work, benchmark difficulty.

Mục đích: cho sinh viên trải nghiệm đào block, thấy thời gian
tăng theo cấp số nhân khi difficulty tăng, hiểu vì sao PoW an toàn.
"""

import time
import streamlit as st
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from state import init_state
from blockchain.block import Block
from blockchain.mining import mine_block, is_valid_pow

init_state()



st.header("7️⃣ Proof of Work — Mining")

# ══════════════════════════════════════════════
# PHẦN 1: Mine một block
# ══════════════════════════════════════════════
st.subheader("🔹 Đào Block")
st.caption("Chọn difficulty, bấm Mine. Miner thử nonce từ 0 đến khi hash bắt đầu bằng đủ số '0'.")

col1, col2 = st.columns([1, 2])
with col1:
    difficulty = st.slider("Difficulty (số ký tự '0' đầu hash):", 2, 5, 3, key="mine_diff")
    st.markdown(f"**Target:** hash bắt đầu bằng `{'0' * difficulty}…`")
    st.caption(f"Không gian: ~16^{difficulty} = ~{16**difficulty:,} lần thử trung bình")

with col2:
    if st.button("⛏️ Start Mining", key="btn_mine"):
        block = Block(
            transactions=[], height=1,
            previous_hash="0" * 64, difficulty=difficulty,
        )

        with st.spinner(f"Đang đào với difficulty={difficulty}..."):
            result = mine_block(block)

        st.success("✅ **Block successfully mined!**")
        st.markdown(f"**Nonce tìm được:** `{result['nonce']:,}`")
        st.markdown(f"**Số lần thử:** `{result['attempts']:,}`")
        st.markdown(f"**Thời gian:** `{result['seconds']:.4f}` giây")
        st.markdown(f"**Hash:**")
        st.code(result["block_hash"], language="text")

        # Đánh dấu các số 0 đầu
        leading = result["block_hash"][:difficulty]
        rest = result["block_hash"][difficulty:]
        st.markdown(f"Leading zeros: **`{leading}`**`{rest}`")

        # Verify
        assert is_valid_pow(block)
        st.caption("✅ is_valid_pow() xác nhận hợp lệ")

st.divider()

# ══════════════════════════════════════════════
# PHẦN 2: Benchmark
# ══════════════════════════════════════════════
st.subheader("🔹 Benchmark — So sánh difficulty")
st.caption("Mine 3 lần mỗi mức difficulty (2, 3, 4), xem thời gian trung bình tăng theo cấp số.")

if st.button("📊 Chạy Benchmark", key="btn_benchmark"):
    results_table = []
    chart_data = {}

    for diff in [2, 3, 4]:
        times = []
        attempts_list = []
        for trial in range(3):
            block = Block(
                transactions=[], height=1,
                previous_hash="0" * 64, difficulty=diff,
                # Dùng timestamp khác nhau mỗi lần để hash khác
                timestamp=f"2026-01-01T00:00:{trial:02d}+00:00",
            )
            result = mine_block(block)
            times.append(result["seconds"])
            attempts_list.append(result["attempts"])

        avg_time = sum(times) / len(times)
        avg_attempts = sum(attempts_list) / len(attempts_list)

        results_table.append({
            "Difficulty": diff,
            "Target": "0" * diff + "…",
            "Không gian (~)": f"{16**diff:,}",
            "Lần thử TB": f"{avg_attempts:,.0f}",
            "Thời gian TB (s)": f"{avg_time:.4f}",
            "Lần 1 (s)": f"{times[0]:.4f}",
            "Lần 2 (s)": f"{times[1]:.4f}",
            "Lần 3 (s)": f"{times[2]:.4f}",
        })
        chart_data[f"d={diff}"] = avg_time

    st.table(results_table)

    # Biểu đồ
    st.markdown("#### ⏱️ Thời gian trung bình theo Difficulty")
    st.bar_chart(chart_data)

    # Phân tích
    if len(results_table) >= 2:
        t2 = float(results_table[0]["Thời gian TB (s)"])
        t3 = float(results_table[1]["Thời gian TB (s)"])
        t4 = float(results_table[2]["Thời gian TB (s)"])
        st.info(
            f"📊 Tỷ lệ tăng: d=2→3: **×{t3/max(t2,0.0001):.1f}**, "
            f"d=3→4: **×{t4/max(t3,0.0001):.1f}** "
            f"(lý thuyết: ×16 mỗi cấp)"
        )

st.divider()

# ══════════════════════════════════════════════
# PHẦN 3: Câu hỏi thảo luận
# ══════════════════════════════════════════════
with st.expander("💬 Câu hỏi thảo luận"):
    st.markdown(
        """
        **1. PoW giúp đạt đồng thuận bằng cơ chế nào?**

        - **Chi phí tính toán**: tạo block mới tốn hàng nghìn–triệu phép hash.
        - **Xác minh tức thì**: kiểm tra PoW chỉ cần 1 phép hash.
        - **Chuỗi dài nhất thắng**: node chọn chuỗi có tổng công sức lớn nhất,
          vì chuỗi dài hơn = nhiều PoW hơn = nhiều tài nguyên thật hơn.
        - **Tấn công 51%**: muốn sửa chuỗi phải đào nhanh hơn toàn bộ mạng,
          cần > 50% sức mạnh tính toán — rất tốn kém.

        ---

        **2. Vì sao thời gian tăng theo cấp số nhân?**

        | Difficulty | Số 0 đầu | Xác suất hash hợp lệ | Lần thử TB |
        |---|---|---|---|
        | 2 | 00 | 1/256 | ~256 |
        | 3 | 000 | 1/4.096 | ~4.096 |
        | 4 | 0000 | 1/65.536 | ~65.536 |
        | 5 | 00000 | 1/1.048.576 | ~1 triệu |

        Mỗi cấp difficulty nhân không gian tìm kiếm lên **×16**.
        Bitcoin hiện tại có difficulty tương đương ~70+ số 0 đầu (dạng bit).

        ---

        **3. Tại sao xác minh PoW nhanh hơn tạo PoW?**

        - Tạo: thử hàng triệu nonce → hàng triệu phép hash.
        - Xác minh: chỉ 1 phép hash, kiểm tra có đủ số 0 không.
        - Đây là **bất đối xứng**: tốn công để tạo, dễ dàng để kiểm tra —
          giống như giải Sudoku khó nhưng kiểm tra đáp án thì nhanh.
        """
    )
