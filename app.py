from module_b.recipients import recipients_bp
from flask import Flask

app = Flask(__name__)
app.register_blueprint(recipients_bp)

@app.route("/")
def home():
    return "OrganLink is running!"


if __name__ == "__main__":
    app.run(debug=True)