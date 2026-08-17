from flask import Flask, jsonify
from flask_cors import CORS

from auth import auth_bp
from accounts import accounts_bp
from admin import admin_bp
from loans import loans_bp


def create_app():
    app = Flask(__name__)
    CORS(app)  # In production, restrict origins to the Node frontend's URL

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(accounts_bp, url_prefix="/api")
    app.register_blueprint(admin_bp, url_prefix="/api")
    app.register_blueprint(loans_bp, url_prefix="/api")

    @app.route("/api/health")
    def health():
        return jsonify({"status": "ok", "bank": "Arnob Special Bank"})

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"error": "Internal server error"}), 500

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)
