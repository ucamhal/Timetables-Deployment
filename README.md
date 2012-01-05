# Timetables Deployment

This tool can be used to reduce the legwork and potential for error involved in creating a ready to run deployment of the [Timetables](https://github.com/ieb/timetables) webapp.

It's quite simple. It basically performs these steps:

* Fetches the Timetables code from a git repo at a tagged revision
* Overlays the deployment specific config file over the default one
* Overlays the deployment data files which are not kept in the src repo
* Sets the correct file permissions for the web server to read/write the things it needs

## Example

The path to the directory containing the deployment is returned upon success.

    $ sudo timetablesdeploy.py --www-user www --www-group www --config timetables/config/config.txt --tag 2012-01-05T1038 --data tmp/data/ --source https://h4l@github.com/h4l/timetables.git /tmp/ 
    /tmp/timetables-2012-01-05T1038-20120105T113358

## Usage

You can run `$ timetablesdeploy.py -h` for full usage/help:

    $ timetablesdeploy.py -h
    usage: timetablesdeploy.py [-h] -s PATH -t TAG -c PATH -d PATH [-n NAME] -u
                                NAME -g NAME
                                [DESTINATION]
    
    A tool to automate deployment of the the Mercury project Timetables web app.
    The code is obtained from a specific tag in a git repository, then external
    data and configurations are overlayed. File permissions are set appropriately
    for the web server. The aim is to minimise the potential for human errror when
    assembling a Timetables deployment, allowing greater confidence that a given
    deployment can be repeated.
    
    positional arguments:
      DESTINATION           The directory to deploy into. A single subdirectory
                            will be created containing the deployed files.
                            (default: current directory)
    
    optional arguments:
      -h, --help            show this help message and exit
      -s PATH, --source-repo PATH
                            The path to the git repo to deploy from.
      -t TAG, --tag TAG     The name of a tag in the source git repository to
                            deploy from.
      -c PATH, --config PATH
                            The configuration file to use for this deployment.
                            This will replace
      -d PATH, --data PATH  A data directory to use in the deployment.
      -n NAME, --name NAME  The name of the deployment. This will be used as the
                            prefix to the name of the deployment directory.
      -u NAME, --www-user NAME
                            The user name the web server runs as.
      -g NAME, --www-group NAME
                            The group name the web server runs as.

