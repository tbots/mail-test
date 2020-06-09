import requests
import datetime
import time
import os
import smtplib
from email.message import EmailMessage
from requests.exceptions import ConnectionError

# create a class to communicate with RossumAPI
class RossumAPI(object):
    ''''
    Script to check Rossum processing of e-mail attachments sent to an organization inbox.
        1. script performs authentication at Rossum API using get_access_token().
        2. sends an email with a file attachment (FILE_NAME) to an email address of a trial organization (EMAIL)
        3. waits for the document to be processed and checks that processing finished OK (annotation status is “to_review”).

        A Python script uses environment variables:

        • FILE_NAME -- file to send as an attachment
        • EMAIL -- Rossum inbox address
        • API_URL -- e.g. api.elis.rossum.ai
        • ROSSUM_USER -- username of a user in trial organization
        • ROSSUM_PASSWORD -- password of a user in trial organization

        If email was processed correctly, file was loaded and shown in API -> return 0
        If email was not processed correctly or file was not found in API or server cannot be reached -> return 1
    '''
    access_token = None
    all_files = []
    # ------------- START config
#   Created environment variables according to task description:
    ROSSUM_USER = os.environ.get('ROSSUM_USER')
    ROSSUM_PASSWORD = os.environ.get('ROSSUM_PASSWORD')
    FILE_NAME = os.environ.get('FILE_NAME')
    API_URL = os.environ.get('API_URL')
    EMAIL = os.environ.get('EMAIL')

    # My own variables used for authentication at smtp.gmail.com to send an email with attachment
    # Needs to have configured gmail account (gmail smtp is used in import_by_email function) to send email to EMAIL address of trial organization
    SENDER_EMAIL_ADDRESS = os.environ.get('SENDER_EMAIL_ADDRESS')
    SENDER_EMAIL_PASSWORD = os.environ.get('SENDER_EMAIL_PASSWORD')

    # -------------- END config

    def get_login_data(self):
        return {
            'username': self.ROSSUM_USER,
            'password': self.ROSSUM_PASSWORD,
        }

    def get_access_token(self):
        user = self.ROSSUM_USER

        login_api_url = f'https://{self.API_URL}/v1/auth/login'
        login_data = self.get_login_data()

        print('Performing authentication at RossumAPI ... ')
        try:
            r = requests.post(login_api_url, data=login_data)
            # Get HTTP status code of a domain + path + data
            if r.status_code not in range(200, 299):
                raise Exception("Could not authenticate client.")
                return False

            response_from_elis = r.json()
            token = response_from_elis['key']
            self.access_token = token
            print(f"User {user} has been successfully authenticated.")
            return token
        except requests.exceptions.RequestException:
            raise Exception(f'Failed to connect to {login_api_url}') from None


    def import_file_by_email(self):
        SENDER_EMAIL_ADDRESS = self.SENDER_EMAIL_ADDRESS
        SENDER_EMAIL_PASSWORD = self.SENDER_EMAIL_PASSWORD
        EMAIL = self.EMAIL
        FILE_NAME = self.FILE_NAME
        msg = EmailMessage()
        msg['Subject'] = 'Sample invoice file'
        msg['From'] = SENDER_EMAIL_ADDRESS
        msg['To'] = EMAIL

        msg.set_content('Process data from the attached file')

        with open(FILE_NAME, 'rb') as f:
            file_data = f.read()
            file_name = f.name
            msg.add_attachment(file_data, maintype='application', subtype='octet-stream', filename=file_name)
        try:
            print(f"Sending email with an attachment {FILE_NAME} to {EMAIL}")
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                smtp.login(SENDER_EMAIL_ADDRESS, SENDER_EMAIL_PASSWORD)
                smtp.send_message(msg)
                print(f'Message has been succesfully delivered to.')

        except smtplib.SMTPAuthenticationError:
            print('Username and Password not accepted.')

    def list_all_documents(self):
        """ This function retreives all documents from requesting endpoint and writes it to list as class attribute.
        """
        access_token = self.access_token
        all_files = self.all_files
        documents_endpoint = f'https://{self.API_URL}/v1/documents'
        headers = {
            "Authorization": f"token {access_token}"
        }
        try:
            r = requests.get(documents_endpoint, headers=headers)
            if r.status_code in range(200, 299):
                # Pagination count to check if there is more then 1 page otherwise file won't be found
                pagination_count = r.json()['pagination']['total_pages']
                # I have setup 30 seconds because when I tested it less than 30 seconds was not enoght for adding a file and file was not shown in all documents
                print('Retreiving information about all documents in all queues ... ')
                time.sleep(30)
                # script checks count of pages and goes page by page and concatenate results to list
                for page in range(1, pagination_count+1):
                    documents_endpoint = f'https://{self.API_URL}/v1/documents?page={page}'
                    r = requests.get(documents_endpoint, headers=headers)
                    if r.status_code in range(200, 299):
                        all_files += r.json()['results']
                self.all_files = all_files
                return self.all_files

        except requests.exceptions.RequestException:
            raise Exception(f'Failed to connect to {documents_endpoint}') from None

    def check_processing(self):
        """ This function checks for latest uploaded file by arrived_at date and by filename then retreives its relevant information (annotation link)
          If annotation link is empty -> returns The file not found and exits with code 1.
          If annotation link is not empty -> goes to its annotation link and retreives file status by status attribute.
        """
        FILE_NAME = self.FILE_NAME
        access_token = self.access_token
        headers = {
            "Authorization": f"token {access_token}"
        }

        # date is used for comparing and finding the lastest date
        date = '0001-01-01T00:00:00.000Z'
        document_list = self.all_files
        annotation_link = None

        def convertDate(d):
            new_date = datetime.datetime.strptime(d, "%Y-%m-%dT%H:%M:%S.%fZ")
            return (new_date.date(), new_date.time())

        date = convertDate(date)

        print(f'Looking for latest uploaded file ...')
        for i in document_list:
            if i['original_file_name']==FILE_NAME:
                if date < convertDate(i['arrived_at']):
                    date = convertDate(i['arrived_at'])
                    annotation_link = i['annotations']
                    filename = i['original_file_name']
        if annotation_link is None:
            print('The file not found. It seems annotation link is empty.')
            return 2

        print(f'Latest uploaded file {FILE_NAME} and its annotation link: {annotation_link[0]}')
        try:
            r = requests.get(annotation_link[0], headers=headers)

            if r.status_code in range(200, 299):
                annotation_data = r.json()['status']
                if annotation_data == 'to_review' and filename==FILE_NAME:
                    print(f"The {filename} has been succesfully added to queue! OK.")
                    return 0
                elif annotation_data == 'failed_import':
                    print(f"Import failed")
                    return 1
                else:
                    print('It seems the file is still importing ... \nWaiting for 20 seconds and retrieving processing status again ...')
                    time.sleep(20)
                    self.check_processing()
        except requests.exceptions.RequestException:
                raise Exception(f'Failed to connect to {annotation_link[0]}') from None

def main():
    client = RossumAPI()
    client.get_access_token()
    client.import_file_by_email()
    client.list_all_documents()
    client.check_processing()
    if client.check_processing() == 2:
        print('********* CHECK#1: format is not supported *********')
        client.list_all_documents()
        client.check_processing()
        if client.check_processing()==2:
            print('It seems you have sent not supported file format which was not processed.')
            return 1

if __name__ == '__main__':
    main()


