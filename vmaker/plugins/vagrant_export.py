# -*- coding: utf-8 -*-
import os
import shutil
import tarfile
from datetime import datetime
from subprocess import Popen, PIPE
from vmaker.utils.logger import STREAM
from vmaker.init.settings import LoadSettings
from vmaker.utils.auxilary import exception_interceptor


class Keyword:
    """
    This plugin allows to export your virtual machine, to vagrant catalog.
    Arguments of user configuration file:
    vm_name = name of the virtual machine in Virtual Box (example: vm_name = ubuntu1610-amd64)
    vagrant_catalog = path to vagrant catalog (example: vagrant_catalog = /var/www/vagrant)
    """
    REQUIRED_CONFIG_ATTRS = ['vm_name', 'vagrant_catalog']

    @exception_interceptor
    def main(self):
        # - Config attributes
        self.vm_name = self.vm_name
        self.vagrant_catalog = self.vagrant_catalog
        # ----------------------------
        if self.vagrant_catalog.endswith("/"):
            self.vagrant_catalog = self.vagrant_catalog[:-1]
        if LoadSettings.VAGRANT_SERVER_URL == "":
            raise Exception("Parameter 'vagrant_server_url' not specified, you must specify it in vmaker.ini")
        if self.vagrant_server_url.endswith("/"):
            self.vagrant_server_url = self.vagrant_server_url[:-1]
        self.vagrant_server_url = LoadSettings.VAGRANT_SERVER_URL.replace("//", "\/")
        self.provider = "virtualbox"
        self.version = datetime.now().strftime("%Y%m%d%H%M")
        self.boxname = "%s_%s_%s.box.prep" % (self.vm_name, self.version, self.provider)
        result = self.export_vm_configuration()
        if result:
            self.create_vagrant_template()
            self.create_box()
            self.create_metadata_file()
            self.renew_vm()
            STREAM.success("==> Exporting into vagrant successfully completed.")

    def _calculate_box_hash(self):
        """Method to calculate vagrant box hashsum"""
        hash = Popen('sha1sum %s' % os.path.join(self.work_dir, self.boxname), shell=True, stdout=PIPE, stderr=PIPE).communicate()
        hash = hash[0].split(" ")[0]
        return hash

    def create_box(self):
        """Method to create vagrant box from exported configuration"""
        STREAM.info("==> Creating box...")
        with tarfile.open(os.path.join(self.work_dir, self.boxname), "w") as tar:
            for fil in os.listdir(self.tmp_dir):
                tar.add(os.path.join(self.tmp_dir, fil), arcname=fil)
        STREAM.debug(" -> Clearing temporary files")
        shutil.rmtree(self.tmp_dir)

    def create_metadata_file(self):
        """Method to create metadata.json file"""
        STREAM.debug("==> Creating metadata.json")
        STREAM.debug(" -> Calculating box checksum...")
        checksum = self._calculate_box_hash()
        STREAM.debug(" -> sha1 checksum: %s" % checksum)
        rel_path = self.vagrant_catalog[self.vagrant_catalog.find("html")+4:]
        rel_path = rel_path.split("/")
        url_rebuild = "\/".join(rel_path)
        url = "\/".join([self.vagrant_server_url, url_rebuild, self.vm_name, self.boxname[:-5]])
        name = os.path.basename(url_rebuild) + "\/" + self.vm_name
        template = """{
    "name": "unix\/%s",
    "versions": [
        {
            "version": "%s",
            "providers": [
                {
                    "name": "%s",
                    "url": "%s",
                    "checksum_type": "sha1",
                    "checksum": "%s"
                }
            ]
        }
    ]
}
        """ % (name, self.version, self.provider, url, checksum)
        with open(os.path.join(self.work_dir, "metadata.json"), "w") as metadata:
            metadata.write(template)

    def create_vagrant_template(self):
        """Method to create Vagrantfile template"""
        STREAM.debug("==> Create Vagrantfile.")
        template = """
Vagrant::Config.run do |config|
  # This Vagrantfile is auto-generated by `vagrant package` to contain
  # the MAC address of the box. Custom configuration should be placed in
  # the actual `Vagrantfile` in this box.
  config.vm.base_mac = "0800274B29D3"
end

# Load include vagrant file if it exists after the auto-generated
# so it can override any of the settings
include_vagrantfile = File.expand_path("../include/_Vagrantfile", __FILE__)
load include_vagrantfile if File.exist?(include_vagrantfile)
"""
        with open(os.path.join(self.tmp_dir, "Vagrantfile"), "w") as vagrant_file:
            vagrant_file.write(template)

    def export_vm_configuration(self):
        """Method to export virtual machine configuration from Virtual Vox"""
        STREAM.info("==> Checking if vm exists...")
        vms = Popen("vboxmanage list vms |awk '{print $1}'", shell=True, stdout=PIPE, stderr=PIPE).communicate()
        vms = vms[0]
        if not self.vm_name in vms:
            STREAM.error(" -> Vm doesn't exist, passed.")
            return False
        STREAM.success(" -> Exists: True")
        STREAM.info("==> Exporting configuration...")
        STREAM.debug(" -> vagrant catalog directory: %s" % self.vagrant_catalog)
        if not os.path.exists(self.vagrant_catalog):
            STREAM.critical(" -> Vagrant catalog (%s) directory does not exist" % self.vagrant_catalog)
            STREAM.warning(" -> Export, passed.")
            return False
        self.work_dir = os.path.join(self.vagrant_catalog, self.vm_name)
        self.tmp_dir = os.path.join(self.vagrant_catalog, self.vm_name, "tmp")
        try:
            os.makedirs(self.tmp_dir)
        except OSError as errno:
            if "Errno 17" in str(errno):
                STREAM.debug("==> Temporary directory detected, cleaning before start...")
                shutil.rmtree(self.tmp_dir)
                os.makedirs(self.tmp_dir)
            else:
                STREAM.error(errno)
                return False
        Popen('VBoxManage export %s --output %s' % (self.vm_name, os.path.join(self.tmp_dir, self.vm_name + ".ovf")),
              shell=True, stdout=PIPE, stderr=PIPE).communicate()
        diskname = ""
        for fil in os.listdir(self.tmp_dir):
            if fil.endswith(".vmdk"):
                diskname = fil
                os.rename(os.path.join(self.tmp_dir, fil), os.path.join(self.tmp_dir, "box-disk.vmdk"))
            elif fil.endswith(".ovf"):
                os.rename(os.path.join(self.tmp_dir, fil), os.path.join(self.tmp_dir, "box.ovf"))
        with open(os.path.join(self.tmp_dir, "box.ovf"), "r") as ovf:
            ovf_file = ovf.read()
        with open(os.path.join(self.tmp_dir, "box.ovf"), "w") as ovf:
            ovf.write(ovf_file.replace(diskname, "box-disk.vmdk"))
        return True

    def renew_vm(self):
        """Method to replace the old box"""
        for fil in os.listdir(self.work_dir):
            if fil.endswith(".box"):
                STREAM.info("==> Renew old box...")
                os.remove(os.path.join(self.work_dir, fil))
        os.rename(os.path.join(self.work_dir, self.boxname), os.path.join(self.work_dir, self.boxname[:-5]))


