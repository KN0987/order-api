from flask import request, jsonify
from werkzeug.exceptions import BadRequest

from .db import db_txn, get_db
from .utils import (
    utc_now_iso,
    new_uuid,
    request_fingerprint,
    json_dumps,
    json_loads,
    log_event,
)

def register_routes(app):

    @app.post("/orders")
    def create_order():
        # Validate Idempotency-Key header
        idem_key = request.headers.get("Idempotency-Key")
        if not idem_key:
            return jsonify({"error": "Missing Idempotency-Key header"}), 400

        # Validate JSON payload
        try:
            payload = request.get_json(force=True)
        except BadRequest:
            return jsonify({"error": "Invalid JSON body"}), 400

        required = ["customer_id", "item_id", "quantity"]
        missing = [k for k in required if k not in payload]
        if missing:
            return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

        customer_id = payload["customer_id"]
        item_id = payload["item_id"]
        quantity = payload["quantity"]

        if not isinstance(quantity, int) or quantity <= 0:
            return jsonify({"error": "quantity must be an integer > 0"}), 400

        # Compute request fingerprint (hash)
        req_hash = request_fingerprint(payload)

        # Check debug header for failure simulation (after commit)
        fail_after_commit = request.headers.get("X-Debug-Fail-After-Commit", "").lower() in ("1", "true", "yes")

        # Run idempotent create inside ONE transaction
        with db_txn() as db:
            # Look up existing idempotency record
            row = db.execute(
                """
                SELECT idempotency_key, request_hash, status_code, response_body
                FROM idempotency_records
                WHERE idempotency_key = ?
                """,
                (idem_key,),
            ).fetchone()

            if row:
                stored_hash = row["request_hash"]
                if stored_hash != req_hash:
                    log_event("orders.create.conflict", idempotency_key=idem_key)
                    # No DB changes; transaction will commit nothing new
                    return jsonify({"error": "Idempotency-Key reused with different payload"}), 409

                # Same key + same payload: return stored response if completed
                if row["status_code"] is not None and row["response_body"] is not None:
                    stored_status = int(row["status_code"])
                    stored_body = json_loads(row["response_body"])
                    log_event("orders.create.replay", idempotency_key=idem_key, order_id=stored_body.get("order_id"))
                    return jsonify(stored_body), stored_status

                # Edge case: exists but incomplete (should be rare). Treat as 500.
                log_event("orders.create.incomplete_record", idempotency_key=idem_key)
                return jsonify({"error": "Idempotency record exists but no stored response"}), 500

            # No idempotency record yet → create it (placeholder), then create order + ledger, then fill stored response
            now = utc_now_iso()

            db.execute(
                """
                INSERT INTO idempotency_records (idempotency_key, request_hash, status_code, response_body, created_at, updated_at)
                VALUES (?, ?, NULL, NULL, ?, ?)
                """,
                (idem_key, req_hash, now, now),
            )

            # Create order
            order_id = new_uuid()
            db.execute(
                """
                INSERT INTO orders (order_id, customer_id, item_id, quantity, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (order_id, customer_id, item_id, quantity, now),
            )

            # Create ledger (charge)
            # If you don't have pricing, charge = quantity is fine for the assignment.
            ledger_id = new_uuid()
            amount = quantity
            db.execute(
                """
                INSERT INTO ledger (ledger_id, order_id, customer_id, amount, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (ledger_id, order_id, customer_id, amount, now),
            )

            # Store the response for replays
            response_body = {"order_id": order_id, "status": "created"}
            db.execute(
                """
                UPDATE idempotency_records
                SET status_code = ?, response_body = ?, updated_at = ?
                WHERE idempotency_key = ?
                """,
                (201, json_dumps(response_body), utc_now_iso(), idem_key),
            )

            log_event("orders.create.success", idempotency_key=idem_key, order_id=order_id)

        # Failure simulation AFTER COMMIT
        if fail_after_commit:
            # DB has already committed at this point
            log_event("orders.create.fail_after_commit", idempotency_key=idem_key)
            raise RuntimeError("Simulated failure after commit (response lost)")

        return jsonify({"order_id": order_id, "status": "created"}), 201


    @app.get("/orders/<order_id>")
    def get_order(order_id):
        db = get_db()
        row = db.execute(
            """
            SELECT order_id, customer_id, item_id, quantity, created_at
            FROM orders
            WHERE order_id = ?
            """,
            (order_id,),
        ).fetchone()

        if not row:
            return jsonify({"error": "Order not found"}), 404

        return jsonify(
            {
                "order_id": row["order_id"],
                "customer_id": row["customer_id"],
                "item_id": row["item_id"],
                "quantity": row["quantity"],
                "created_at": row["created_at"],
            }
        ), 200
