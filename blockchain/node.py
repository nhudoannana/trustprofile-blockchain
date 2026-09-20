"""Module node — Full Node và Network (mạng ngang hàng mô phỏng).

Mục đích: mỗi Node giữ bản sao blockchain và mempool riêng,
nhận giao dịch/block qua inbox và tự xác minh trước khi chấp nhận,
mô phỏng tính phi tập trung — không ai tin ai, mọi node tự kiểm tra.
"""

import copy
import queue
import threading
import time
from dataclasses import dataclass
from datetime import datetime

from blockchain.block import Block
from blockchain.blockchain import Blockchain
from blockchain.mempool import Mempool
from blockchain.merkle import calculate_merkle_root
from blockchain.mining import mine_block, is_valid_pow
from blockchain.transaction import verify_transaction


@dataclass
class Message:
    """Thông điệp trao đổi giữa các node.

    Vì sao tồn tại: trong mạng P2P, node giao tiếp qua message —
    mỗi loại message kích hoạt một quy trình xử lý khác nhau.
    """
    msg_type: str       # "TX", "BLOCK", "SYNC_REQUEST", "SYNC_RESPONSE"
    sender_id: str      # node_id của người gửi
    payload: object     # Transaction, Block, Blockchain, …


class Node:
    """Full Node — giữ blockchain, mempool riêng và xử lý message bằng thread.

    Vì sao tồn tại: mỗi node là một thực thể độc lập, tự xác minh
    mọi thứ nhận được — đây là nền tảng của tính phi tập trung.
    """

    def __init__(self, node_id: str, host: str, port: int,
                 network: "Network", authorized_issuers: set[str] | None = None):
        self.node_id = node_id
        self.host = host
        self.port = port
        self.status = "ONLINE"

        self.blockchain = Blockchain()
        self.mempool = Mempool(authorized_issuers)
        self.network = network

        self.inbox: queue.Queue = queue.Queue()
        self._seen_tx_ids: set[str] = set()

        # Thread xử lý message — chạy song song thật
        self._running = True
        self._worker = threading.Thread(
            target=self._process_loop, daemon=True, name=f"worker-{node_id}",
        )
        self._worker.start()

    @property
    def height(self) -> int:
        """Chiều cao chuỗi = số block - 1 (genesis = 0)."""
        return len(self.blockchain.chain) - 1

    # ── API công khai (gọi từ main thread / UI) ──

    def submit_transaction(self, tx) -> tuple[bool, str]:
        """Nhận transaction từ bên ngoài, verify, thêm mempool, broadcast.

        Vì sao tồn tại: đây là điểm nhập cho giao dịch mới —
        node đầu tiên kiểm tra rồi lan truyền cho toàn mạng.
        """
        if self.status != "ONLINE":
            return False, f"{self.node_id} đang OFFLINE"

        # Dùng blockchain thật làm ledger_view (thay DummyLedger từ Bước 5)
        ok, reason = self.mempool.add_transaction(tx, self.blockchain)
        if not ok:
            self.network.log_event(self.node_id, f"TX REJECT: {reason}")
            return False, reason

        self._seen_tx_ids.add(tx.tx_id)
        self.network.log_event(
            self.node_id, f"TX ACCEPT: {tx.tx_id[:16]}… → broadcast to peers"
        )

        # Chuyển tiếp cho tất cả peer
        msg = Message("TX", self.node_id, tx)
        self.network.broadcast(self.node_id, msg)
        return True, "Accepted — đã thêm vào Mempool và broadcast"

    def mine_pending(self, max_txs: int = 10, difficulty: int = 3) -> tuple:
        """Lấy Tx từ Mempool, tạo Block, mine (PoW), broadcast.

        Vì sao tồn tại: đây là luồng chính tạo block mới —
        gom giao dịch chờ, đóng gói, chứng minh công sức tính toán,
        rồi phát cho mạng để đạt đồng thuận.

        Returns:
            (block, mining_result) nếu thành công, (None, lý_do) nếu thất bại.
        """
        if self.status != "ONLINE":
            return None, "Node đang OFFLINE"

        txs = self.mempool.get_transactions()[:max_txs]
        if not txs:
            return None, "Mempool trống — không có TX để mine"

        prev_hash = self.blockchain.get_latest_block().compute_hash()
        height = len(self.blockchain.chain)

        block = Block(
            transactions=list(txs), height=height,
            previous_hash=prev_hash, difficulty=difficulty,
        )

        self.network.log_event(
            self.node_id,
            f"⛏️ Mining started: {len(txs)} TXs, difficulty={difficulty}",
        )

        result = mine_block(block)

        self.network.log_event(
            self.node_id,
            f"⛏️ Block mined! height={height}, nonce={result['nonce']:,}, "
            f"attempts={result['attempts']:,}, time={result['seconds']:.4f}s",
        )

        # Thêm vào chain của chính mình
        self.blockchain.add_block(block)

        # Xoá Tx đã đóng gói khỏi Mempool
        tx_ids = [tx.tx_id for tx in txs]
        self.mempool.remove_transactions(tx_ids)

        self.network.log_event(
            self.node_id,
            f"✅ Block added. Height: {self.height}. "
            f"Mempool remaining: {len(self.mempool.get_transactions())}",
        )

        # Broadcast block cho peers
        msg = Message("BLOCK", self.node_id, block)
        self.network.broadcast(self.node_id, msg)

        self.network.log_event(self.node_id, "📡 Block broadcast to peers")

        return block, result

    def request_sync(self) -> None:
        """Yêu cầu đồng bộ chain từ các peer.

        Vì sao tồn tại: node mới tham gia hoặc vừa online lại
        cần lấy chuỗi dài nhất hợp lệ từ mạng để bắt kịp.
        """
        msg = Message("SYNC_REQUEST", self.node_id, None)
        self.network.broadcast(self.node_id, msg)
        self.network.log_event(self.node_id, "SYNC_REQUEST → all peers")

    def go_online(self) -> None:
        """Bật node lên trạng thái ONLINE."""
        self.status = "ONLINE"
        self.network.log_event(self.node_id, "Status → ONLINE")

    def go_offline(self) -> None:
        """Tắt node — message đến sẽ bị Network bỏ qua."""
        self.status = "OFFLINE"
        while not self.inbox.empty():
            try:
                self.inbox.get_nowait()
            except queue.Empty:
                break
        self.network.log_event(self.node_id, "Status → OFFLINE")

    # ── Vòng lặp xử lý message (chạy trong thread riêng) ──

    def _process_loop(self):
        """Liên tục lấy message từ inbox và xử lý."""
        while self._running:
            try:
                msg = self.inbox.get(timeout=0.3)
                if self.status == "ONLINE":
                    self._handle_message(msg)
            except queue.Empty:
                continue

    def _handle_message(self, msg: Message):
        """Phân loại và xử lý message theo loại."""
        if msg.msg_type == "TX":
            self._handle_tx(msg)
        elif msg.msg_type == "BLOCK":
            self._handle_block(msg)
        elif msg.msg_type == "SYNC_REQUEST":
            self._handle_sync_request(msg)
        elif msg.msg_type == "SYNC_RESPONSE":
            self._handle_sync_response(msg)

    # ── TX handler ──

    def _handle_tx(self, msg: Message):
        """Nhận TX từ peer: verify, thêm mempool. Không forward lại."""
        tx = msg.payload
        if tx.tx_id in self._seen_tx_ids:
            return
        self._seen_tx_ids.add(tx.tx_id)

        # Dùng blockchain thật làm ledger_view
        ok, reason = self.mempool.add_transaction(tx, self.blockchain)
        if ok:
            self.network.log_event(
                self.node_id,
                f"TX ACCEPT (relay from {msg.sender_id}): {tx.tx_id[:16]}…",
            )
        else:
            self.network.log_event(
                self.node_id,
                f"TX REJECT (relay from {msg.sender_id}): {reason}",
            )

    # ── BLOCK handler — consensus ──

    def _handle_block(self, msg: Message):
        """Nhận block từ peer: kiểm tra toàn bộ rồi accept hoặc reject.

        Vì sao tồn tại: mỗi node phải tự kiểm tra mọi block nhận được —
        không tin tưởng miner. Đây là bản chất trustless.

        Kiểm tra theo thứ tự:
        1. previous_hash khớp tip hiện tại (nếu không → fork/stale → sync).
        2. Merkle root khớp danh sách TX.
        3. Proof of Work hợp lệ.
        4. Mỗi TX: chữ ký hợp lệ + kiểm tra ledger (credential status).
        """
        block = msg.payload
        my_tip = self.blockchain.get_latest_block().compute_hash()

        # 1. Kiểm tra previous_hash khớp tip
        if block.header.previous_hash != my_tip:
            self.network.log_event(
                self.node_id,
                f"⚠️ STALE/FORK detected from {msg.sender_id}: "
                f"block prev_hash ≠ our tip → triggering sync",
            )
            self.request_sync()
            return

        # 2. Kiểm tra merkle_root
        tx_hashes = [tx.tx_id for tx in block.transactions]
        expected_root = calculate_merkle_root(tx_hashes)
        if block.header.merkle_root != expected_root:
            self.network.log_event(
                self.node_id,
                f"❌ BLOCK REJECTED from {msg.sender_id}: "
                f"merkle_root không khớp danh sách TX",
            )
            return

        # 3. Kiểm tra Proof of Work
        if not is_valid_pow(block):
            self.network.log_event(
                self.node_id,
                f"❌ BLOCK REJECTED from {msg.sender_id}: "
                f"PoW không hợp lệ (cần {block.header.difficulty} số '0' đầu)",
            )
            return

        # 4. Kiểm tra từng TX (chữ ký + ledger)
        for tx in block.transactions:
            ok, reason = verify_transaction(tx)
            if not ok:
                self.network.log_event(
                    self.node_id,
                    f"❌ BLOCK REJECTED from {msg.sender_id}: "
                    f"TX {tx.tx_id[:12]}… invalid: {reason}",
                )
                return

            # Kiểm tra ledger — credential status
            cred_id = tx.payload.get("credential_id")
            if cred_id and tx.tx_type == "ISSUE":
                status = self.blockchain.credential_status(cred_id)
                if status == "ACTIVE":
                    self.network.log_event(
                        self.node_id,
                        f"❌ BLOCK REJECTED from {msg.sender_id}: "
                        f"credential {cred_id} đã ACTIVE",
                    )
                    return

        # ═══ Tất cả kiểm tra OK → ACCEPT ═══
        self.blockchain.add_block(block)

        # Xoá TX đã đóng gói khỏi Mempool
        tx_ids = [tx.tx_id for tx in block.transactions]
        self.mempool.remove_transactions(tx_ids)

        self.network.log_event(
            self.node_id,
            f"✅ BLOCK ACCEPTED from {msg.sender_id}: "
            f"height {block.height}, {len(block.transactions)} TXs. "
            f"My height: {self.height}",
        )

    # ── SYNC handlers ──

    def _handle_sync_request(self, msg: Message):
        """Peer yêu cầu chain → gửi bản sao chain hiện tại."""
        chain_copy = copy.deepcopy(self.blockchain)
        response = Message("SYNC_RESPONSE", self.node_id, chain_copy)
        self.network.send(self.node_id, msg.sender_id, response)
        self.network.log_event(
            self.node_id,
            f"SYNC_RESPONSE → {msg.sender_id} (height {self.height})",
        )

    def _handle_sync_response(self, msg: Message):
        """Nhận chain từ peer — chấp nhận nếu dài hơn và hợp lệ.

        Vì sao tồn tại: quy tắc chuỗi dài nhất — node luôn chọn
        chuỗi hợp lệ có nhiều block nhất.
        """
        peer_bc = msg.payload
        peer_height = len(peer_bc.chain) - 1

        if peer_height <= self.height:
            self.network.log_event(
                self.node_id,
                f"SYNC SKIP from {msg.sender_id}: "
                f"peer height {peer_height} ≤ my height {self.height}",
            )
            return

        ok, _, reason = peer_bc.is_chain_valid()
        if ok:
            self.blockchain = peer_bc
            self.network.log_event(
                self.node_id,
                f"🔄 CHAIN UPDATED from {msg.sender_id} "
                f"(height → {self.height})",
            )
        else:
            self.network.log_event(
                self.node_id,
                f"CHAIN REJECTED from {msg.sender_id}: {reason}",
            )


