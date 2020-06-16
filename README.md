## Installation and Setting up Environment Variables

1. Please download the project and setup dependencies for the script:

```
pip install -r requirements.txt
source mail-env/bin/activate
```

2. Please setup environment variables for script execution in config.ini file.

[settings]

ROSSUM_USER=

ROSSUM_PASSWORD=

SENDER_EMAIL_ADDRESS=

SENDER_EMAIL_PASSWORD=

FILE_NAME=

EMAIL=

API_URL=

## Usage:
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

* If email was processed correctly, file was loaded and shown in API -> return 0
* If email was not processed correctly or file was not found in API -> return 1
