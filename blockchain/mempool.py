"""Module mempool — hàng chờ giao dịch chưa được đóng block.

Mục đích: lưu trữ tạm các giao dịch hợp lệ đang chờ miner chọn,
loại bỏ giao dịch trùng, sai chữ ký, hoặc Issuer không được phép
trước khi vào block.
"""

from blockchain.transaction import Transaction, verify_transaction


class DummyLedger:
    """Bản giả ledger_view — trả None cho mọi credential.

    Vì sao tồn tại: ở giai đoạn chưa có blockchain thật,
    dùng bản giả để test Mempool độc lập.
    Sẽ được thay bằng blockchain thật ở bước sau.
    """

    def credential_status(self, credential_id: str) -> str | None:
        """Luôn trả None — chưa có credential nào trên chain."""
        return None

    def credential_issuer(self, credential_id: str) -> str | None:
        """Luôn trả None — chưa biết ai phát hành."""
        return None


class Mempool:
    """Hàng chờ giao dịch chưa đóng block.

    Vì sao tồn tại: giao dịch cần được kiểm tra kỹ trước khi vào block —
    Mempool là bộ lọc đầu tiên, chỉ giữ lại giao dịch hợp lệ
    để miner không lãng phí công sức đào block chứa rác.
    """

    def __init__(self, authorized_issuers: set[str] | None = None):
        self._pool: dict[str, Transaction] = {}     # tx_id → Transaction
        self.authorized_issuers: set[str] = set(authorized_issuers or [])

    def add_transaction(self, tx: Transaction, ledger_view) -> tuple[bool, str]:
        """Thêm transaction vào Mempool sau 5 bước kiểm tra.

        Vì sao tồn tại: mỗi node tự kiểm tra trước khi lan truyền,
        ngăn giao dịch rác hoặc giả mạo lây lan trong mạng.

        Returns:
            (True, "Đã thêm vào Mempool") hoặc (False, lý do cụ thể).
        """
        # 1–2. Định dạng + chữ ký hợp lệ (verify_transaction kiểm tra cả hai)
        ok, reason = verify_transaction(tx)
        if not ok:
            return False, f"Từ chối — {reason}"

        # 3. Không trùng tx_id trong Mempool (chống replay / nộp lặp)
        if tx.tx_id in self._pool:
            return False, f"Từ chối — transaction đã tồn tại trong Mempool (trùng tx_id)"

        # 4. Issuer phải nằm trong registry (nếu registry không rỗng)
        if self.authorized_issuers and tx.sender_public_key not in self.authorized_issuers:
            return False, "Từ chối — Issuer không nằm trong danh sách được phép (unauthorized)"

        # 5. Kiểm tra trạng thái credential trên ledger
        cred_id = tx.payload.get("credential_id")
        if cred_id and tx.tx_type == "ISSUE":
            status = ledger_view.credential_status(cred_id)
            if status == "ACTIVE":
                return False, (
                    f"Từ chối — credential '{cred_id}' đã tồn tại "
                    f"và đang ACTIVE trên blockchain"
                )

        if cred_id and tx.tx_type == "REVOKE":
            status = ledger_view.credential_status(cred_id)
            if status != "ACTIVE":
                return False, (
                    f"Từ chối — credential '{cred_id}' không ở trạng thái "
                    f"ACTIVE (hiện tại: {status}), không thể thu hồi"
                )
            # Kiểm tra chỉ Issuer gốc mới được thu hồi
            issuer = ledger_view.credential_issuer(cred_id)
            if issuer and issuer != tx.sender_public_key:
                return False, "Từ chối — chỉ Issuer gốc mới có quyền thu hồi credential"

        # Tất cả kiểm tra đều qua → thêm vào pool
        self._pool[tx.tx_id] = tx
        return True, "Đã thêm vào Mempool"

    def remove_transactions(self, tx_ids: list[str]) -> None:
        """Xoá các transaction đã được đóng vào block.

        Vì sao tồn tại: sau khi miner đóng block thành công,
        các transaction trong block phải rời mempool để không bị đóng lại.
        """
        for tx_id in tx_ids:
            self._pool.pop(tx_id, None)

    def get_transactions(self) -> list[Transaction]:
        """Trả về danh sách transaction đang chờ trong Mempool.

        Vì sao tồn tại: miner gọi hàm này để lấy danh sách
        transaction cần đóng vào block tiếp theo.
        """
        return list(self._pool.values())