class Network:
    """Mạng ngang hàng mô phỏng — kết nối các Node với nhau.

    Vì sao tồn tại: trong blockchain thật, node giao tiếp qua TCP/IP.
    Ở đây dùng queue để mô phỏng — mỗi node nhận message qua inbox,
    giữ nguyên nguyên lý: mọi node bình đẳng, tự xác minh.
    """

    def __init__(self):
        self.nodes: dict[str, Node] = {}
        self._event_log: list[str] = []
        self._log_lock = threading.Lock()

    def create_node(self, node_id: str, host: str, port: int,
                    authorized_issuers: set[str] | None = None) -> Node:
        """Tạo và đăng ký node mới vào mạng."""
        node = Node(node_id, host, port, self, authorized_issuers)
        self.nodes[node_id] = node
        self.log_event(node_id, f"Registered at {host}:{port}")
        return node

    def send(self, from_id: str, to_id: str, message: Message) -> bool:
        """Gửi message trực tiếp đến 1 node."""
        if to_id in self.nodes:
            target = self.nodes[to_id]
            if target.status == "ONLINE":
                target.inbox.put(message)
                return True
        return False

    def broadcast(self, from_id: str, message: Message) -> None:
        """Gửi message cho tất cả node khác đang ONLINE."""
        for node_id, node in self.nodes.items():
            if node_id != from_id and node.status == "ONLINE":
                node.inbox.put(message)

    def log_event(self, node_id: str, event: str) -> None:
        """Ghi log thread-safe, có timestamp và node_id."""
        with self._log_lock:
            ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            self._event_log.append(f"[{ts}] [{node_id}] {event}")

    def get_event_log(self, last_n: int = 50) -> list[str]:
        """Trả về n dòng log gần nhất."""
        with self._log_lock:
            return list(self._event_log[-last_n:])

    def clear_event_log(self) -> None:
        """Xoá toàn bộ log."""
        with self._log_lock:
            self._event_log.clear()
