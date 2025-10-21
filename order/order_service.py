from flask import Flask, jsonify
from flask_pymongo import PyMongo
from flask_restx import Api, Resource, fields
import os
import uuid
from datetime import datetime

app = Flask(__name__)
app.config['MONGO_URI'] = os.getenv("MONGO_URI")
mongo = PyMongo(app)

api = Api(app, title="Order Service API", version="1.0", doc="/")

order_ns = api.namespace('orders', description='Order operations')

# Order model
order_model = api.model('Order', {
    'customer_id': fields.String(required=True, description='Customer ID'),
    'products': fields.List(fields.Raw, required=True, description='List of products with product_id and quantity'),
    'total_amount': fields.Float(required=True, description='Total order amount'),
    'status': fields.String(required=True, description='Order status'),
    'timestamp': fields.String(required=True, description='Order creation timestamp (ISO 8601)'),
    'updated': fields.String(required=True, description='Last updated timestamp (ISO 8601)'),
    'confirmed': fields.Boolean(required=True, description='Order confirmation status'),
    'tracking_numbers': fields.List(fields.String, required=True, description='Tracking numbers')
})

@order_ns.route('/')
class OrderList(Resource):
    @order_ns.doc('list_orders')
    def get(self):
        data = list(mongo.db.orders.find())
        for item in data:
            item["_id"] = str(item["_id"])
            if "timestamp" in item and isinstance(item["timestamp"], datetime):
                item["timestamp"] = item["timestamp"].isoformat()
            if "updated" in item and isinstance(item["updated"], datetime):
                item["updated"] = item["updated"].isoformat()
        return jsonify(data)

    @order_ns.doc('create_order')
    @order_ns.expect(order_model)
    def post(self):
        args = api.payload
        required_fields = ['customer_id', 'products', 'total_amount', 'status', 'timestamp', 'updated', 'confirmed', 'tracking_numbers']
        for field in required_fields:
            if field not in args:
                api.abort(400, f"Missing required field: {field}")
        args['order_id'] = str(uuid.uuid4())
        try:
            timestamp = datetime.fromisoformat(args['timestamp'])
            updated = datetime.fromisoformat(args['updated'])
        except (ValueError, TypeError):
            api.abort(400, "Invalid timestamp or updated format. Use ISO 8601.")

        document = {
            "order_id": args["order_id"],
            "customer_id": args["customer_id"],
            "products": args["products"],
            "total_amount": float(args["total_amount"]),
            "status": args["status"],
            "timestamp": timestamp,
            "updated": updated,
            "confirmed": args["confirmed"],
            "tracking_numbers": args["tracking_numbers"]
        }
        result = mongo.db.orders.insert_one(document)
        document["_id"] = str(result.inserted_id)
        document["timestamp"] = timestamp.isoformat()
        document["updated"] = updated.isoformat()
        return document, 201

@order_ns.route('/by_customer/<customer_id>')
@order_ns.doc(params={'customer_id': 'The customer ID'})
class OrderByCustomer(Resource):
    @order_ns.doc('lookup_orders_by_customer')
    def get(self, customer_id):
        data = list(mongo.db.orders.find({"customer_id": customer_id}))
        for item in data:
            item["_id"] = str(item["_id"])
            if "timestamp" in item and isinstance(item["timestamp"], datetime):
                item["timestamp"] = item["timestamp"].isoformat()
            if "updated" in item and isinstance(item["updated"], datetime):
                item["updated"] = item["updated"].isoformat()
        return jsonify(data)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5003, debug=True)