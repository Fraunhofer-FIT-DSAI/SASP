# Incident Response Playbook: Suspicious Outgoing Connection
Author: John Doe  
Version: 1.0  
Last Change: 2025-09-01  
Tags: mitigation
Activities: investigate connection, isolate host  

## Triggering Conditions 
SIEM Rule: 10010  
Description: Outgoing connection to non-standard port.

## Summary 
This playbook is intended to be executed when an alert for a suspicious outgoing connection from a host is raised. The responder investigates the destination of the connection and blocks it or isolates the host if necessary. 

## Workflow 
### Step 1: Gathering information 
- Extract the target domain, destination port and ip from the SIEM alert 
- Check the IP against the list of known C2 servers in the IPcheck tool 
### Step 2: Response 
If the IP is among the list of known C2 servers immediately block the connection and isolate the host from the network.
Begin executing the Compromised Host Investigation playbook. 

If the IP or target domain is internal contact the owner of the system. Ask them about the reason for the connection and tell them to request an exception if necessary. If the connection has a valid reason this alert can be closed as false positive. 

If the IP or target domain is external but not in the list of known C2 servers block the connection and contact the owner of the system for further investigation.

### Step 3: Documentation 
- Once the investation is finished document the findings. 
- Include the results of the investigation of the target domain, ip and destination port in the case documentation.
- Document any decisions made and add references if an exeception request was created in reponse to the alert.
- Don't forget to close the case with the correct resolution status