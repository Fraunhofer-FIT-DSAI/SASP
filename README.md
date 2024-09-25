# SASP

<div id="top"></div>
<!-- PROJECT LOGO -->
<br />
<div align="center">
    <img src="readme-images/sasp-banner.png" alt="Logo" width="400" >
  <h3 align="center">SASP Playbook Management Tool</h3>
</div>

<!-- TABLE OF CONTENTS -->
## <summary>Table of Contents</summary>
  <ol>
    <li><a href="#about-the-project">About The Project</a></li>
    <li><a href="#dependencies">Dependencies</a></li>
    <li><a href="#installation">Installation</a></li>
    <li><a href="#roadmap">Roadmap</a></li>
    <li><a href="#technologies-used">Technologies Used</a></li>
    <li><a href="#citation">Citation</a></li>
  </ol>

<!-- ABOUT THE PROJECT -->
## About The Project
This README document is designed to help the viewer understand the structure of the overall repository. The tool contains files related to the playbook management tool used to input/edit/query the mediawiki with new information. The `readme-images` folder simply contains any image files that are used in the many readme files of the project. 
The playbook management tool is designed to provide a wide variety of functionalities around cyber security playbooks. Such as playbook creation, management, limited automatic execution and easy sharing. However, the open-source version does not contain all the functionalities.

## Dependencies
As a scientific library in the Python ecosystem, we rely on external libraries to offer our features. In the `/third_party` folder, we list all the licenses of our direct dependencies. Please check the `/third_party/licenses.json` file to get a full list of dependencies and the corresponding licenses.

