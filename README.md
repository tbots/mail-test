## Installation and Setting up Environment Variables

1. Please download the project and setup dependencies for the script:

```
pip install -r requirements.txt
source mail-env/bin/activate
```

2. Please setup environment variables for script execution:

a) to run the script in shell, please setup variables for your os environment

b) to run the script in PyCharm or another IDE, please add support for `.env` files or source environmental variables from os environment

## Usage
    Script to check Rossum processing of e-mail attachments sent to an organization inbox.
        1. script performs authentication at Rossum API using get_access_token().
        2. sends an email with a file attachment (FILE_NAME) to an email address of a trial organization (EMAIL)
        3. waits for the document to be processed and checks that processing finished OK (annotation status is “to_review”).

        A Python script use environment variables:

        • FILE_NAME -- file to send as an attachment
        • EMAIL -- Rossum inbox address
        • API_URL -- e.g. api.elis.rossum.ai
        • ROSSUM_USER -- username of a user in trial organization
        • ROSSUM_PASSWORD -- password of a user in trial organization

        If email was processed correctly -> return 0
        If email was not processed correctly -> return 1


