from flask import Flask, jsonify
from flask_pymongo import PyMongo
from flask_restx import Api, Resource, fields
import os
import uuid
from datetime import datetime

app = Flask(__name__)
app.config['MONGO_URI'] = os.getenv("MONGO_URI")
mongo = PyMongo(app)

api = Api(app, title="Product Service API", version="1.0", doc="/")

product_ns = api.namespace('products', description='Product operations')

# Product model
product_model = api.model('Product', {
    'name': fields.String(required=True, description='Product name'),
    'description': fields.String(required=True, description='Product description'),
    'price': fields.Float(required=True, description='Product price'),
    'updated': fields.String(required=True, description='Last updated timestamp (ISO 8601)'),
    'expired': fields.Boolean(required=True, description='Product expiration status'),
    'categories': fields.List(fields.String, required=True, description='Product categories')
})

@product_ns.route('/')
class ProductList(Resource):
    @product_ns.doc('list_products')
    def get(self):
        data = list(mongo.db.products.find())
        for item in data:
            item["_id"] = str(item["_id"])
            if "updated" in item and isinstance(item["updated"], datetime):
                item["updated"] = item["updated"].isoformat()
        return jsonify(data)

    @product_ns.doc('create_product')
    @product_ns.expect(product_model)
    def post(self):
        args = api.payload
        required_fields = ['name', 'description', 'price', 'updated', 'expired', 'categories']
        for field in required_fields:
            if field not in args:
                api.abort(400, f"Missing required field: {field}")
        args['product_id'] = str(uuid.uuid4())
        try:
            updated = datetime.fromisoformat(args['updated'])
        except (ValueError, TypeError):
            api.abort(400, "Invalid updated format. Use ISO 8601.")

        document = {
            "product_id": args["product_id"],
            "name": args["name"],
            "description": args["description"],
            "price": float(args["price"]),
            "updated": updated,
            "expired": args["expired"],
            "categories": args["categories"]
        }
        result = mongo.db.products.insert_one(document)
        document["_id"] = str(result.inserted_id)
        document["updated"] = updated.isoformat()
        return document, 201

@product_ns.route('/<product_id>')
@product_ns.doc(params={'product_id': 'The product ID'})
class ProductResource(Resource):
    @product_ns.doc('get_product')
    def get(self, product_id):
        """Get a product by its ID"""
        product = mongo.db.products.find_one({"product_id": product_id})
        if not product:
            api.abort(404, "Product not found")

        product["_id"] = str(product["_id"])
        if "updated" in product and isinstance(product["updated"], datetime):
            product["updated"] = product["updated"].isoformat()

        return product, 200

    @product_ns.doc('delete_product')
    def delete(self, product_id):
        """Delete a product by its ID"""
        result = mongo.db.products.delete_one({"product_id": product_id})
        if result.deleted_count:
            return {"message": "Product deleted"}, 200
        api.abort(404, "Product not found")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)