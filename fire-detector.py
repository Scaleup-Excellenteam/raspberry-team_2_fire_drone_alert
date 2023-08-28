import datetime
import time
import cv2
import numpy as np
import playsound
import threading
import sqlite3
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
import requests
import asyncio
from telegram import Bot


# Load environment variables from .env file
load_dotenv()

# Global variables
Alarm_Status = False
Email_Status = False
Fire_Reported = 0
queued_emails_sent = False
lock = threading.Lock()  # Lock to synchronize threads




def play_alarm_sound():
    while True:
        playsound.playsound('alarm-sound.mp3', True)


def send_email_thread(coordinates, maps_link, message):
    global queued_emails_sent

    print(message)
    # Email configuration
    sender_email = os.getenv('EMAIL')
    receiver_email = 'dronefirealert@gmail.com'
    subject = 'DroneFire Alert - Fire Alarm!'
    email_message = message.format(coordinates, maps_link)

    try:
        # Create a MIME object
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg['Subject'] = subject
        msg.attach(MIMEText(email_message, 'plain'))

        # SMTP server settingsf
        smtp_server = 'smtp.gmail.com'
        smtp_port = 587  # Use 465 for SSL/TLS

        # Login credentials
        smtp_username = os.getenv('EMAIL')
        smtp_password = os.getenv('PASSWORD')

        # Establish a connection to the SMTP server
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()  # Enable TLS encryption

        # Log in to the SMTP server
        server.login(smtp_username, smtp_password)

        # Send the email
        server.sendmail(sender_email, receiver_email, msg.as_string())

        # Quit the server
        server.quit()

        print("Email sent successfully!")



    except Exception as e:
        print("Error sending email:", e)
        # Add the email message components to the database for later sending
        with lock:
            save_queued_email_to_db(email_message)
            queued_emails_sent = True


def save_queued_email_to_db(message):
    try:
        connection = sqlite3.connect('queued_emails.db')
        cursor = connection.cursor()

        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        explanation = (
            "An occurrence of network error led to a transmission delay,"
            "resulting in an alteration of the original timestamp for the fire incident, which was initially set at {}"
        ).format(current_time)
        timestamped_message = f"{explanation}\n{message}"

        cursor.execute("INSERT INTO queued_emails (message) VALUES (?)", (timestamped_message,))
        connection.commit()

        print("Email saved for later sending.")
    except Exception as e:
        print("Error saving email:", e)
    finally:
        connection.close()

def telegram_notification(message):
    TELEGRAM_SERVER_URL = "https://9f89-82-80-173-170.ngrok-free.app/message"  # Replace with your server URL
    payload = {
        "message": message
    }
    response = requests.post(TELEGRAM_SERVER_URL, json=payload)
    if response.status_code == 200:
        print("Telegram message sent successfully!")
    else:
        print("Error sending Telegram message:", response.status_code, response.text)


def get_gps_coordinates():
    try:
        response = requests.get('https://ipinfo.io')
        data = response.json()
        lat, lon = data['loc'].split(',')
        return float(lat), float(lon)
    except Exception as e:
        print(f"An error occurred while getting location: {e}")
        return None


def get_google_maps_link(latitude, longitude):
    return "https://www.google.com/maps?q={},{}".format(latitude, longitude)


def create_email_db():
    connection = sqlite3.connect('queued_emails.db')
    cursor = connection.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS queued_emails (message TEXT)")
    connection.commit()
    connection.close()


def send_queued_emails():
    print("Checking for queued emails and sending if needed...")
    while True:
        connection = sqlite3.connect('queued_emails.db')
        cursor = connection.cursor()

        cursor.execute("SELECT message FROM queued_emails")
        queued_messages = cursor.fetchall()

        for message_row in queued_messages:
            send_email_thread(None, None, message_row[0])  # Replace None with actual coordinates and maps_link

            # Remove the sent message from the database
            cursor.execute("DELETE FROM queued_emails WHERE message=?", (message_row[0],))
            connection.commit()

        connection.close()

        # Sleep for a certain duration before checking again
        time.sleep(60)  # Adjust the sleep duration as needed

video = cv2.VideoCapture(0)  # 'webcam is 0 or 1 , also can put video path.

# Call the function to create the database and table
create_email_db()

# Create a thread to send queued emails in the background
email_sender_thread = threading.Thread(target=send_queued_emails)
email_sender_thread.start()


while True:
    (grabbed, frame) = video.read()
    if not grabbed:
        break

    frame = cv2.resize(frame, (960, 540))
    blur = cv2.GaussianBlur(frame, (21, 21), 0)
    hsv = cv2.cvtColor(blur, cv2.COLOR_BGR2HSV)
    lower = [0, 120, 120]  # Lower HSV values for reddish colors
    upper = [20, 255, 255]  # Upper HSV values for reddish colors
    lower = np.array(lower, dtype="uint8")
    upper = np.array(upper, dtype="uint8")
    mask = cv2.inRange(hsv, lower, upper)
    output = cv2.bitwise_and(frame, hsv, mask=mask)
    no_red = cv2.countNonZero(mask)

    if int(no_red) > 15000:
        Fire_Reported = Fire_Reported + 1

    cv2.imshow("output", output)

    if Fire_Reported >= 1:
        if not Alarm_Status:
            threading.Thread(target=play_alarm_sound).start()
            Alarm_Status = True

        if not Email_Status and not queued_emails_sent:
            coordinates_with_maps_link = get_gps_coordinates()
            latitude, longitude = get_gps_coordinates()
            maps_link = get_google_maps_link(latitude, longitude)
            maps_link = "https://www.google.com/maps/search/31.78345455410293,35.22100964747501"

            # Define your email message here
            email_message = "Warning: A Fire Accident has been detected.\nCoordinates: {}\nGoogle Maps: {}".format(
                coordinates_with_maps_link, maps_link)

            # Start a thread for sending the email
            email_thread = threading.Thread(target=send_email_thread,
                                            args=(coordinates_with_maps_link, maps_link, email_message))
            email_thread.start()

            Email_Status = True
            queued_emails_sent = True  # Set the flag here

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cv2.destroyAllWindows()
video.release()

