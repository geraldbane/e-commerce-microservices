from flask import Flask, jsonify
from flask_pymongo import PyMongo
from flask_restx import Api, Resource, fields
import os
from datetime import datetime

app = Flask(__name__)
app.config['MONGO_URI'] = os.getenv("MONGO_URI")
mongo = PyMongo(app)

api = Api(app, title="Inventory Service API", version="1.0", doc="/")

inventory_ns = api.namespace('inventory', description='Inventory operations')

# Inventory model
inventory_model = api.model('Inventory', {
    'product_id': fields.String(required=True, description='Product ID'),
    'stock': fields.Integer(required=True, description='Stock quantity'),
    'updated': fields.String(required=True, description='Last updated timestamp (ISO 8601)'),
    'low_stock_alert': fields.Boolean(required=True, description='Low stock alert status'),
    'warehouse_locations': fields.List(fields.String, required=True, description='Warehouse locations')
})

@inventory_ns.route('/')
class InventoryList(Resource):
    @inventory_ns.doc('list_inventory')
    def get(self):
        data = list(mongo.db.inventory.find())
        for item in data:
            item["_id"] = str(item["_id"])
            if "updated" in item and isinstance(item["updated"], datetime):
                item["updated"] = item["updated"].isoformat()
        return jsonify(data)

    @inventory_ns.doc('create_inventory')
    @inventory_ns.expect(inventory_model)
    def post(self):
        args = api.payload
        required_fields = ['product_id', 'stock', 'updated', 'low_stock_alert', 'warehouse_locations']
        for field in required_fields:
            if field not in args:
                api.abort(400, f"Missing required field: {field}")
        try:
            updated = datetime.fromisoformat(args['updated'])
        except (ValueError, TypeError):
            api.abort(400, "Invalid updated format. Use ISO 8601.")

        document = {
            "product_id": args["product_id"],
            "stock": int(args["stock"]),
            "updated": updated,
            "low_stock_alert": args["low_stock_alert"],
            "warehouse_locations": args["warehouse_locations"]
        }
        result = mongo.db.inventory.insert_one(document)
        document["_id"] = str(result.inserted_id)
        document["updated"] = updated.isoformat()
        return document, 201

@inventory_ns.route('/<product_id>')
@inventory_ns.doc(params={'product_id': 'The product ID'})
class InventoryResource(Resource):
    @inventory_ns.doc('get_inventory')
    def get(self, product_id):
        """Get inventory entry by product_id"""
        inventory = mongo.db.inventory.find_one({"product_id": product_id})
        if not inventory:
            api.abort(404, "Inventory not found")

        inventory["_id"] = str(inventory["_id"])
        if "updated" in inventory and isinstance(inventory["updated"], datetime):
            inventory["updated"] = inventory["updated"].isoformat()

        return inventory, 200

    @inventory_ns.doc('delete_inventory')
    def delete(self, product_id):
        """Delete inventory entry by product_id"""
        result = mongo.db.inventory.delete_one({"product_id": product_id})
        if result.deleted_count:
            return {"message": "Inventory deleted"}, 200
        api.abort(404, "Inventory not found")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=True)