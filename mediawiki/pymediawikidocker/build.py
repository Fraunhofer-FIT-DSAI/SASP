#!/usr/bin/env python3
# encoding: utf-8

import subprocess
import json
import yaml
import shutil
import time
import requests
from pathlib import Path
from mwclient import Site
from rich import print as rprint

# Pretty color functions
def error(text, bold=False):
    if bold:
        rprint(f"[bold red]{text}[/]")
    else:
        rprint(f"[red]{text}[/]")
def success(text, bold=False):
    if bold:
        rprint(f"[bold green]{text}[/]")
    else:
        rprint(f"[green]{text}[/]")
def info(text, bold=False):
    if bold:
        rprint(f"[bold blue]{text}[/]")
    else:
        rprint(f"[blue]{text}[/]")
def warning(text, bold=False):
    if bold:
        rprint(f"[bold yellow]{text}[/]")
    else:
        rprint(f"[yellow]{text}[/]")

info("Starting build...", bold=True)

## Configuration

try:
    build_config = json.loads(Path("config.json").read_text())
except FileNotFoundError:
    error("No config.json file found", bold=True)
    exit(1)

# Required keys
required_keys = ["container_name", "user", "password", "base_port", "host", "prot"]
for key in required_keys:
    if key not in build_config:
        error(f"Required key {key} not found in config.json",bold=True)
        exit(1)
if "docker_path" not in build_config:
    build_config["docker_path"] = Path.home() / ".pymediawikidocker"

logo_path = Path("./resources/sasp_logo_sq_135x135.png")
main_page_path = Path("./resources/default_mainpage.txt")
bot_id = build_config.pop("bot_id", None)
bot_password = build_config.pop("bot_password", None)
if not bot_id or not bot_password:
    warning(
        "Either bot_id or bot_password not found in config.json. Bot will not be created"
    )


args = []
for key, value in build_config.items():
    if isinstance(value, bool):
        if value:
            args.append(f"--{key}")
    elif isinstance(value, list):
        args.append(f"--{key}")
        for item in value:
            args.append(item)
    else:
        args.append(f"--{key}")
        args.append(str(value))

build_dir = Path(build_config["docker_path"]) / build_config["container_name"]


# $wgRateLimits['edit']['user'] = [ 10000, 1 ];
# $wgRateLimits['edit']['newbie'] = [ 10000, 1 ];
# $wgRateLimits['edit']['ip'] = [ 10000, 1 ];
# $wgRateLimits['move']['user'] = [ 10000, 1 ];
# $wgRateLimits['move']['newbie'] = [ 10000, 1 ];
# $wgRateLimits['move']['ip'] = [ 10000, 1 ];
overwrites = {
    "$wgSitename": "'SASP Wiki'",
    "$wgGroupPermissions['*']['delete']": "true",
    "$wgRateLimits['edit']['user']": "[ 10000, 1 ]",
    "$wgRateLimits['edit']['newbie']": "[ 10000, 1 ]",
    "$wgRateLimits['edit']['ip']": "[ 10000, 1 ]",
    "$wgRateLimits['move']['user']": "[ 10000, 1 ]",
    "$wgRateLimits['move']['newbie']": "[ 10000, 1 ]",
    "$wgRateLimits['move']['ip']": "[ 10000, 1 ]",
    "$wgJobRunRate" : "1000;",
}

## Script begins here

# Assert that no previous build is active
info("Checking for active build...",bold=True)

abort = False
# dockerbuild folder
if build_dir.exists():
    error(f"A build with the same name already exists at {build_dir.resolve()}")
    abort = True

# docker container
try:
    process = subprocess.run(["docker", "ps", "-a", "--format", "json"], check=True, stdout=subprocess.PIPE)
    containers = [json.loads(c) for c in process.stdout.decode().split("\n") if c]
    container_names = [c["Names"] for c in containers]
    if f"{build_config['container_name']}-mw" in container_names:
        error(f"Container {build_config['container_name']}-mw already exists")
        abort = True
    
    if f"{build_config['container_name']}-db" in container_names:
        error(f"Container {build_config['container_name']}-db already exists")
        abort = True
    
    for c in containers:
        if c["State"] == "running":
            # print(c)
            if f"{build_config['base_port']}->80/tcp" in c["Ports"]:
                error(f"Container {c['Names']} is already running on given port {build_config['base_port']}")
                abort = True
            if f"{build_config['sql_base_port']}->3306/tcp" in c["Ports"]:
                error(f"Container {c['Names']} is already running on given sql port {build_config['sql_base_port']}")
                abort = True
except Exception as e:
    error("Error while checking for active build")
    error(f"{e}")

# docker volume
try:
    process = subprocess.run(["docker", "volume", "ls", "--format", "json"], check=True, stdout=subprocess.PIPE)
    volumes = [json.loads(c) for c in process.stdout.decode().split("\n") if c]
    volumes = [c["Name"] for c in volumes]
    if f"{build_config['container_name']}_mysql-data" in volumes:
        error(f"Volume {build_config['container_name']}_mysql-data already exists")
        abort = True
    if f"{build_config['container_name']}_wiki-etc" in volumes:
        error(f"Volume {build_config['container_name']}_mysql-data already exists")
        abort = True
    if f"{build_config['container_name']}_wiki-www" in volumes:
        error(f"Volume {build_config['container_name']}_wiki-www already exists")
        abort = True
except Exception as e:
    error("Error while checking for active build")
    error(f"{e}")

