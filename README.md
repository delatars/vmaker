# vmaker

The program is intended for automatic updating of virtual machines, their uploading into Vagrant catalog and Openstack.

### Installation

Install from GitLab

    pip install git+https://github.com/delatars/vmaker
    
### Usage

```bash
$ vmaker -h
usage: vmaker [-h] [-c <path>] [-g] [--generate-from-path <path>]
              [--check-plugin <plugin_name>]
 
optional arguments:
  -h, --help                    show this help message and exit
  -c <path>                     specify configuration file
  -g                            generate default configuration file
  --generate-from-path <path>   generate configuration file with Virtual
                                machines objects, based on names of specified
                                directory.
  --check-plugin <plugin_name>  check target plugin

```