### Basic Technologies
- You need to download and install Semantic Mediawiki (SMW) instance. For that, you need to have [Docker](https://www.docker.com/), and then install the [SMW](https://github.com/WolfgangFahl/pymediawikidocker?tab=readme-ov-file/).
- [Python](https://www.python.org/), v3.10.13 was used for the development. Anything later *should* work fine too. Previous versions may work but are not tested. Python 2 is not supported.
### Python Packages
All the required packages are listed in the `requirements.txt` file. They can be installed using the following command:
```bash
python -m pip install -r requirements.txt
```

## Installation
This section concerns the creation of a Semantic Media Wiki instance which is a prerequisite for SASP. If you are updating from a previous version or connecting to an existing instance, you can skip this section.

**This section is under development. We will provide an automated script to install a dockerized version of SMW.**

You need to download and install SMW instance. For that, you need to have [Docker](https://www.docker.com/), and then install the [SMW](https://github.com/WolfgangFahl/pymediawikidocker?tab=readme-ov-file/).

### Run Program
In order for SASP to work, the mediawiki setup must have been fully completed and the Mediawiki must be active. After the setup procedure is done, make sure the docker containers are running and then proceed with the installation of the tool. The tool is being developed using Python 3.10.13 and Django 4.1 and should be compatible with Python 3.10 and above. The tool is currently being developed on Windows 10, but should be compatible with Linux and MacOS as well.

### Prerequisites and Installation

Make sure all the dependencies listed above are installed. 

### Configuration

The project uses a `config.env` and `keys.env` to store configuration and sensitive information. 
In the `/config/` folder, there is a `config_example.env` and `keys_example.env` file that can be used as a template for the actual `config.env` and `keys.env` files and below is an overview of the environment variables used in the project and installation.

#### Overview of Environment Variables
##### Config.env
| Variable | Description | Default Value | Optional | Notes |
| --- | --- | --- | --- | --- |
| `GRAPHVIZ_PATH` | Path to the Graphviz installation used for BPMN generation | `` | Yes | - |
| `PROTOCOL` | Protocol used to connect to the mediawiki | `http` | No | - |
| `TOOL_HOST` | Hostname of the tool | `localhost` | No | - |
| `WIKI_HOST` | Hostname of the mediawiki (if you access the tool and mediawiki from a different machine, this should be the IP of the machine running the mediawiki, not just localhost) | `localhost` | No | - |
| `PORT` | Port used to connect to the mediawiki | `8081` | No | - |
| `URL_BASE` | Base URL of the mediawiki | `${WIKI_HOST}:${PORT}` | No | - |
| `API_PATH` | Path to the mediawiki api | `/w/` | No | - |
| `USER_PATH` | Path to the mediawiki user pages | `/wiki/` | No | - |
| `URL` | Full URL to the mediawiki | `${PROTOCOL}://${URL_BASE}` | No | - |
| `API` | Full URL to the mediawiki api | `${URL}${API_PATH}` | No | - |
| `USER_URL` | Full URL to the mediawiki user pages | `${URL}${USER_PATH}` | No | - |
| `SYS_USERNAME` | Username of the mediawiki system user | `WikiSysop` | No | - |
| `SYS_PASSSWORD` | Password of the mediawiki system user | `acomplicatedPassword1` | No | Will be moved to `keys.env` in the future |
| `BOT_PASSWORD` | Password of the mediawiki bot user | `a@rkct3k9aqhhc1fhtq5j1vsql8kp5ec94` | No | Will be moved to `keys.env` in the future |
| `MISP_URL` | URL to the MISP instance | `https://localhost` | Yes | Used for sharing playbooks with MISP, not essential for the tool to work if not used |
| `HIVE_URL` | URL to the Hive instance | `http://localhost:9000` | Yes | Used for the automatic execution of playbooks |
| `CORTEX_URL` | URL to the Cortex instance | `http://localhost:9001` | Yes | Used for the automatic execution of playbooks |
| `KEYCLOAK_URL` | URL to the Keycloak for SSO | `http://localhost:8083` | Sometimes | A requirement for the project is to integrate with Keycloak for SSO, but until final details are worked out, this is bypassed |
| `KEYCLOAK_CLIENT_ID` | Client ID for the Keycloak instance | `experiments` | Sometimes | See above |
| `KEYCLOAK_REALM` | Realm for the Keycloak instance | `TestRealm` | Sometimes | See above |
| `KAFKA_CLIENT_ID` | Client ID for the Kafka instance | `python-kafka-client` | No | Used for sharing via Kafka, not yet implemented |
| `KAFKA_BOOTSTRAP_SERVERS` | URL to the Kafka instance | `kafka.cyberseas-io.eu:9092` | No | Used for sharing via Kafka, not yet implemented |
| `KAFKA_SSL_CA_LOCATION` | Path to the Kafka CA certificate | `kafka/certs/ca/ca-cert.pem` | No | Used for sharing via Kafka, not yet implemented |
| `KAFKA_SSL_CERTIFICATE_LOCATION` | Path to the Kafka client certificate | `kafka/certs/sappan/sappan-cert.pem` | No | Used for sharing via Kafka, not yet implemented |
| `KAFKA_SSL_KEY_LOCATION` | Path to the Kafka client key | `kafka/certs/sappan/sappan-key.pem` | No | Used for sharing via Kafka, not yet implemented |
| `KAFKA_CONSUMER_GROUP_ID` | Consumer group ID for the Kafka instance | `python-kafka-consumer` | No | Used for sharing via Kafka, not yet implemented |
| `KAFKA_REGISTRY_PLAIN_SSL_KEY_LOCATION` | Path to the decrypted Kafka client key | `kafka/certs/sappan/sappan-key-plain.pem` | No | Used for sharing via Kafka, not yet implemented |
| `APP_application_id` | An identifier for this application | `FRAUNHOFER-SASP` | No | Used for signing playbooks when shared |

  ##### Keys.env
| Variable | Description | Default Value | Notes |
| --- | --- | --- | --- |
| `MISP_KEY` | API key for the MISP instance | `` | - |
| `HIVE_API_KEY` | API key for the Hive instance | `` | - |
| `CORTEX_API_KEY` | API key for the Cortex instance | `` | - |
| `KAFKA_SSL_KEY_PWD` | Password for the Kafka client key | `` | - |

### Automatic Setup
1.  Install all the prerequisites from the previous chapter
2.  Make sure the mediawiki is running and the connection information is correct in the `config/config.env` file.
3.  Execute the following commands
```sh
python setup.py
```

### Manual Setup
1. Install all the prerequisites from the previous chapter
2. Make sure the mediawiki is running and the connection information is correct in the `config/config.env` file.
4. Execute the following commands
```sh
# Creates the database
python manage.py migrate
# Creates the default user with the configuration information from the `*.env` files
python manage.py make_default_user
# Compiles the forms and pushes them to the wiki
python manage.py update_forms
```

### Updating the Tool
Unless otherwise instructed you only need to update the database and the default user, so use the provided switches in the `setup.py` script to skip the form update and playbook import steps.

### Running the Program
Assuming everything is set up correctly, you can run the program with the following steps:
1. Run SASP from the terminal/powershell while in the project's folder
   ```sh
    python manage.py runserver
    ```  
    You can also specify address and port to run the server on. For example:
    ```sh
    python manage.py runserver 0.0.0.0:8000
    ```
7. Open the browser and navigate to the URL that is printed in the terminal/powershell. By default this is `http://localhost:8000/sasp/`

### Additional Commands
There are a few additional commands that can be used to interact with the tool all are invoked with `python manage.py <command>`. 
- `import_playbook`: Imports a playbook from a json file into the tool
  - `--path`: Path to the json file (Required)
- `make_default_user`: Creates a default user with the configuration information from the `*.env` files or overwrites the existing one
- `createsuperuser`: Django command to create a superuser. With this user you can access the admin interface of the tool at `http://localhost:8000/admin/` and manage the database

<!-- FILES OVERVIEW -->
### Package Overview
The tool code is located in the `sasp` folder.
To give an overview of each file/folder:
- `auth`: Contains methods for SSO using Keycloak
- `localization`: Contains localization files
- `management`: Contains definitions of Django management commands
- `migrations`: Contains Django migrations. Djangos migration system is used to keep the database in sync with the models
- `misp_sharing_tool`: Contains the original and modified versions of the MISP sharing tool that was used as a base for the SASP's MISP sharing functionality
- `models`: Contains the Django models, that represent the database tables
- `sasp_exceptions`: Contains custom exceptions for the tool
- `sharing_kafka`: Contains current efforts to implement sharing via Kafka
- `static`: Contains static files like CSS, JS and images
- `templates`: Contains the HTML templates for the tool
- `templatetags`: Contains custom template tags for use in Django's templating system
- `util`: Contains utility functions
- `views`: Contains the views, that provide the bulk of the interfaces and logic
- `wiki_forms`: Contains the forms that define the playbooks on the wiki
- `admin.py`: Django admin interface configuration
- `apps.py`: Django app configuration
- `bpmn_util.py`: functions related to generating BPMN diagrams
- `db_syncs.py`: functions for syncing the tool database with the mediawiki
- `fake_stix.py`: old file, for use in a STIX demo, not used in the current version
- `file_export_util.py`: functions for exporting playbooks to json
- `file_import_util.py`: functions for importing playbooks from json
- `forms.py`: Django forms, that provide user input for the tool
- `knowledge.py`: Location for information like paths or formats that is available to the entire project
- `logic_management.py`: functions too complex to be in the views
- `MISPInterface.py`: functions for interacting with the MISP instance
- `sanitizer_util.py`: functions for sanitizing playbooks before exporting
- `serializers.py`: Django serializers, that provide a way to convert complex data types to and from native Python data types. Mostly used for the REST API
- `tests.py`: Django tests
- `urls.py`: Django URLs, that map URLs to views
- `utils.py`: utility functions
- `vocabulary_translator.py`: contains a variety of functions and data structures for translating between the tool, the mediawiki and the CACAO standard
- `wiki_forms.py`: functions for interacting with the forms that define the playbooks on the wiki
- `wiki_interface.py`: functions for interacting with the mediawiki

### Frontend
The UI was designed using Django. There are a variety of tutorials online that can help you get started with Django. The [official documentation](https://docs.djangoproject.com/en/5.0/) is also a good resource.


## Roadmap
This section shows a **very** general overview of the tasks that have been completed and other features that have yet to have been implemented.
 - [ ] Clean up repository structure, update documentation
 - [ ] Implement semantic functionality for the tool and remove the mediawiki dependency

### Release Notes

To track the incremental updates, please refer to the [CHANGELOG](./CHANGELOG) file.

## Technologies Used
This section should list all the major technologies that are used to develop the project within the repository.

* [pymediawikidocker](https://github.com/WolfgangFahl/pymediawikidocker)
* [Docker](https://www.docker.com/)
* [PHP](https://www.php.net/)
* [Python](https://python.org/)
* [Django](https://www.djangoproject.com/)
* [Keycloak](https://www.keycloak.org/)
* [Bootstrap](https://getbootstrap.com/)
* [CACAO](https://docs.oasis-open.org/cacao/security-playbooks/v1.1/security-playbooks-v1.1.html)

## Citation
This project has received funding from the European Union’s Horizon 2020 research and innovation programme under grant agreements No 833418 ([SAPPAN](https://sappan-project.eu/)) and No 101020560 ([CyberSEAS](https://cyberseas.eu/)).
To reference our work in your publications, please use the following papers:

**Playbook management tool:** 
Mehdi Akbari Gurabi, Avikarsha Mandal, Jan Popanda, Robert Rapp, and Stefan Decker. "SASP: a Semantic web-based Approach for management of Sharable cybersecurity Playbooks." In Proceedings of the 17th International Conference on Availability, Reliability and Security, pp. 1-8. 2022.
[DOI](https://doi.org/10.1145/3538969.3544478)

**Integration with security tools, automation and reporting effort:**
Mehdi Akbari Gurabi, Lasse Nitz, Andrej Bregar, Jan Popanda, Christian Siemers, Roman Matzutt, and Avikarsha Mandal. "Requirements for Playbook-Assisted Cyber Incident Response, Reporting and Automation." Digital Threats: Research and Practice (2024).
[DOI](https://doi.org/10.1145/3688810)

<p align="center">
  <img src="readme-images/sasp_logo.png" alt="Logo" width="250"/>
</p>

