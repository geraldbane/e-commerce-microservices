from flask import Flask, jsonify
from flask_pymongo import PyMongo
from flask_restx import Api, Resource, fields
import os
import uuid
from datetime import datetime

app = Flask(__name__)
app.config['MONGO_URI'] = os.getenv("MONGO_URI")
mongo = PyMongo(app)

api = Api(app, title="Payment Service API", version="1.0", doc="/")

payment_ns = api.namespace('payments', description='Payment operations')

# Payment model
payment_model = api.model('Payment', {
    'order_id': fields.String(required=True, description='Order ID'),
    'amount': fields.Float(required=True, description='Payment amount'),
    'status': fields.String(required=True, description='Payment status'),
    'timestamp': fields.String(required=True, description='Payment creation timestamp (ISO 8601)'),
    'updated': fields.String(required=True, description='Last updated timestamp (ISO 8601)'),
    'expired': fields.Boolean(required=True, description='Payment expiration status'),
    'payment_methods': fields.List(fields.String, required=True, description='Payment methods')
})

@payment_ns.route('/')
class PaymentList(Resource):
    @payment_ns.doc('list_payments')
    def get(self):
        data = list(mongo.db.payments.find())
        for item in data:
            item["_id"] = str(item["_id"])
            if "timestamp" in item and isinstance(item["timestamp"], datetime):
                item["timestamp"] = item["timestamp"].isoformat()
            if "updated" in item and isinstance(item["updated"], datetime):
                item["updated"] = item["updated"].isoformat()
        return jsonify(data)

    @payment_ns.doc('create_payment')
    @payment_ns.expect(payment_model)
    def post(self):
        args = api.payload
        required_fields = ['order_id', 'amount', 'status', 'timestamp', 'updated', 'expired', 'payment_methods']
        for field in required_fields:
            if field not in args:
                api.abort(400, f"Missing required field: {field}")
        args['payment_id'] = str(uuid.uuid4())
        try:
            timestamp = datetime.fromisoformat(args['timestamp'])
            updated = datetime.fromisoformat(args['updated'])
        except (ValueError, TypeError):
            api.abort(400, "Invalid timestamp or updated format. Use ISO 8601.")

        document = {
            "payment_id": args["payment_id"],
            "order_id": args["order_id"],
            "amount": float(args["amount"]),
            "status": args["status"],
            "timestamp": timestamp,
            "updated": updated,
            "expired": args["expired"],
            "payment_methods": args["payment_methods"]
        }
        result = mongo.db.payments.insert_one(document)
        document["_id"] = str(result.inserted_id)
        document["timestamp"] = timestamp.isoformat()
        document["updated"] = updated.isoformat()
        return document, 201

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5004, debug=True)