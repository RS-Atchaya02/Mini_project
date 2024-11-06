from flask import Flask, request, jsonify
from twilio.rest import Client
from datetime import datetime, timedelta
import sqlite3
import threading
import time

app = Flask(__name__)

# Twilio credentials
SID = ''
AUTH_TOKEN = ''
TWILIO_NUMBER = ''
client = Client(SID, AUTH_TOKEN)

# SQLite database setup
DATABASE = 'reminders.db'

def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS reminders (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        phone TEXT NOT NULL,
                        occasion TEXT NOT NULL,
                        reminder_time TEXT NOT NULL
                    )''')
    conn.commit()
    conn.close()

# Call this function once at the start
init_db()

# Background thread to send SMS reminders
def send_reminders():
    while True:
        time.sleep(60)  # Check every minute
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M')
        cursor.execute("SELECT id, phone, occasion FROM reminders WHERE reminder_time = ?", (current_time,))
        reminders = cursor.fetchall()

        for reminder in reminders:
            try:
                message = client.messages.create(
                    body=f"Reminder: Don't forget your {reminder[2]}!",
                    from_=TWILIO_NUMBER,
                    to=reminder[1]
                )
                print(f"Sent reminder to {reminder[1]} for {reminder[2]}")
                # Delete the reminder after sending
                cursor.execute("DELETE FROM reminders WHERE id = ?", (reminder[0],))
                conn.commit()
            except Exception as e:
                print(f"Error sending message: {e}")

        conn.close()

# Start the background thread
threading.Thread(target=send_reminders, daemon=True).start()

# Endpoint to set a reminder
@app.route('/set_reminder', methods=['POST'])
def set_reminder():
    data = request.json
    phone = data.get('phone')
    occasion = data.get('occasion')
    reminder_time = data.get('reminder_time')  # Format: 'YYYY-MM-DD HH:MM'

    # Validate input
    try:
        reminder_datetime = datetime.strptime(reminder_time, '%Y-%m-%d %H:%M')
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD HH:MM'}), 400

    # Insert into database
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO reminders (phone, occasion, reminder_time) VALUES (?, ?, ?)",
                   (phone, occasion, reminder_time))
    conn.commit()
    conn.close()

    return jsonify({'message': 'Reminder set successfully!'})

# Endpoint to handle incoming SMS (Twilio forwards SMS here)
@app.route('/receive_sms', methods=['POST'])
def receive_sms():
    from_number = request.form['From']
    body = request.form['Body']

    # Simple response (optional)
    response = f"Thank you! You sent: {body}. We’ll remind you accordingly."
    client.messages.create(body=response, from_=TWILIO_NUMBER, to=from_number)

    # Here you could parse the message content and set a reminder if necessary
    # For example, if the message was "Remind me about Meeting at 15:30 on 2024-11-02"
    # you could extract these details and set a reminder.

    return 'Message received'

if __name__ == '__main__':
    app.run(debug=True)
