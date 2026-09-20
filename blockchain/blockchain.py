"""Module blockchain — quản lý chuỗi các block.

Mục đích: duy trì danh sách block theo thứ tự, kiểm tra tính hợp lệ
toàn chuỗi (hash liên kết, Merkle root) để phát hiện giả mạo.
"""

from blockchain.block import Block, BlockHeader
from blockchain.hash import sha256_hex
from blockchain.merkle import (
    calculate_merkle_root, generate_merkle_proof, verify_merkle_proof,
)
from blockchain.mining import is_valid_pow
from blockchain.transaction import verify_transaction


class Blockchain:
    """Chuỗi block liên kết qua hash, bắt đầu từ Genesis Block.

    Vì sao tồn tại: blockchain là sổ cái bất biến — mỗi block khoá chặt
    block trước bằng hash, sửa một block buộc phải sửa tất cả block sau.
    """

    def __init__(self):
        self.chain: list[Block] = [self._create_genesis()]

    def _create_genesis(self) -> Block:
        """Tạo Genesis Block — block đầu tiên, previous_hash toàn số 0.

        Vì sao tồn tại: mọi blockchain cần một điểm khởi đầu cố định
        mà tất cả node đều đồng ý, không phụ thuộc block trước.
        """
        return Block(
            transactions=[],
            height=0,
            previous_hash="0" * 64,
            timestamp="2026-01-01T00:00:00+00:00",
        )

    def add_block(self, block: Block) -> None:
        """Thêm block vào cuối chuỗi.

        Vì sao tồn tại: sau khi miner đào thành công và node xác minh,
        block mới được nối vào chuỗi, mở rộng sổ cái.
        """
        self.chain.append(block)

    def get_latest_block(self) -> Block:
        """Trả về block mới nhất (cuối chuỗi).

        Vì sao tồn tại: khi tạo block mới, cần hash của block cuối
        để gán vào previous_hash, duy trì liên kết chuỗi.
        """
        return self.chain[-1]

    def is_chain_valid(self) -> tuple[bool, int | None, str]:
        """Kiểm tra tính hợp lệ toàn chuỗi, trả về block sai đầu tiên.

        Vì sao tồn tại: bất kỳ node nào cũng phải tự kiểm tra toàn chuỗi
        trước khi tin tưởng — đây là bản chất trustless của blockchain.

        Kiểm tra:
        1. merkle_root khớp danh sách giao dịch thực tế trong block.
        2. previous_hash của mỗi block khớp hash block trước.
        3. Proof of Work hợp lệ (trừ Genesis).

        Returns:
            (True, None, "Chain hợp lệ") hoặc
            (False, chỉ_số_block_sai, lý_do).
        """
        for i in range(len(self.chain)):
            block = self.chain[i]

            # 1. Kiểm tra merkle_root khớp giao dịch
            tx_hashes = [tx.tx_id for tx in block.transactions]
            expected_root = calculate_merkle_root(tx_hashes)
            if block.header.merkle_root != expected_root:
                return (
                    False, i,
                    f"Block {i}: merkle_root không khớp danh sách giao dịch "
                    f"(header={block.header.merkle_root[:16]}…, "
                    f"expected={expected_root[:16]}…)"
                )

            # 2–3 chỉ áp dụng cho block sau genesis
            if i > 0:
                # 2. Kiểm tra previous_hash
                prev_hash_expected = self.chain[i - 1].compute_hash()
                if block.header.previous_hash != prev_hash_expected:
                    return (
                        False, i,
                        f"Block {i}: previous_hash không khớp hash Block {i - 1} "
                        f"(stored={block.header.previous_hash[:16]}…, "
                        f"expected={prev_hash_expected[:16]}…)"
                    )

                # 3. Kiểm tra Proof of Work
                if not is_valid_pow(block):
                    block_hash = block.compute_hash()
                    return (
                        False, i,
                        f"Block {i}: Proof of Work không hợp lệ "
                        f"(hash={block_hash[:16]}…, "
                        f"cần {block.header.difficulty} ký tự '0' đầu)"
                    )

        return (True, None, "Chain hợp lệ")

    # ── Ledger View (thay DummyLedger bằng dữ liệu thật từ chain) ──

    def credential_status(self, credential_id: str) -> str | None:
        """Quét toàn bộ chain, trả trạng thái credential: ACTIVE / REVOKED / None.

        Vì sao tồn tại: Mempool cần kiểm tra trạng thái credential trước
        khi chấp nhận ISSUE (chưa tồn tại) hoặc REVOKE (đang ACTIVE).
        Đây là ledger_view thật, thay thế DummyLedger ở Bước 5.
        """
        status = None
        for block in self.chain:
            for tx in block.transactions:
                cred = tx.payload.get("credential_id")
                if cred == credential_id:
                    if tx.tx_type == "ISSUE":
                        status = "ACTIVE"
                    elif tx.tx_type == "REVOKE":
                        status = "REVOKED"
        return status

    def credential_issuer(self, credential_id: str) -> str | None:
        """Tìm public key của Issuer đã cấp credential.

        Vì sao tồn tại: khi REVOKE, cần xác minh người gửi
        chính là Issuer gốc — không ai khác được phép thu hồi.
        """
        for block in self.chain:
            for tx in block.transactions:
                if (tx.tx_type == "ISSUE"
                        and tx.payload.get("credential_id") == credential_id):
                    return tx.sender_public_key
        return None

    # ── Verify Credential (12 bước) ──

    def verify_credential(
        self, credential_id: str, authorized_issuers: set[str] | None = None,
    ) -> tuple[list[tuple[str, bool, str]], str, dict]:
        """Xác minh credential qua 12 bước, trả kết quả từng bước.

        Vì sao tồn tại: Verifier cần kiểm chứng toàn bộ đường đi của
        credential — từ TX đến block đến chuỗi — để tin tưởng tuyệt đối
        mà không cần tin ai cả (trustless verification).

        Returns:
            (steps, final_status, info)
            - steps: list[(tên_bước, passed, chi_tiết)]
            - final_status: "VERIFIED" | "REVOKED" | "NOT_FOUND" | "INVALID"
            - info: dict thông tin credential, block, TX
        """
        steps: list[tuple[str, bool, str]] = []
        info: dict = {}

        # ── Tìm TX ISSUE và REVOKE trong chain ──
        issue_tx = None
        issue_block = None
        issue_block_idx = None
        revoke_tx = None
        revoke_block_idx = None

        for idx, block in enumerate(self.chain):
            for tx in block.transactions:
                cid = tx.payload.get("credential_id")
                if cid == credential_id:
                    if tx.tx_type == "ISSUE" and issue_tx is None:
                        issue_tx = tx
                        issue_block = block
                        issue_block_idx = idx
                    elif tx.tx_type == "REVOKE" and revoke_tx is None:
                        revoke_tx = tx
                        revoke_block_idx = idx

        # ── Bước 1: Credential tồn tại ──
        if issue_tx is None:
            steps.append((
                "Credential tồn tại", False,
                f"Không tìm thấy credential '{credential_id}' trong blockchain",
            ))
            return steps, "NOT_FOUND", info
        steps.append((
            "Credential tồn tại", True,
            f"Tìm thấy trong Block {issue_block_idx}",
        ))

        # Thu thập info
        info = {
            "credential_id": credential_id,
            "issuer_name": issue_tx.payload.get("issuer_name", "—"),
            "holder_name": issue_tx.payload.get("holder_name", "—"),
            "title": issue_tx.payload.get("title", "—"),
            "issue_date": issue_tx.payload.get("issue_date", "—"),
            "issuer_public_key": issue_tx.sender_public_key,
            "issue_tx_id": issue_tx.tx_id,
            "issue_block_height": issue_block.height,
            "issue_block_hash": issue_block.compute_hash(),
            "issue_merkle_root": issue_block.header.merkle_root,
        }
        if revoke_tx:
            info["revoke_tx_id"] = revoke_tx.tx_id
            info["revoke_block_height"] = revoke_block_idx
            info["revoke_reason"] = revoke_tx.payload.get("reason", "—")

        # ── Bước 2: TX tồn tại ──
        steps.append(("TX tồn tại", True, f"tx_id: {issue_tx.tx_id[:24]}…"))

        # ── Bước 3: TX hash đúng ──
        if issue_tx.compute_hash() == issue_tx.tx_id:
            steps.append(("TX hash đúng", True, "tx_id khớp compute_hash()"))
        else:
            steps.append(("TX hash đúng", False, "tx_id ≠ compute_hash() — dữ liệu bị sửa"))
            return steps, "INVALID", info

        # ── Bước 4: Chữ ký Issuer ──
        sig_ok, sig_reason = verify_transaction(issue_tx)
        if sig_ok:
            steps.append(("Chữ ký Issuer hợp lệ", True, "ECDSA signature verified"))
        else:
            steps.append(("Chữ ký Issuer hợp lệ", False, sig_reason))
            return steps, "INVALID", info

        # ── Bước 5: Issuer trong registry ──
        if authorized_issuers:
            if issue_tx.sender_public_key in authorized_issuers:
                steps.append(("Issuer trong registry", True, "Issuer được phép"))
            else:
                steps.append(("Issuer trong registry", False, "Issuer không nằm trong danh sách"))
                return steps, "INVALID", info
        else:
            steps.append(("Issuer trong registry", True, "Bỏ qua (registry mở)"))

        # ── Bước 6: Block chứa TX ──
        steps.append((
            "Block chứa TX tồn tại", True,
            f"Block {issue_block_idx}, height {issue_block.height}",
        ))

        # ── Bước 7: Merkle Proof ──
        tx_hashes = [t.tx_id for t in issue_block.transactions]
        tx_index = tx_hashes.index(issue_tx.tx_id)
        root = calculate_merkle_root(tx_hashes)
        proof = generate_merkle_proof(tx_hashes, tx_index)
        proof_ok = verify_merkle_proof(issue_tx.tx_id, proof, root)
        if proof_ok and root == issue_block.header.merkle_root:
            steps.append((
                "Merkle Proof khớp Root", True,
                f"Proof: {len(proof)} hash, khớp Merkle Root của block",
            ))
        else:
            steps.append(("Merkle Proof khớp Root", False, "Proof/Root không khớp"))
            return steps, "INVALID", info

        # ── Bước 8: Block hash đúng ──
        block_hash = issue_block.compute_hash()
        steps.append(("Block hash đúng", True, f"hash: {block_hash[:24]}…"))

        # ── Bước 9: previous_hash đúng ──
        if issue_block_idx > 0:
            exp_prev = self.chain[issue_block_idx - 1].compute_hash()
            if issue_block.header.previous_hash == exp_prev:
                steps.append(("previous_hash đúng", True, "Khớp hash block trước"))
            else:
                steps.append(("previous_hash đúng", False, "Không khớp"))
                return steps, "INVALID", info
        else:
            steps.append(("previous_hash đúng", True, "Genesis block"))

        # ── Bước 10: PoW hợp lệ ──
        if issue_block_idx == 0 or is_valid_pow(issue_block):
            steps.append((
                "PoW hợp lệ", True,
                f"difficulty={issue_block.header.difficulty}, "
                f"nonce={issue_block.header.nonce:,}",
            ))
        else:
            steps.append(("PoW hợp lệ", False, "Block không thoả mãn PoW"))
            return steps, "INVALID", info

        # ── Bước 11: Blockchain hợp lệ ──
        chain_ok, _, chain_reason = self.is_chain_valid()
        if chain_ok:
            steps.append((
                "Blockchain hợp lệ", True,
                f"Toàn bộ {len(self.chain)} block hợp lệ",
            ))
        else:
            steps.append(("Blockchain hợp lệ", False, chain_reason))
            return steps, "INVALID", info

        # ── Bước 12: Trạng thái hiện tại ──
        status = self.credential_status(credential_id)
        if status == "ACTIVE":
            steps.append(("Trạng thái", True, "✅ ACTIVE"))
            return steps, "VERIFIED", info
        elif status == "REVOKED":
            detail = "🔴 REVOKED"
            if revoke_block_idx is not None:
                detail += f" tại Block {revoke_block_idx}"
            steps.append(("Trạng thái", False, detail))
            return steps, "REVOKED", info
        else:
            steps.append(("Trạng thái", False, "Trạng thái không xác định"))
            return steps, "INVALID", info

