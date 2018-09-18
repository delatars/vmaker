# -*- coding: utf-8 -*-
import os
import sys
from keystoneauth1 import loading, session
from glanceclient import Client
from ConfigParser import ConfigParser
from vmaker.init.settings import LoadSettings
from vmaker.utils.logger import STREAM
from vmaker.utils.auxilary import exception_interceptor


class Keyword(object):
    """
    This plugin allows to export your VirtualMachine, to openstack cluster.
    Arguments of user configuration file:
    vm_name = name of the VirtualMachine in Virtual Box (example: vm_name = ubuntu1610-amd64)
    openstack_cluster = <path to configuration file which contains cluster connection settings>::<target_section>
        if path not specified connection settings will be searched in the vmaker.ini
        (example:
            openstack_cluster = /home/user/clusters.ini::openstack_cluster_1
            openstack_cluster = openstack_cluster_1 (target section will be searched in vmaker.ini)
    openstack_image_name = name of the VirtualMachine in Openstack cluster (example: openstack_image_name = ubuntu1610)
    openstack_image_properties = base openstack image properties
        (example: openstack_image_properties = disk_format:vdi, container_format:bare, ...)
    openstack_image_custom_properties = custom openstack image properties (can contain an empty value)
        (example:
            openstack_image_custom_properties =
            openstack_image_custom_properties = hw_video_model:vga, hw_vif_model:e1000, ...)
    """
    REQUIRED_CONFIG_ATTRS = ["vm_name", "openstack_cluster", "openstack_image_name",
                             "openstack_image_properties", "openstack_image_custom_properties"]

    @exception_interceptor
    def main(self):
        # - Attributes taken from config
        self.vm_name = self.vm_name
        self.openstack_cluster = self.openstack_cluster
        self.openstack_image_name = self.openstack_image_name
        self.openstack_image_properties = self.openstack_image_properties
        self.openstack_image_custom_properties = self.openstack_image_custom_properties
        # --------------------------------
        # List of available clusters
        self.clusters = {}
        target_cluster = self.openstack_credentials_harvester()
        glance = self.cluster_connect(target_cluster)
        self.upload_image(glance)

    def openstack_credentials_harvester(self):
        """Method to get cluster's connection settings from the configuration file"""
        STREAM.info("==> Get Openstack cluster connection settings")
        try:
            configfile, section = self.openstack_cluster.split("::")
            STREAM.debug(" -> Using user configuration file %s" % configfile)
        except ValueError:
            configfile = LoadSettings.GENERAL_CONFIG
            STREAM.debug(" -> Using general configuration file %s" % configfile)
            section = self.openstack_cluster
        config = ConfigParser()
        config.read(configfile)
        args = {key: value.strip() for key, value in config.items(section)}
        self.clusters[section] = args
        if self.clusters == {}:
            STREAM.error(" -> There are no connection settings for the Openstack clusters found!")
            STREAM.error(" -> Export passed.")
            sys.exit(1)
        STREAM.info(" -> Found connection settings for the Openstack cluster")
        STREAM.info(" -> Target Openstack cluster set to: %s" % section)
        target_cluster_name = section
        return target_cluster_name

    def cluster_connect(self, target_cluster):
        """Method to connect to the openstack cluster"""
        cluster = self.clusters[target_cluster]
        os.environ["REQUESTS_CA_BUNDLE"] = cluster["ca_cert"]
        loader = loading.get_plugin_loader('password')
        auth = loader.load_from_options(
            auth_url=cluster["auth_url"],
            username=cluster["username"],
            password=cluster["password"],
            project_name=cluster["project_name"],
            user_domain_id=cluster["user_domain_id"],
            project_domain_id=cluster["project_domain_id"])
        sess = session.Session(auth=auth)
        glance = Client('2', session=sess)
        return glance

    def get_image_properties(self):
        """Method to get image properties from configuration attributes"""
        base_properties = {key: value for key, value in
                           [prop.split(":") for prop in
                            [prop.strip() for prop in self.openstack_image_properties.split(",")]]}
        try:
            custom_properties = {key: value for key, value in
                                 [prop.split(":") for prop in
                                  [prop.strip() for prop in self.openstack_image_custom_properties.split(",")]]}
        except ValueError:
            custom_properties = {}
        args = dict(base_properties, **custom_properties)
        return args

    def delete_image(self, connection, id):
        """Method to delete image from the openstack cluster"""
        connection.images.delete(id)

    def find_vm_files(self):
        """Method to find VirtualMachine files location"""
        try:
            vbox_path = getattr(self, "openstack_vbox_catalog")
        except AttributeError:
            if os.path.exists(os.path.join(os.path.expanduser("~"), "VirtualBox VMs")):
                vbox_path = os.path.join(os.path.expanduser("~"), "VirtualBox VMs")
            elif os.path.exists(os.path.join(os.path.expanduser("~"), "virtualbox")):
                vbox_path = os.path.join(os.path.expanduser("~"), "virtualbox")
            else:
                STREAM.error(" -> Virtual box catalog not found!")
                STREAM.warning(" -> You may specify it directly by adding 'openstack_vbox_catalog' attribute"
                               " in your configuration file")
                return None
        STREAM.debug(" -> VirtualBox directory: %s" % vbox_path)
        vm_path = None
        for paths, dirs, files in os.walk(vbox_path):
            if self.vm_name in dirs:
                vm_path = os.path.join(paths, self.vm_name)
                return vm_path
        if vm_path is None:
            STREAM.error("VirtualMachine directory(%s) not found in the VirtualBox catalog directory tree(%s)!\n"
                         "Make sure that the VirtualMachine name you specify in parameter(vm_name) exists"
                         " in the directory tree (%s)" % (self.vm_name, vbox_path, vbox_path))
            return None

    def upload_image(self, connection):
        """Method to upload image to the openstack cluster"""
        args = self.get_image_properties()
        args["name"] = self.openstack_image_name
        STREAM.info("==> Uploading image...")
        STREAM.debug(" -> Image properties: %s" % args)
        # Find where vm files are located
        vm_dir = self.find_vm_files()
        if vm_dir is None:
            return
        # Find specified disk format in vm directory.
        disk = None
        for fil in os.listdir(vm_dir):
            if fil.endswith(args["disk_format"]):
                disk = os.path.join(vm_dir, fil)
        if disk is None:
            STREAM.error("%s disk not found in %s\nMake sure that you are specify a right disk_format "
                         "in parameter(openstack_image_properties) or the disk exists." % (args["disk_format"], vm_dir))
            STREAM.error("Export in openstack passed.")
            return
        STREAM.debug(" -> VirtualMachine's virtual hard drive location: %s" % disk)
        # Get image id, if image with specified name already exists
        old_image_id = self.image_exists(connection, args["name"])
        # Create image object with specified properties.
        image = connection.images.create(**args)
        # Uploading image.
        connection.images.upload(image.id, open(disk, 'rb'))
        STREAM.success(" -> Uploading complete.")
        if old_image_id is not None:
            STREAM.info(" -> Remove old image.")
            self.delete_image(connection, old_image_id)
            STREAM.debug(" -> Removed image with id: %s" % old_image_id)
            STREAM.success(" -> Removed.")

    def image_exists(self, connection, name):
        """Method to check if image already exists"""
        images = self.get_images(connection)
        for image in images:
            if image["name"] == name:
                exists_image = image["id"]
                return exists_image
        return None

    def get_images(self, connection):
        """Method to get images from the openstack cluster"""
        images = connection.images.list()
        return images


if __name__ == "__main__":
    pass
