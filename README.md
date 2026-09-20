# TrustProfile

Hệ thống xác thực chứng nhận số bằng Blockchain — mô phỏng để học (educational simulation).

## Mô tả

Issuer ký và phát hành credential cho Holder. Credential trở thành Transaction,
đi qua Mempool, được Miner đóng gói vào Block bằng Proof of Work,
các Full Node xác minh và đồng thuận. Verifier nhập Credential ID để kiểm tra.

## Cài đặt

```bash
pip install -r requirements.txt
```

## Chạy

```bash
streamlit run app.py
```

## Chạy test

```bash
pytest tests/ -v
```
