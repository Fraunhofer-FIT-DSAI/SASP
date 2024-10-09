# This file contains most of the actual code for setup and update. Please refer to setup.py for a
# explanations of the individual steps.

import subprocess
import json
import configparser
from pathlib import Path
from rich import print as rprint

def python_status(python_executable: str):
    try:
        process = subprocess.run([python_executable, "--version"], check=True, capture_output=True)
        pip_packages = subprocess.run([python_executable, "-m", "pip", "list"], check=True, capture_output=True)
        rprint(f"[green]Python {process.stdout.decode()} found.[/]")
        rprint(f"[green]Installed packages:[/]\n{pip_packages.stdout.decode()}")
    except Exception as e:
        abort_script(f"Python not found: {e}")

def check_file_exists(file: Path):
    return file.exists()

def abort_script(message: str):
    rprint(f"[bold red]{message}[/]")
    rprint("[red]Aborting script.[/]")
    exit(1)

def warning(message: str):
    rprint(f"[yellow]{message}[/]")

def check_config(config_path: Path):
    try:
        config_data = configparser.ConfigParser()
        config_data.read(config_path)
    except Exception as e:
        abort_script(f"Error loading config file: {e}")
    
    if not config_data.get('Wiki', 'url', fallback=None):
        abort_script("Wiki url not found in config file.")
    if not config_data.get('Wiki', 'user_path', fallback=None):
        abort_script("User path not found in config file. This is the location of pages on the wiki e.g. '/wiki/' or '/index.php/'.")
    if not config_data.get('Wiki', 'api_path', fallback=None):
        abort_script("API path not found in config file. This is the location of the wiki API e.g. '/api.php/'.")

def manage_setup_database(manage_file: Path, python_executable: str):
    try:
        process = subprocess.run([python_executable, manage_file, "migrate"], check=True)
    except Exception as e:
        abort_script(f"Error setting up database: {e}")

def manage_setup_user(manage_file: Path, python_executable: str):
    try:
        process = subprocess.run([python_executable, manage_file, "make_default_user"], check=True)
    except Exception as e:
        abort_script(f"Error setting up user: {e}")

def update_forms(manage_file: Path, python_executable: str):
    try:
        process = subprocess.run([python_executable, manage_file, "update_forms", "--force"], check=True)
    except Exception as e:
        abort_script(f"Error updating forms: {e}")

def import_playbook(manage_file: Path, python_executable: str, playbook_file: Path):
    try:
        process = subprocess.run([python_executable, manage_file, "import_playbook", '--path', playbook_file], check=True)
    except Exception as e:
        abort_script(f"Error importing playbook: {e}")

def check_container_running(container_name: str):
    try:
        process = subprocess.run(["docker", "inspect", container_name], check=True, capture_output=True)
        assert process.returncode == 0
        assert json.loads(process.stdout.decode())[0]['State']['Running']
    except Exception as e:
        abort_script(f"Container {container_name} not found. Is the container running?")

def run_job_queue(container_name: str):
    try:
        process = subprocess.run(["docker", "exec", container_name, "php", "maintenance/run.php", "runJobs.php"], check=True, capture_output=True)
    except Exception as e:
        abort_script(f"Error running job queue: {e}")