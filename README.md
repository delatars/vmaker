# vmaker

The program is intended for automatic updating of virtual machines, their uploading into Vagrant catalog and Openstack.

### Installation

Install from Githib

    pip install git+https://github.com/delatars/vmaker
    
### Usage

```bash
$ vmaker -h
Usage: vmaker [options]

Options:
  -c <path>  - Specify config file
  -g         - Generate default config

  --gfp <path>  - Generate config, based on specified path

```

#### Base configuration file(.vmaker.ini)

```ini
[General]
; List of enabled plugins, you can create your plugin, put it to the plugins dir and enabling it here.
enabled_plugins = vbox_start, unix_update, vbox_stop, port_forwarding, test, vagrant_export
; Global parameter (in minutes) to the end of which plugin process will be terminated.
;   You can specify your own "kill_timeout" parameter for each action in vm, like <action>_kill_timeout = 10
;   Example: vbox_start_kill_timeout = 5
kill_timeout = 20
; Specify path to output log
log = ~/.vmaker/stdout.log
; Enable/Disable debug prints
debug = false

;[openstack_cluster1]
;auth_url=https://localhost:5000/v3
;username=root
;password=toor
;project_name=project1
;user_domain_id=default
;project_domain_id=default
;ca_cert=/etc/ssl/certs/localhost.pem

```

#### User configuration file(default.ini)

```ini
; You can create vm objects and assign them any actions.
; Specify preffered section name.
[my centos]
; Mandatory keys.
;   Key specifies, which type of object will be generated (vm, group, alias).
type = vm
;   Key specifies plugins which will be performed for this object.
actions = vagrant_export
;   Key specifies to which group this object belongs.
group = linux
; Variable keys
;  If you need to create snapshot executing doing all actions you can specify a special key.
;  Snapshot will be created before executing actions, and deleted after all actions are successed.
;snapshot = true
; User keys.
;   You can specify your keys and use it in your plugin's classobj attributes. ex: self.vm_name
vm_name = centos7-amd64
vagrant_catalog = /vagrant/boxes
vagrant_export_kill_timeout = 15

; You can create groups and combine it with other objects.
;   Groups support attribute inheritance (groups attributes have a lower priority than vm attributes).
;   Specify name of the group.
[linux]
; Mandatory keys.
type = group
; User keys.
openstack_catalog = openstack_cluster1
;actions = Vbox_start, ...
;credentials = root:root

; You can combine some plugins in one action, named alias.
[aliases]
type = aliases
; By default aliases extends to all objects, but you can assign aliases at specific group
;group = linux
reboot = vbox_stop, vbox_start
```