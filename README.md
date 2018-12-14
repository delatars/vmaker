# vmaker

### Description
The program is intended to automate routine work on VirtualBox VirtualMachines.

VirtualMachines must be placed on the same host where vmaker installed.

Vmaker supports such a thing as "Keyword" (action), which can be performed on a virtual machine. Actions can be combined, and build from them a variety of sequences of actions.

### List of current available keywords
|         keyword        | description  | supported VM OSes |
|          :--          |     :--     |       :--:        |
| create_base_snapshot   | Create a snapshot of the virtual machine with the name "base" | All |
| execute_command        | Run a command in a virtual machine | Unix/Windows |
| execute_script         | Run script in virtual machine | Unix/Windows |
| install_vbox_additions | Install guest OS add-ons in unix virtual machine | Unix |
| openstack_cache_image  | Creates a virtual machine cache in an openstack cluster | All |
| openstack_export       | Export Virtual Machine to Openstack Cluster | All |
| port_forwarding        | Port forwarding to a virtual machine | All |
| restore_base_snapshot  | Restore the state of the virtual machine from snapshot under the name "base" | All |
| update_os              | Virtual machine update | Unix |
| vagrant_export         | Uploading a virtual machine to the Vagrant directory | All |
| vbox_start             | Starting a virtual machine | All |
| vbox_stop              | Turn off the virtual machine | All |

### Installation

Install from GitLab

    pip install git+https://github.com/delatars/vmaker
    
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
