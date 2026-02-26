PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS orders (
  order_id TEXT PRIMARY KEY,
  customer_id TEXT NOT NULL,
  item_id TEXT NOT NULL,
  quantity INTEGER NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ledger (
  ledger_id TEXT PRIMARY KEY,
  order_id TEXT NOT NULL,
  customer_id TEXT NOT NULL,
  amount INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY(order_id) REFERENCES orders(order_id),
  UNIQUE(order_id)
);

CREATE TABLE IF NOT EXISTS idempotency_records (
  idempotency_key TEXT PRIMARY KEY,
  request_hash TEXT NOT NULL,
  status_code INTEGER,
  response_body TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);