if abort:
    error("Aborting build",bold=True)
    info("Please clean up the existing build and try again",bold=True)
    exit(1)
else:
    info("No active build found. Continuing...",bold=True)

# Setting up the mediawiki cluster
info("Executing: ",bold=True)
info("" + str(["mwcluster", *args, "-d", "--create"]) + "")
try:
    process = subprocess.run(["mwcluster", *args, "-d", "--create"], check=True)
except Exception as e:
    error("Error while setting up the mediawiki cluster",bold=True)
    error(f"{e}",bold=True)
    exit(1)

# Shutting down the cluster
info("Shutting down the cluster",bold=True)
try:
    process = subprocess.run(["docker-compose", "down"], cwd=build_dir, check=True)
except Exception as e:
    error("Error while shutting down the cluster",bold=True)
    error(f"{e}",bold=True)
    exit(1)

# Updating the docker-compose file
info("Updating the docker-compose file",bold=True)
with open(build_dir / "docker-compose.yml", "r") as f:
    compose = yaml.safe_load(f)

info(
    "Setting restart policy to 'unless-stopped' for services 'mw' and 'db'"
)
compose["services"]["mw"]["restart"] = "unless-stopped"
compose["services"]["db"]["restart"] = "unless-stopped"


info(
    "Adding mount './LocalSettings.php:/var/www/html/LocalSettings.php' to docker-compose.yml"
)
compose["services"]["mw"]["volumes"] += [
    "./LocalSettings.php:/var/www/html/LocalSettings.php"
]
if logo_path.exists():
    info(
        "Adding mount './logo.png:/var/www/html/resources/assets/logo.png' to docker-compose.yml"
    )
    shutil.copy(logo_path, build_dir / "logo.png")
    compose["services"]["mw"]["volumes"] += [
        "./logo.png:/var/www/html/resources/assets/logo.png"
    ]
else:
    warning("No logo.png file found")

compose["services"]["mw"]["volumes"] = list(set(compose["services"]["mw"]["volumes"]))
with open(build_dir / "docker-compose.yml", "w") as f:
    yaml.dump(compose, f, default_flow_style=False)

# Updating the LocalSettings.php file
info("Updating the LocalSettings.php file",bold=True)
with open(build_dir / "LocalSettings.php", "r") as f:
    lines = f.readlines()
    for i in range(len(lines)):
        for key, value in overwrites.items():
            if lines[i].startswith(key):
                new_line = f"{key} = {value};\n"
                info(f"{lines[i].strip()} -> {new_line.strip()}")
                lines[i] = new_line
                overwrites.pop(key)
                break
    if not lines[-1].endswith("\n"):
        lines[-1] += "\n"
    for key, value in overwrites.items():
        info(f"Adding {key} = {value}")
        lines.append(f"{key} = {value};\n")
with open(build_dir / "LocalSettings.php", "w") as f:
    f.writelines(lines)

# Starting the cluster
info("Starting the cluster",bold=True)
process = subprocess.run(["docker-compose", "up", "-d"], cwd=build_dir, check=True)

# Connecting to the wiki
info("Connecting to the wiki",bold=True)
for i in range(10):
    try:
        wiki = Site(
            f'{build_config["host"]}:{build_config["base_port"]}',
            scheme=build_config["prot"],
            path="/",
        )
        break
    except requests.exceptions.ConnectionError:
        warning(f"Connection failed {i+1}/10 times. Retrying in 5 seconds")
        time.sleep(5)
    except Exception as e:
        error(f"Error. Could not connect to the wiki. {e}",bold=True)
        raise e
        exit(1)
else:
    error("Error. Could not connect to the wiki after 10 attempts",bold=True)
    exit(1)

# Creating the bot
if bot_id and bot_password:
    info("Creating the bot",bold=True)
    try:
        warning("Following text in white is command output")
        process = subprocess.run(
            [
                "docker-compose",
                "exec",
                "mw",
                "php",
                "maintenance/run.php",
                "createBotPassword",
                f"{build_config['user']}",
                f"{bot_password}",
                f"--appid={bot_id}",
                "--grants",
                "basic,blockusers,createaccount,createeditmovepage,delete,editinterface,editmycssjs,editmyoptions,editmywatchlist,editpage,editprotected,editsiteconfig,highvolume,mergehistory,oversight,patrol,privateinfo,protect,rollback,sendemail,uploadeditmovefile,uploadfile,viewdeleted,viewmywatchlist,viewrestrictedlogs",
            ],
            cwd=build_dir,
            check=True,
        )
        warning(" Disregard the above")
        success(
            f"Successfully created bot. You can reset the password using '{build_config['host']}:{build_config['base_port']}/index.php/Special:BotPasswords'"
        )
    except Exception as e:
        error(f"Error while creating bot. {e}",bold=True)
        exit(1)

try:
    if bot_id and bot_password:
        pw = f"{bot_id}@{bot_password}"
        info(f"Logging in as admin '{build_config['user']}' with password '{build_config['password']}'")
        wiki.login(build_config["user"], build_config['password'])
        success(f"Successfully logged in as admin '{build_config['user']}'")
except Exception as e:
    error(f"Error. Could not login to the wiki. {e}",bold=True)
    exit(1)

# Adjust Main Page
if main_page_path.exists():
    info("Setting new default Main Page",bold=True)
    with open(main_page_path, "r") as f:
        wiki.pages["Main_Page"].edit(f.read(), "Set new default Main Page")
else:
    warning("No default Main Page found")

success("Build completed successfully",bold=True)
