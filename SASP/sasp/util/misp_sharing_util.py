import subprocess
import dotenv
from pathlib import Path

BASE_PATH = Path(__file__).parent.parent

def load_credentials() -> dict:
    """
    Loads the credentials from the .env file

    Returns:
        dict: The credentials
    """
    env_file = dotenv.dotenv_values(BASE_PATH / ".env")
    env_key_file = dotenv.dotenv_values(BASE_PATH / "keys.env")
    try:
        credentials = {
            "misp_url": env_file["MISP_URL"],
            "misp_key": env_key_file["MISP_KEY"],
            "misp_cert": env_file.get("MISP_CERT", None)
        }
    except KeyError:
        raise KeyError("Please set the MISP_URL and MISP_KEY in the .env file")
    
    return credentials

def api_search(keywords:str,misp_url:str,misp_key:str,misp_cert:str=None) -> list:
    """
    Searches for playbooks with the given keywords and returns the playbook IDs and paths

    Args:
        keywords (str): The keywords to search for
        misp_url (str): The URL of the MISP instance
        misp_key (str): The API key of the user
        misp_cert (str, optional): The certificate of the MISP instance. Defaults to None.

    Returns:
        list: A list of tuples containing the ID and path of the playbooks
    """

    # Create the command
    args = [
        "python",   BASE_PATH / "misp-sharing-tool" / "playbook_sharing.py",
        "--search", keywords,
        "--url",    misp_url,
        "--key",    misp_key,
        "-v"
    ]
    if misp_cert:
        args.append("--cert")
        args.append(misp_cert)

    # Run the command
    process = subprocess.run(args, capture_output=True,shell=True,cwd=BASE_PATH/"misp-sharing-tool",timeout=20)
    
    # Parse the output
    output = process.stderr.decode("utf-8").split("\n")
    output += process.stdout.decode("utf-8").split("\n")
    output = [entry for entry in output if "[DEBUG]" in entry]
    output_len = int(output[0].split(" ")[3])

    return_value = []

    for entry in output[1:]:
        id = entry.split(" ")[4]
        path = entry.split(" ")[-1]
        return_value.append((id,path))
    
    # Check if the number of results is correct
    assert output_len==len(return_value), "The number of results is not correct. Something went wrong."

    return return_value

def api_share(filepath:str,misp_url:str,misp_key:str,misp_cert:str=None) -> bool:
    """
    Shares the playbook at filepath with the MISP instance

    Args:
        filepath (str): The local path to the playbook
        misp_url (str): The URL of the MISP instance
        misp_key (str): The API key of the user
        misp_cert (str, optional): The certificate of the MISP instance. Defaults to None.

    Returns:
        bool: Returns true if successful
    """

    # Create the command
    args = [
        "python",   BASE_PATH / "misp-sharing-tool" / "playbook_sharing.py",
        "--playbook", filepath,
        "--url",    misp_url,
        "--key",    misp_key,
        "-v",
        "--sappan",
        "-q"
    ]
    if misp_cert:
        args.append("--cert")
        args.append(misp_cert)

    # Run the command
    try:
        process = subprocess.run(args, capture_output=True,shell=True,cwd=BASE_PATH/"misp-sharing-tool",timeout=20)
    except subprocess.TimeoutExpired:
        return False
    
    # Parse the output
    output = process.stderr.decode("utf-8").split("\n")
    output += process.stdout.decode("utf-8").split("\n")
    for line in output:
        print(line)
    if any("ERROR" in line for line in output):
        return False

    return_value = []

    return True