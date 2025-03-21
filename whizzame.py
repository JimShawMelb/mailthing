import json
import os
import pickle
# Gmail API utils
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
# for encoding/decoding messages in base64
from base64 import urlsafe_b64encode
# for dealing with attachement MIME types
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from mimetypes import guess_type as guess_mime_type

# Request all access (permission to read/send/receive emails, manage the inbox, and more)

# Mostly just copypasta from https://thepythoncode.com/article/use-gmail-api-in-python - I was in a hurry :)

SCOPES = ['https://mail.google.com/']
our_email = os.environ["GMAIL_ADDRESS"]


def gmail_authenticate():
    creds = None
    # the file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first time
    if os.path.exists("env/token.pickle"):
        with open("env/token.pickle", "rb") as token:
            creds = pickle.load(token)
    # if there are no (valid) credentials availablle, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('env/creds.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # save the credentials for the next run
        with open("env/token.pickle", "wb") as token:
            pickle.dump(creds, token)
    return build('gmail', 'v1', credentials=creds)


def add_attachment(message, filename):
    content_type, encoding = guess_mime_type(filename)
    if content_type is None or encoding is not None:
        content_type = 'application/octet-stream'
    main_type, sub_type = content_type.split('/', 1)
    if main_type == 'text':
        fp = open(filename, 'rb')
        msg = MIMEText(fp.read().decode(), _subtype=sub_type)
        fp.close()
    elif main_type == 'image':
        fp = open(filename, 'rb')
        msg = MIMEImage(fp.read(), _subtype=sub_type)
        fp.close()
    elif main_type == 'audio':
        fp = open(filename, 'rb')
        msg = MIMEAudio(fp.read(), _subtype=sub_type)
        fp.close()
    else:
        fp = open(filename, 'rb')
        msg = MIMEBase(main_type, sub_type)
        msg.set_payload(fp.read())
        fp.close()
    filename = os.path.basename(filename)
    msg.add_header('Content-Disposition', 'attachment', filename=filename)
    message.attach(msg)


def build_message(destination, obj, body, attachments=[]):
    if not attachments: # no attachments given
        message = MIMEText(body, "html")
        message["bcc"] = our_email
        message['to'] = destination
        # message['from'] = our_email
        message['subject'] = obj
    else:
        message = MIMEMultipart()
        message["bcc"] = our_email
        message['to'] = destination
        # message['from'] = our_email
        message['subject'] = obj
        message.attach(MIMEText(body))
        for filename in attachments:
            add_attachment(message, filename)
    return {'raw': urlsafe_b64encode(message.as_bytes()).decode()}


def send_message(service, destination, obj, body, attachments=[]):
    return service.users().messages().send(
      userId="me",  # Yes, this thing actually wants the word "me" here
      body=build_message(destination, obj, body, attachments)
    ).execute()


# get the Gmail API service
service = gmail_authenticate()
campers_file = "env/addresses.json"
with open(campers_file, "r") as f:
    campers = json.load(f)
cleaned_camper_batches = []

# Clean strings and put into batches of 99
index = 0
batch = []
for camper in campers:
    camper = camper.strip()
    if camper:
        batch.append(camper)
    if len(batch) == 99:
        cleaned_camper_batches.append(batch)
        batch = []
    index += 1

for batch in cleaned_camper_batches:
    campers_string = ";".join(batch)
    send_message(
        service, campers_string,
        "2025-03-03 Test message #1", 
        "<body><p>Hello!</p>\n<p>This message was sent to test email automations.  Please contact Security Automation folks via Teams (or prod email) if receiving such messages is disruptive, happy to remove you.</p><p><i>Thanks for playing!</i></p></body>", []
    )
