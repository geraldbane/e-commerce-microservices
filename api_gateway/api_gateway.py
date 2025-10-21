from flask import Flask, jsonify
from flask_pymongo import PyMongo
from flask_restx import Api, Resource, fields
import os
import requests
import uuid
from datetime import datetime



app = Flask(__name__)
app.config['MONGO_URI'] = os.getenv("MONGO_URI")
mongo = PyMongo(app)

api = Api(app, title="API Gateway", version="1.0", doc="/")

gateway_ns = api.namespace('', description='API Gateway for order creation')



CUSTOMER_SERVICE_URL = os.getenv("CUSTOMER_SERVICE_URL")
PRODUCT_SERVICE_URL = os.getenv("PRODUCT_SERVICE_URL")
INVENTORY_SERVICE_URL = os.getenv("INVENTORY_SERVICE_URL")
ORDER_SERVICE_URL = os.getenv("ORDER_SERVICE_URL")
PAYMENT_SERVICE_URL =os.getenv("PAYMENT_SERVICE_URL")

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

@gateway_ns.route('/create-order')
class OrderCreation(Resource):
    @gateway_ns.expect(order_model)
    @gateway_ns.doc('create_order')
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

        try:
            customer_response = requests.get(f"{CUSTOMER_SERVICE_URL}/customers/{args['customer_id']}")
            if not customer_response.ok or not customer_response.json():
                api.abort(400, "Invalid customer ID")
        except requests.RequestException:
            api.abort(503, "Customer service unavailable")

        total_amount = 0
        for product in args['products']:
            try:
                product_response = requests.get(f"{PRODUCT_SERVICE_URL}/products/{product['product_id']}")
                if not product_response.ok or not product_response.json():
                    api.abort(400, f"Invalid product ID: {product['product_id']}")
                product_data = product_response.json()
                total_amount += product_data.get('price', 0)

                inventory_response = requests.get(f"{INVENTORY_SERVICE_URL}/inventory/{product['product_id']}")
                if not inventory_response.ok or not inventory_response.json() or inventory_response.json().get('stock', 0) <= 0:
                    api.abort(400, f"Product out of stock: {product['product_id']}")
            except requests.RequestException:
                api.abort(503, "Product or inventory service unavailable")

        order_data = {
            "order_id": args["order_id"],
            "customer_id": args["customer_id"],
            "products": args["products"],
            "total_amount": total_amount,
            "status": args["status"],
            "timestamp": timestamp.isoformat(),
            "updated": updated.isoformat(),
            "confirmed": args["confirmed"],
            "tracking_numbers": args["tracking_numbers"]
        }
        try:
            order_response = requests.post(f"{ORDER_SERVICE_URL}/orders", json=order_data)
            if not order_response.ok:
                api.abort(500, "Failed to create order")
        except requests.RequestException:
            api.abort(503, "Order service unavailable")

        return {
            "order_id": args["order_id"],
            "total_amount": total_amount,
            "status": "order created"
        }, 201

@gateway_ns.route('/customers/<customer_id>')
class CustomerLookup(Resource):
    def get(self, customer_id):
        try:
            response = requests.get(f"{CUSTOMER_SERVICE_URL}/customers/{customer_id}")
            return response.json(), response.status_code
        except requests.RequestException:
            api.abort(503, "Customer service unavailable")
@gateway_ns.route('/products/<product_id>')
class ProductLookup(Resource):
    def get(self, product_id):
        try:
            response = requests.get(f"{PRODUCT_SERVICE_URL}/products/{product_id}")
            return response.json(), response.status_code
        except requests.RequestException:
            api.abort(503, "Product service unavailable")
@gateway_ns.route('/inventory/<product_id>')
class InventoryCheck(Resource):
    def get(self, product_id):
        try:
            response = requests.get(f"{INVENTORY_SERVICE_URL}/inventory/{product_id}")
            return response.json(), response.status_code
        except requests.RequestException:
            api.abort(503, "Inventory service unavailable")
            
@gateway_ns.route('/orders/<customer_id>')
class OrderLookup(Resource):
    def get(self, customer_id):
        try:
            response = requests.get(f"{ORDER_SERVICE_URL}/orders/by_customer/{customer_id}")
            return response.json(), response.status_code
        except requests.RequestException:
            api.abort(503, "Order service unavailable")




if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)