from flask import Flask, render_template, request, redirect, url_for, jsonify
import imaplib
import email
from email.header import decode_header
import smtplib
import google.generativeai as genai

app = Flask(__name__)

# Default sender credentials (they'll be updated on login)
SENDER_EMAIL = ''
SENDER_PASSWORD = ''

# Set the API key for Google Generative AI (replace with your actual key)
api_key = "AIzaSyBp2mfs0aCGo7uKNffWamT570G9INwO3IA"
genai.configure(api_key=api_key)

def send_email(recipient_email, subject, message):
    try:
        # Connect to the Gmail SMTP server
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)

        # Create the email message
        email_message = f"Subject: {subject}\n\n{message}"

        # Send the email
        server.sendmail(SENDER_EMAIL, recipient_email, email_message)
        server.quit()
        return {"success": True, "message": "Email sent successfully"}
    except Exception as e:
        return {"success": False, "message": str(e)}

def check_inbox(username, password):
    emails = []
    try:
        # Connect to the Gmail IMAP server
        mail = imaplib.IMAP4_SSL('imap.gmail.com', 993)
        mail.login(username, password)
        mail.select('inbox')

        # Fetch the latest emails (up to 5 emails in this case)
        status, messages = mail.search(None, 'ALL')
        mail_ids = messages[0].split()

        if len(mail_ids) == 0:
            return emails

        # Get up to the 5 most recent emails
        latest_mail_ids = mail_ids[-5:]  # Fetch the last 5 emails
        for mail_id in latest_mail_ids:
            status, data = mail.fetch(mail_id, '(RFC822)')
            raw_email = data[0][1].decode("utf-8")
            msg = email.message_from_string(raw_email)

            # Decode the subject
            subject, encoding = decode_header(msg["Subject"])[0]
            if isinstance(subject, bytes):
                subject = subject.decode(encoding if encoding else "utf-8")

            # Get the 'From' field
            from_ = msg["From"]

            # Extract the email body (this part can be improved for rich content emails)
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    if content_type == "text/plain":
                        body = part.get_payload(decode=True).decode()
                        break
            else:
                body = msg.get_payload(decode=True).decode()

            # Store each email in a dict
            emails.append({
                'from': from_,
                'subject': subject,
                'body': body[:50] + '...',  # Show only the first 50 characters as preview
                'full_body': body
            })

        mail.logout()

    except Exception as e:
        print(f"Error fetching emails: {e}")

    return emails

@app.route('/')
def login():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login_post():
    global SENDER_EMAIL, SENDER_PASSWORD
    SENDER_EMAIL = request.form.get('sender_email')
    SENDER_PASSWORD = request.form.get('sender_password')
    if SENDER_EMAIL and SENDER_PASSWORD:
        return redirect(url_for('index'))
    else:
        return render_template('login.html', error="Please provide both email and password.")

@app.route('/home')
def index():
    # Fetch emails from Gmail inbox
    emails = check_inbox(SENDER_EMAIL, SENDER_PASSWORD)
    return render_template('index2.html', emails=emails)

@app.route('/send')
def send_email_page():
    return render_template('index1.html')

@app.route('/send-email', methods=['POST'])
def send_email_route():
    data = request.form
    recipient_email = data.get('recipient_email')
    subject = data.get('subject')
    message = data.get('message')

    if not (recipient_email and subject and message):
        return jsonify({"success": False, "message": "All fields are required."}), 400

    result = send_email(recipient_email, subject, message)
    return jsonify(result)

@app.route('/generate-response', methods=['POST'])
def generate_response():
    input_message = request.form.get("input_message")
    try:
        # Create a new chat session with history
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config={
                "temperature": 1,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 8192,
            }
        )

        chat_session = model.start_chat(history=[])
        # Send message to AI model
        response = chat_session.send_message(input_message)
        return jsonify(success=True, response=response.text)
    except Exception as e:
        print(f"Error generating response: {e}")
        return jsonify(success=False, response=f"Error generating response: {str(e)}")

if __name__ == '__main__':
    app.run(debug=True)
