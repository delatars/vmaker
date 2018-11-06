# vmaker

The program is intended to automate routine work on virtual machines.

### Wiki
https://wiki.dev.drweb.com:8443/display/testlab/vmaker

### Installation

Install from GitLab

    pip install git+https://gitlab.i.drweb.ru/testlab-unix/vmaker
    
### Usage

```bash
$ vmaker -h
usage: vmaker [-h] [-c <path>] [-g] [--generate-from-path <path>]
              [--check-keyword <keyword_name>]
 
optional arguments:
  -h, --help                    show this help message and exit
  -c <path>                     specify configuration file
  -g                            generate default configuration file
  --generate-from-path <path>   generate configuration file with Virtual
                                machines objects, based on names of specified
                                directory.
  --check-keyword <keyword_name>  check target keyword

```
