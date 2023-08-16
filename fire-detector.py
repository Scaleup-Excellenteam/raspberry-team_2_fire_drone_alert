import sqlite3

import cv2
import numpy as np
import playsound
import threading

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Global variables
Alarm_Status = False
Email_Status = False
Fire_Reported = 0
queued_emails_sent = False  # Initialize the variable

# create database for situation that internet connection lost
# Create or connect to the SQLite database
db_connection = sqlite3.connect('email_queue.db')
db_cursor = db_connection.cursor()

# Create the table if it doesn't exist
db_cursor.execute('''CREATE TABLE IF NOT EXISTS email_queue
                    (coordinates TEXT, maps_link TEXT)''')
db_connection.commit()


def play_alarm_sound():
    while True:
        playsound.playsound('alarm-sound.mp3', True)


# this function will save the messages emails for fire alarm with the date and time
# and when internet connection return it will send the email that couldnt sended when internet lost
def send_queued_emails():
    db_cursor.execute("SELECT coordinates, maps_link FROM email_queue")
    queued_emails = db_cursor.fetchall()
    for email in queued_emails:
        send_mail_function(email[0], email[1])
        # Delete the sent email from the database
        db_cursor.execute("DELETE FROM email_queue WHERE coordinates = ? AND maps_link = ?", email)
        db_connection.commit()

def get_gps_coordinates():
    # i should replace this with my actual GPS code to get the coordinates
    latitude = 12.345678
    longitude = 98.765432
    return "(Latitude: {}, Longitude: {})".format(latitude, longitude)

def get_google_maps_link(latitude, longitude):
    return "https://www.google.com/maps?q={},{}".format(latitude, longitude)


def send_mail_function(coordinates, maps_link ):

    try:
        # Email configuration
        sender_email = os.getenv('EMAIL')
        receiver_email = 'dronefirealert@gmail.com'
        subject = 'DroneFire Alert - Fire Alarm!'
        message = f"Warning: A Fire Accident has been detected.\nCoordinates: {coordinates}\nGoogle Maps: {maps_link}"

        # Create a MIME object
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg['Subject'] = subject
        msg.attach(MIMEText(message, 'plain'))

        # SMTP server settings
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
    except Exception as e: # if the internet connection lost, so save the email for later
        print("Error sending email:", e)
        # Add the email message components to the database for later sending
        db_cursor.execute("INSERT INTO email_queue (coordinates, maps_link) VALUES (?, ?)", (coordinates, maps_link))
        db_connection.commit()


video = cv2.VideoCapture(0)  # 'webcam is 0 or 1 , also can put video path.

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

        if not Email_Status:
            coordinates_with_maps_link = get_gps_coordinates()  # Get the formatted coordinates
            latitude, longitude = 12.345678, 98.765432  # Replace with actual coordinates
            maps_link = get_google_maps_link(latitude, longitude)  # Get the Google Maps link
            threading.Thread(target=send_mail_function, args=(coordinates_with_maps_link, maps_link)).start()
            Email_Status = True

    if Email_Status and not queued_emails_sent:
        send_queued_emails()
        queued_emails_sent = True


    if cv2.waitKey(1) & 0xFF == ord('q'):
        break


db_connection.close()  # Close the database connection
cv2.destroyAllWindows()
video.release()