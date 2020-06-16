import pytz
import requests
import datetime
import time
import smtplib
from datetime import datetime
from email.message import EmailMessage
from configparser import ConfigParser

# Class to communicate with RossumAPI
class RossumAPI(object):
    ''''
    Script to check Rossum processing of e-mail attachments sent to an organization inbox.
        1. script performs authentication at Rossum API using get_access_token().
        2. sends an email with a file attachment (FILE_NAME) to an email address of a trial organization (EMAIL)
        3. waits for the document to be processed and checks that processing finished OK (annotation status is “to_review”).

        A Python script uses environment variables, you can set it in config.ini:
            • FILE_NAME -- file to send as an attachment
            • EMAIL -- Rossum inbox address
            • API_URL -- e.g. api.elis.rossum.ai
            • ROSSUM_USER -- username of a user in trial organization
            • ROSSUM_PASSWORD -- password of a user in trial organization

        If email was processed correctly, file was loaded and shown in API -> return 0
        If email was not processed correctly or file was not found in API -> return 1
    '''

    send_email_time = None
    annotation_link = None
    access_token = None
    all_files = []

    def __init__(self, file='config.ini'):
        '''The method takes a config file as an argument and initialize the object with the environment variables specified in config.ini.'''
        config = ConfigParser()
        config.read(file)

        self.rossum_user = config.get('settings', 'ROSSUM_USER')
        self.rossum_password = config.get('settings', 'ROSSUM_PASSWORD')
        self.email = config.get('settings', 'EMAIL')
        self.api_url = config.get('settings', 'API_URL')
        self.file_name = config.get('settings', 'FILE_NAME')
        # variables are used for authentication at smtp.gmail.com to send an email with attachment
        # needs to have configured gmail account (gmail smtp is used in import_by_email function) to send email to EMAIL address of trial organization
        self.sender_email_address = config.get('settings', 'SENDER_EMAIL_ADDRESS')
        self.sender_email_password = config.get('settings', 'SENDER_EMAIL_PASSWORD')
        print(f'The object has been initialized.\nRossum user is {self.rossum_user}.\nConfigured inbox is {self.email}.\nFilename: {self.file_name}')

        ## I haven't used here try/except, because if something goes wrong in initialization using configparser, confirparser will raise errors, stops execution and exists with code 1, f.e in case NoSectionError

    def get_access_token(self):
        '''The methods performs authentication at RossumAPI using credentials stored in login_data and returns token.'''
        login_data = {
                'username': self.rossum_user,
                'password': self.rossum_password,
            }
        login_api_url = f'https://{self.api_url}/v1/auth/login'
        print('Performing authentication at RossumAPI ... ')
        r = requests.post(login_api_url, data=login_data)
        r.raise_for_status()

        response_from_api = r.json()
        token = response_from_api['key']
        self.access_token = token
        print(f"User {self.rossum_user} has been successfully authenticated.")
        return token

    def import_file_by_email(self):
        ''' The method allows to login at smtp.gmail.com and sends an email.'''
        msg = EmailMessage()
        msg['Subject'] = 'Sample invoice file'
        msg['From'] = self.sender_email_address
        msg['To'] = self.email

        msg.set_content('Process data from the attached file')
        with open(self.file_name, 'rb') as f:
            file_data = f.read()
            file_name = f.name
            msg.add_attachment(file_data, maintype='application', subtype='octet-stream', filename=file_name)
            print(f"Trying to send an email with an attachment {file_name} to {self.email}")

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(self.sender_email_address, self.sender_email_password)
            smtp.send_message(msg)
            ## This time is needed to compare with the latest time in the list to find the specific file which was sent from this time.
            ## according to UTC time as on the server
            send_email_time = datetime.fromisoformat(str(datetime.now(pytz.utc))[:-6])
            self.send_email_time = send_email_time
            print(f'Message has been succesfully sent. Time is {send_email_time}.')
            ## I haven't used here try/except, because if something goes wrong in sending email using smtplib, smtplib will raise errors, stops execution and exists with code 1, f.e in case smtplib.SMTPAuthenticationError

    def find_last_file_status(self):
        '''This method retreives all documents according the filename from requesting endpoint and writes it to list as class attribute.'''
        send_email_time = self.send_email_time
        access_token = self.access_token
        all_files = self.all_files
        documents_endpoint = f'https://{self.api_url}/v1/documents'
        headers = {
            "Authorization": f"token {access_token}"
        }

        r = requests.get(documents_endpoint, headers=headers)
        r.raise_for_status()
        pagination_count = r.json()['pagination']['total_pages']

        date = '0001-01-01T00:00:00.000'
        compare_date = datetime.fromisoformat(date)
        print('Retreiving information about all documents in all queues ... ')
        ## This for loop is needed for updating a list and waiting when the send file will be added and shown in a queue:
        for x in range(10):
            for page in range(1, pagination_count + 1):
                documents_endpoint = f'https://{self.api_url}/v1/documents?page={page}&original_file_name={self.file_name}&ordering=-arrived_at'
                r = requests.get(documents_endpoint, headers=headers)
                all_files += r.json()['results']
                self.all_files = all_files

            # Get latest date in all.files:
            # First I compare all times in the list, then with send_email_time
            for file in all_files:
                if compare_date < datetime.fromisoformat(file['arrived_at'][:-1]):
                    compare_date = datetime.fromisoformat(file['arrived_at'][:-1])
                    annotation_link = file['annotations']
                    file_name = file['original_file_name']
                    # when this condition is true, the variable self.annotation_link will be set to a new value
                    if send_email_time < compare_date:
                        self.annotation_link = annotation_link
                        self.file_name = file_name
        # The condition for files with empty annotation_link -> not supported format f.e xlsx
        if self.annotation_link == None:
            print('File not found')
            return 2

        else:
            print(f'Latest uploaded file {self.file_name} and its annotation link: {self.annotation_link[0]}')
            ## Get status of a file:
            r = requests.get(self.annotation_link[0], headers=headers)
            r.raise_for_status()
            annotation_data = r.json()['status']
            while annotation_data == 'importing':
                print(
                    f'Status is {annotation_data} ...')
                time.sleep(5)
                r = requests.get(annotation_link[0], headers=headers)
                annotation_data = r.json()['status']
            if annotation_data == 'to_review':
                print(f"Status is {annotation_data}.\nThe {self.file_name} has been succesfully added to queue! OK.")
                return 0
            elif annotation_data == 'failed_import':
                print(f"Import failed")
                return 1

def main():
    client = RossumAPI()
    client.get_access_token()
    client.import_file_by_email()
    result_status = client.find_last_file_status()
    if result_status == 2 or result_status == 1:
        exit(1)
    elif result_status == 0:
        exit(0)

if __name__ == '__main__':
    main()