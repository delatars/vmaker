# vmaker

The program is intended for automatic updating of virtual machines, their uploading into Vagrant catalog and Openstack.

### Installation

Install from Githib

    pip install git+https://gitlab.i.drweb.ru/testlab-unix/vmaker.git
    
### Usage

```bash
$ vmaker -h
Usage: vmaker [options]

Options:
  -c <path>  - Specify config file
  -g         - Generate default config

  --gfp <path>                  - Generate configuration file, based on specified path.
  --check-plugin <plugin name>  - Check target plugin.

```
### Wiki
https://wiki.dev.drweb.com:8443/display/testlab/vmaker