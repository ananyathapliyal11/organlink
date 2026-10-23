from flask import Blueprint, render_template
from db import get_db_connection

recipients_bp = Blueprint("recipients", __name__)

@recipients_bp.route("/recipients")
def view_recipients():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT * FROM recipient")
    recipients = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template("recipients.html", recipients=recipients)