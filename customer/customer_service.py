from flask import Flask, jsonify
from flask_pymongo import PyMongo
from flask_restx import Api, Resource, fields
import os
import uuid
from datetime import datetime

app = Flask(__name__)
app.config['MONGO_URI'] = os.getenv("MONGO_URI")
mongo = PyMongo(app)

api = Api(app, title="Customer Service API", version="1.0", doc="/")

customer_ns = api.namespace('customers', description='Customer operations')

customer_model = api.model('Customer', {
    'name': fields.String(required=True, description='Customer name'),
    'email': fields.String(required=True, description='Customer email'),
    'address': fields.String(required=True, description='Customer address'),
    'updated': fields.String(required=True, description='Last updated timestamp (ISO 8601)'),
    'confirmed': fields.Boolean(required=True, description='Confirmation status'),
    'orders_history': fields.List(fields.String, required=True, description='List of order IDs')
})

@customer_ns.route('/')
class CustomerList(Resource):
    @customer_ns.doc('list_customers')
    def get(self):
        data = list(mongo.db.customers.find())
        for item in data:
            item["_id"] = str(item["_id"])
            if "updated" in item and isinstance(item["updated"], datetime):
                item["updated"] = item["updated"].isoformat()
        return jsonify(data)

    @customer_ns.doc('create_customer')
    @customer_ns.expect(customer_model)
    def post(self):
        args = api.payload
        required_fields = ['name', 'email', 'address', 'updated', 'confirmed', 'orders_history']
        for field in required_fields:
            if field not in args:
                api.abort(400, f"Missing required field: {field}")
        args['customer_id'] = str(uuid.uuid4())
        try:
            updated = datetime.fromisoformat(args['updated'])
        except (ValueError, TypeError):
            api.abort(400, "Invalid updated format. Use ISO 8601.")

        document = {
            "customer_id": args["customer_id"],
            "name": args["name"],
            "email": args["email"],
            "address": args["address"],
            "updated": updated,
            "confirmed": args["confirmed"],
            "orders_history": args["orders_history"]
        }
        result = mongo.db.customers.insert_one(document)
        document["_id"] = str(result.inserted_id)
        document["updated"] = updated.isoformat()
        return document, 201
    
@customer_ns.route('/<customer_id>')
@customer_ns.doc(params={'customer_id': 'The customer ID'})
class Customer(Resource):
    @customer_ns.doc('get_customer')
    def get(self, customer_id):
        """Get a customer by ID"""
        customer = mongo.db.customers.find_one({"customer_id": customer_id})
        if not customer:
            api.abort(404, "Customer not found")
        
        customer["_id"] = str(customer["_id"])
        if "updated" in customer and isinstance(customer["updated"], datetime):
            customer["updated"] = customer["updated"].isoformat()
        
        return customer, 200

    @customer_ns.doc('delete_customer')
    def delete(self, customer_id):
        """Delete a customer by ID"""
        result = mongo.db.customers.delete_one({"customer_id": customer_id})
        if result.deleted_count:
            return {"message": "Customer deleted"}, 200
        api.abort(404, "Customer not found")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)