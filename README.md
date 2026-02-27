# Assignment 2
**Tech Stack:** Python 3.11, Flask, SQLite  
**Public Base URL:** `http://3.101.124.41:8000`

---
##  Endpoints
- `POST /orders` 
- `GET /orders/{order_id}`  
- `GET /health` (utility)

## Verify endpoints

### 1) Basic Order Creation
```bash
curl -X POST http://3.101.124.41:8000/orders \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: test-123" \
  -d '{"customer_id":"cust1","item_id":"item1","quantity":1}'
```

### 2) Retry with Same Idempotency Key
```bash
curl -X POST http://3.101.124.41:8000/orders \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: test-123" \
  -d '{"customer_id":"cust1","item_id":"item1","quantity":1}'
```

### 3) Same Key, Different Payload (Conflict Case)
```bash
curl -X POST http://3.101.124.41:8000/orders \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: test-123" \
  -d '{"customer_id":"cust1","item_id":"item1","quantity":5}'
```

### 4) Simulated Failure After Commit
```bash
curl -X POST http://3.101.124.41:8000/orders \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: test-fail-1" \
  -H "X-Debug-Fail-After-Commit: true" \
  -d '{"customer_id":"cust2","item_id":"item2","quantity":1}'
```

### 5) Retry After Simulated Failure
```bash
curl -X POST http://3.101.124.41:8000/orders \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: test-fail-1" \
  -d '{"customer_id":"cust2","item_id":"item2","quantity":1}'
```

### 6) Verify Order Exists
```bash
curl http://3.101.124.41:8000/orders/<order_id>
```

---

## How to Run Locally
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export FLASK_APP="app:create_app"  
flask run --host 0.0.0.0 --port 8000
```

---

## Deployment Info (EC2)
- **Instance Type:** t3.micro
- **OS:** Ubuntu 22.04 LTS
- **Port:** 8000
- **Security Group Inbound Rules:**
  - SSH: TCP 22 (source: my IP)
  - API: Custom TCP 8000 (source: 0.0.0.0/0)
 
  ## Deploy to EC2 (Ubuntu)

### 1) Install dependencies
```bash
sudo apt update
sudo apt install -y python3-pip python3-venv git sqlite3
```

### 2) Clone repo and install Python dependencies
```bash
git clone https://github.com/KN0987/order-api.git
cd order-api
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3) Create DB directory
```bash
mkdir -p /home/ubuntu/order-api-data
```

### 4) Run with Gunicorn (manual test)
```bash
export DATABASE_PATH=/home/ubuntu/order-api-data/orders.db
gunicorn -w 2 -b 0.0.0.0:8000 "app:create_app()"
```


### 5) Run as a service (systemd)

Create service file
```bash
sudo nano /etc/systemd/system/order-api.service
```
Paste the following
```bash
[Unit]
Description=Order API (Flask + Gunicorn)
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/order-api
Environment=DATABASE_PATH=/home/ubuntu/order-api-data/orders.db
Environment=PYTHONUNBUFFERED=1
ExecStart=/home/ubuntu/order-api/.venv/bin/gunicorn -w 2 -b 0.0.0.0:8000 "app:create_app()"
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Enable and start the service
```bash
sudo systemctl daemon-reload
sudo systemctl enable order-api
sudo systemctl start order-api
sudo systemctl status order-api --no-pager
```
