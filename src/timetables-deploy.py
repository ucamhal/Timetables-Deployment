#!/usr/bin/env python
"""
A script to (semi) automate the deployment of the Mercury project Timetables web
app. The code is obtained from a specific tag in a git repository, then external
data and configurations are overlayed.
"""

import argparse, collections, git, tempfile, os, shutil, sys, datetime, pwd, grp
from os.path import join

def create_temp_directory():
    return tempfile.mkdtemp()

def init_from_git_repository(dir, repo_path, tag):
    repo = git.Repo.clone_from(repo_path, dir)
    if not tag in repo.tags:
        raise Exception("No such tag: {0}".format(tag))
    repo.git.checkout("tags/{0}".format(tag))

# Stages the deployment into a temporary directory. The source repository @ the
# specified revision/tag is cloned and the config and data are overlayed. The
# path to the directory is returned on success.
def stage_deployment(config):
     dir = create_temp_directory()
     try:
         populate_directory(dir, config)
     except:
         cleanup(dir)
         raise
     return dir

def create_if_not_present(path):
    with open(path, "a"):
        pass

def populate_directory(dir, config):
    init_from_git_repository(dir, config.source_repo_path, config.source_tag)
    overlay_config(dir, config.config_path)
    overlay_data(dir, config.data_path)
    # The log file currently has to exist
    create_if_not_present(join(dir, LOG_PATH))
    setup_permissions(dir, config.www_user, config.www_group)
    create_deployment_file(dir, config)

def overlay_data(dir, data_path):
    dest_dir = join(dir, DATA_PATH)
    shutil.copytree(data_path, dest_dir)

def overlay_config(dir, config_path):
    dest_path = join(dir, CONFIG_PATH)
    shutil.copyfile(config_path, dest_path)

def recursive_take_ownership(dir, user, group):
    def take_ownership(path, isdir=False):
        os.chown(path, user, group)
        os.chmod(path, 0770 if isdir else 0660)
    
    for path, dirs, files in os.walk(dir):
        take_ownership(path, isdir=True)
        for file in files: take_ownership(join(path, file))

def setup_permissions(dir, www_user, www_group):
    recursive_take_ownership(join(dir, SECRET_PATH), www_user, www_group)
    recursive_take_ownership(join(dir, DATA_PATH), www_user, www_group)

def timestamp():
    return datetime.datetime.now().strftime(ISO_8601_DT_BASIC)

def create_deployment_file(dir, config):
    with open(join(dir, DEPLOYMENT_FILE), "w") as f:
        f.write(DEPLOYMENT_FILE_TEMPLATE.format(config.source_repo_path,
                                                config.source_tag,
                                                config.timestamp))

def deployment_dir_name(deployment_name, source_tag, timestamp):
    return "{0}-{1}-{2}".format(deployment_name, source_tag, timestamp)

def cleanup(staging_dir):
    shutil.rmtree(staging_dir, ignore_errors=True)

def deploy(config):
    staged_deployment_dir = stage_deployment(config)
    try:
        dest_dir = deployment_dir_name(config.deployment_name, 
                                       config.source_tag, config.timestamp)
        deployment_destination_dir = join(config.destination_path, dest_dir)
        os.rename(staged_deployment_dir, deployment_destination_dir)
    except:
        cleanup(staged_deployment_dir)
        raise
    return deployment_destination_dir

# Define our command line arguments
PARSER = argparse.ArgumentParser()
PARSER.add_argument("destination_path", metavar="DESTINATION", nargs="?", 
                    default=".", 
                    help="The directory to deploy into. A single subdirectory "
                    "will be created containing the deployed files. (default: "
                    "current directory)")
PARSER.add_argument("-s", "--source-repo", metavar="PATH", required=True, 
                    dest="source_repo_path",
                    help="The path to the git repo to deploy from.")
PARSER.add_argument("-t", "--tag", metavar="TAG", required=True, 
                    dest="source_tag",
                    help="The name of a tag in the source git repository to "
                    "deploy from.")
PARSER.add_argument("-c", "--config", metavar="PATH", required=True, 
                    dest="config_path",
                    help="The configuration file to use for this deployment. "
                    "This will replace ")
PARSER.add_argument("-d", "--data", metavar="PATH", required=True, 
                    dest="data_path",
                    help="A data directory to use in the deployment.")
PARSER.add_argument("-n", "--name", metavar="NAME", default="timetables",
                    dest="deployment_name",
                    help="The name of the deployment. This will be used as the "
                    "prefix to the name of the deployment directory.")
PARSER.add_argument("-u", "--www-user", metavar="NAME", dest="www_user", 
                    required=True,
                    help="The user name the web server runs as.")
PARSER.add_argument("-g", "--www-group", metavar="NAME", dest="www_group", 
                    required=True,
                    help="The group name the web server runs as.")

# strftime() format string for ISO 8601 datetime basic (no hyphens or colons) 
ISO_8601_DT_BASIC = "%Y%m%dT%H%M%S"

CONFIG_PATH = "config/config.txt"
DATA_PATH = "data/"
LOG_PATH = DATA_PATH + "log.txt"
SECRET_PATH = "secret/"
DEPLOYMENT_FILE = "DEPLOYMENT"

DEPLOYMENT_FILE_TEMPLATE =\
"""# The contents of this directory were created by timetables-deploy.py
repository: {0}
tag: {1}
time: {2}
"""

DeploymentConfig = collections.namedtuple("DeploymentConfig", [
        "source_repo_path", "source_tag", "config_path", "data_path", 
        "www_user", "www_group", "destination_path", "deployment_name", 
        "timestamp"])

# Gets the group ID of a group name
def get_group_id(group_name):
    return grp.getgrnam(group_name).gr_gid

# Gets the user ID of a user name
def get_user_id(user_name):
    return pwd.getpwnam(user_name).pw_uid

def create_config(cmd_line_args):
    config_args = filter(lambda (k,v): k in DeploymentConfig._fields,
                         vars(cmd_line_args).items())
    config_args.append(("timestamp", timestamp()))
    return DeploymentConfig(**dict(config_args))

if __name__ == "__main__":
    args = PARSER.parse_args()
    # Convert user and group names to IDs for use with chmod/chown
    args.www_group = get_group_id(args.www_group)
    args.www_user = get_user_id(args.www_user)
    config = create_config(args)
    deployed_location = deploy(config)
    print deployed_location