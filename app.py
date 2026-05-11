from flask import Flask, jsonify


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/")
    def index():
        return jsonify(
            {
                "project": "PSX Real-Time AI-Powered Market Intelligence System",
                "scope": "Week 2 baseline",
                "status": "running",
                "dashboard": "TODO Week 3: real-time UI",
            }
        )

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
