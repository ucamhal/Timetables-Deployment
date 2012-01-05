#!/usr/bin/env python
# Copyright (c) 2011, CARET, University of Cambridge <hwtb2@caret.cam.ac.uk>
# 
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
# 
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

# Non standard dependancies:
# - argparse: either use Python >= 2.7 or easy_install argparse
# - git: GitPython: http://gitorious.org/git-python   easy_install gitpython

"""
A tool to automate deployment of the the Mercury project Timetables web app. 
The code is obtained from a specific tag in a git repository, then external
data and configurations are overlayed. File permissions are set appropriately 
for the web server.

The aim is to minimise the potential for human errror when assembling a 
Timetables deployment, allowing greater confidence that a given deployment can 
be repeated.
"""

import argparse, collections, git, tempfile, os, shutil, sys, pwd, grp, sys, re
from os.path import join
from datetime import datetime

def create_temp_directory():
    return tempfile.mkdtemp()

def init_directory_from_git_repository(dir_path, repo_path, tag):
    repo = git.Repo.clone_from(repo_path, dir_path)
    if not tag in repo.tags:
        raise Exception("No such tag: {0}".format(tag))
    repo.git.checkout("tags/{0}".format(tag))

# Stages the deployment into a temporary directory. The source repository @ the
# specified revision/tag is cloned and the config and data are overlayed. The
# path to the directory is returned on success.
def stage_deployment(config):
    dir_path = create_temp_directory()
    try:
        populate_directory(dir_path, config)
    except:
        cleanup(dir_path)
        raise
    return dir_path

def populate_directory(dir_path, config):
    init_directory_from_git_repository(dir_path, config.source_repo_path, 
                                       config.source_tag)
    overlay_config(dir_path, config.config_path)
    overlay_data(dir_path, config.data_path)
    setup_permissions(dir_path, config.www_user, config.www_group)
    create_deployment_file(dir_path, config)

def overlay_data(dir_path, data_path):
    dest_dir = join(dir_path, DATA_PATH)
    shutil.copytree(data_path, dest_dir)

def overlay_config(dir_path, config_path):
    dest_path = join(dir_path, CONFIG_PATH)
    shutil.copyfile(config_path, dest_path)

def recursive_take_ownership(dir_path, user, group):
    def take_ownership(path, isdir=False):
        os.chown(path, user, group)
        os.chmod(path, 0770 if isdir else 0660)
    
    for path, dirs, files in os.walk(dir_path):
        take_ownership(path, isdir=True)
        for file in files: take_ownership(join(path, file))

def setup_permissions(dir_path, www_user, www_group):
    recursive_take_ownership(join(dir_path, SECRET_PATH), www_user, www_group)
    recursive_take_ownership(join(dir_path, DATA_PATH), www_user, www_group)
    os.chown(dir_path, -1, www_group)
    os.chmod(dir_path, 0750)

def timestamp():
    return datetime.now().strftime(ISO_8601_DT_BASIC)

def create_deployment_file(dir_path, config):
    with open(join(dir_path, DEPLOYMENT_FILE), "w") as f:
        f.write(DEPLOYMENT_FILE_TEMPLATE.format(config.source_repo_path,
                                                config.source_tag,
                                                config.timestamp))
        os.fchmod(f.fileno(), 0444)

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

def default_user_id():
    return os.getuid()

def default_group_id():
    return pwd.getpwuid(default_user_id()).pw_gid

def is_int(string):
    return bool(re.match("^\d+$", string))

# Gets the group ID of a group name
def get_group_id(group_name):
    if is_int(group_name):
        return int(group_name)
    return grp.getgrnam(group_name).gr_gid

# Gets the user ID of a user name
def get_user_id(user_name):
    if is_int(user_name):
        return int(user_name)
    return pwd.getpwnam(user_name).pw_uid

def create_config(cmd_line_args):
    config_args = filter(lambda (k,v): k in DeploymentConfig._fields,
                         vars(cmd_line_args).items())
    config_args.append(("timestamp", timestamp()))
    return DeploymentConfig(**dict(config_args))

def run(args):
    if os.name != "posix":
        print >> sys.stderr, "** I don't appear to be running on a UNIX system. "\
                             "I'm probably not going to work. **"
    args = PARSER.parse_args(args)
    # Convert user and group names to IDs for use with chmod/chown
    args.www_group = get_group_id(args.www_group)
    args.www_user = get_user_id(args.www_user)
    config = create_config(args)
    deployed_location = deploy(config)
    return deployed_location

# Define our command line arguments
PARSER = argparse.ArgumentParser(description=__doc__)
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
PARSER.add_argument("-u", "--www-user", metavar="NAME|UID", dest="www_user",
                    default=str(default_user_id()),
                    help="The user name the web server runs as. "
                    "(default: current user)")
PARSER.add_argument("-g", "--www-group", metavar="NAME|GID", dest="www_group",
                    default=str(default_group_id()),
                    help="The group name the web server runs as."
                    "(default: current user's group)")

# strftime() format string for ISO 8601 datetime basic (no hyphens or colons) 
ISO_8601_DT_BASIC = "%Y%m%dT%H%M%S"

CONFIG_PATH = "config/config.txt"
DATA_PATH = "data/"
SECRET_PATH = "secret/"
DEPLOYMENT_FILE = "DEPLOYMENT"

DEPLOYMENT_FILE_TEMPLATE =\
"""# The contents of this directory were created by timetablesdeploy.py
repository: {0}
tag: {1}
time: {2}
"""

DeploymentConfig = collections.namedtuple("DeploymentConfig", [
        "source_repo_path", "source_tag", "config_path", "data_path", 
        "www_user", "www_group", "destination_path", "deployment_name", 
        "timestamp"])

if __name__ == "__main__":
    print run(sys.argv[1:])