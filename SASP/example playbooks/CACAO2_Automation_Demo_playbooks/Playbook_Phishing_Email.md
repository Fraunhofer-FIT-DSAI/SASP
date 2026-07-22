# Incident Response Playbook: Suspicious Email Investigation
Author: John Doe  
Version: 1.0  
Last Change: 2025-09-01  
Tags: investigation
Activities: investigate content, scan attachments

## Triggering Conditions 
Trigger: E-Mail forwarded to investigation inbox.  

## Summary 
This playbook is intended to be executed when a user forwards a suspicious e-mail to the investigation inbox. The operator is expected to scan the meta data and content of the message for signs of a phishing attempt and investigate any attachments.

## Workflow 
### Step 1: Gathering information 
- Investigate the sender of the mail
    - is it from an internal or external sender?
    - is the sender a known partner of the company? 
- Investigate the sender domain 
    - did the mail pass SPF-checks and DKIM-verification? 
    - is the sender domain on any known spam list? 
- Investigate the content
  - Does not content show typical signs of phishing attempts? (generic text, pressure to act, asking user to log in, ..)
  - Are there any links in the message? 
    - Investigate links for signs of deception (typo-squatting, url-shorteners, redirect-urls, ..)
    - Investigate the link from a sandbox, verify site ownership
- Are there any attachments? 
  - Do the attachments look suspicious (e.g. file.pdf.exe, office documents with macros, compressed archives)
  - Upload the attachments to VirusTotal
  - Investigate file content in a sandbox environment

### Step 2: Decision 
- If the mail does not show clear signs of phishing attempts try to investigate further
    - If SPF or DKIM failed but the mail seems otherwise normal verify the reasons for the failure. Work with the mail team or the abuse team of the sender as necessary
    - If the mail was forwarded to the inbox by a user contact the user to discuss the reason for the report, contextual information can shift the perspective of what is happening
    - If the email is determined to be benign unlock it from quarantine for the user and move to Step 5
- If there are certain signs of a phishing attempt, such as a link to a phishing website or malware in the attachments:
    - treat the mail as malicious and move to Step 3

### Step 3: Remediation
- Remove the mail from the user's inbox
- If the mail was sent by a known bad domain or obviously malicious domain (e.g. typosquatting in domain name) block the sender
- If an attachment was determined to be malicious add the file signature to the block list of the scanner 
- If a linked website was determined to be used for phishing block the domain in the firewall 
Make sure to include a reference to the id of this case for any configuration changes you make in response to this alert.

### Step 4: Recovery/Investigate further potential impact
- If the mail was sent by an internal sender begin further investigation according to the information gathered in Step 1, i.e. investigate if credentials of an internal user were compromised
- If the mail was sent by a known business partner or reputable contact try to contact their abuse contact to inform them of a possible compromised account 
- If a malicious attachment or link was found
    - Determine if the user who reported the mail has already downloaded a file or clicked on a link and take appropriate actions 
    - Create a filter to search for other received emails from the same sender or with the same attachments 
- If this alert seems to be part of a larger-scale phishing campaign escalate this information as appropriate

### Step 5: Documentation 
- Document the results of the investigation
    - document any configuration changes and block-list entries that were created in response to this alert 
- Create follow-up tasks for any ongoing investigation
- If the mail was initially reported by a user inform them of the result of the investigation