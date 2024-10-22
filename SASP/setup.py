# This is a script to setup the tool for the first time. It can also be used to update, but
# then it is important to pay attention to the individual steps and read the comments below.

# Please remeber to set up the config.env and keys.env files before running this script.

from setup_methods import (
    Path, rprint, check_file_exists, abort_script, check_config, check_container_running,
    warning, manage_setup_database, manage_setup_user, update_forms, run_job_queue, import_playbook,
    python_status, setup_complete
)
## Configuration User

# Name of container the semantic mediawiki is running in. This is used to run the job queue after the setup
# and to check if the container is running.
# It is not essential and can be set to None, but this might lead to unexpected behavior. You can put your smw instance name here.
smw_cont = "smw41-mw"

# Location of the python executable. If you are using a virtual environment, this should point to the python
# executable in the virtual environment.
python_executable = "python"

# Location of the tools manage.py file. Should be in the same directory as this file.
django_manage = Path(__file__).parent / "manage.py"

config_file = Path(__file__).parent / "config" / "config.ini"
keys_file = Path(__file__).parent / "config" / "keys.ini"

example_playbooks = [
    Path(__file__).parent / "example playbooks" / "Automated Actions Playbook.json",
    Path(__file__).parent / "example playbooks" / "Hello World Demonstration.json"
]

python_status(python_executable=python_executable)

## Validation
rprint("[bold blue]Starting setup...[/]")
rprint("[blue]Step 1: Checking for required files[/]")

if not(check_file_exists(django_manage)):
    abort_script(f"manage.py not found at {django_manage.resolve()}")
if not(check_file_exists(config_file)):
    abort_script(f"config.ini not found at {config_file.resolve()}")
if not(check_file_exists(keys_file)):
    abort_script(f"keys.ini not found at {keys_file.resolve()}")

for example_playbook in example_playbooks:
    if not(check_file_exists(example_playbook)):
        abort_script(f"Example playbook not found at {example_playbook.resolve()}")

check_config(config_file)

if smw_cont:
    check_container_running(smw_cont)
else:
    warning("No container name provided. Job queue will not be run.")

## Setup database
# This runs the Django migration to setup the database. If the database already exists
# and changes have been made to the models, this will update the database.
rprint("[blue]Step 2: Setting up database[/]")
manage_setup_database(django_manage, python_executable)

## Setup user
# This creates the default user for the tool. If one already exists, it will be updated with contents from the
# config file. If the user does not exist, it will be created.
rprint("[blue]Step 2: Setting up user[/]")
manage_setup_user(django_manage, python_executable)

## Update forms
# This step updates the wiki with the form data for our playbooks. This is only necessary on first setup
# or if the form data has changed, so you can use the skip flag below to skip this step.
SKIP_FORM_UPDATE = False
if not SKIP_FORM_UPDATE:
    rprint("[blue]Step 3: Updating forms[/]")
    update_forms(django_manage, python_executable)
else:
    rprint("[yellow]Skipping form update[/]")

## Run wiki job queue
if smw_cont:
    rprint("[blue]Step 4: Running wiki job queue[/]")
    run_job_queue(smw_cont)
else:
    rprint("[yellow]Skipping job queue[/]")

## Import example playbook
# This imports an example playbook to the wiki. This is only necessary on first setup, so you can use the skip flag below
# to skip this step.
SKIP_PLAYBOOK_IMPORT = False
if not SKIP_PLAYBOOK_IMPORT:
    rprint("[blue]Step 5: Importing example playbooks[/]")
    for example_playbook in example_playbooks:
        import_playbook(django_manage, python_executable, example_playbook)
        
setup_complete()
