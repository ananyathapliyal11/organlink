from flask import Flask
from module_b.recipients import recipients_bp
from module_b.requests import requests_bp

app = Flask(__name__)

# Required for Flask flash messages and sessions
app.secret_key = "organlink-local-dev-key-change-before-deployment"

app.register_blueprint(recipients_bp)
app.register_blueprint(requests_bp)


@app.route("/")
def home():
    return "OrganLink is running!"


if __name__ == "__main__":
    app.run(debug=True)