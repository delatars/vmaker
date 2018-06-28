# -*- coding: utf-8 -*-
from keystoneauth1 import loading, session
from glanceclient import Client
from ConfigParser import ConfigParser
from vmaker.init.settings import LoadSettings
import os
import sys
from vmaker.utils.logger import STREAM
from vmaker.utils.auxilary import exception_interceptor


class Keyword(object):
    REQUIRED_CONFIG_ATTRS = ["vm_name", "openstack_cluster"]
    VIRTUAL_BOX_DIR = os.path.join(os.path.expanduser("~"), "VirtualBox VMs")

    @exception_interceptor
    def main(self):
        self.openstack_cluster = self.openstack_cluster
        self.openstack_image_properties = self.openstack_image_properties
        self.openstack_image_custom_properties = self.openstack_image_custom_properties
        self.vm_name = self.vm_name
        # List of available clusters
        self.clusters = {}
        target_cluster = self.openstack_credentials_harvester()
        # glance = self.cluster_connect(target_cluster)
        # self.get_images(glance)
        self.upload_image(None)
        # self.delete_image("6737641a-f35d-4fe6-acdf-f2e2569c30cc")

    def openstack_credentials_harvester(self):
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
        for sec in config.sections():
            if "openstack_cluster" in sec:
                args = {key: value.strip() for key, value in config.items(sec)}
                self.clusters[sec] = args
        if self.clusters == {}:
            STREAM.error(" -> There are no connection settings for the Openstack clusters found!")
            STREAM.error(" -> Export passed.")
            sys.exit(0)
        STREAM.info(" -> Found connection settings for %s Openstack clusters" % len(self.clusters))
        STREAM.info(" -> Target Openstack cluster set to: %s" % section)
        target_cluster_name = section
        return target_cluster_name

    def cluster_connect(self, target_cluster):
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
        connection.images.delete(id)

    def find_vm_files(self):
        try:
            vbox_path = getattr(self, "openstack_vbox_catalog")
        except AttributeError:
            if os.path.exists(os.path.join(os.path.expanduser("~"), "VirtualBox VMs")):
                vbox_path = os.path.join(os.path.expanduser("~"), "VirtualBox VMs")
            elif os.path.exists(os.path.join(os.path.expanduser("~"), "virtualbox")):
                vbox_path = os.path.join(os.path.expanduser("~"), "virtualbox")
            else:
                STREAM.error("Virtual box catalog not found!")
                STREAM.warning("You may specify it directly by adding 'openstack_vbox_catalog' attribute"
                               " in your configuration file")
                return None
        vm_path = None
        for paths, dirs, files in os.walk(vbox_path):
            if self.vm_name in dirs:
                vm_path = os.path.join(paths, self.vm_name)
                return vm_path
        if vm_path is None:
            STREAM.error("Vm directory (%s) not found in the Vbox catalog directory(%s)" % (self.vm_name, vbox_path))
            return None


    def upload_image(self, connection):
        args = self.get_image_properties()
        args["name"] = self.vm_name
        STREAM.info("==> Uploading image.")
        STREAM.debug("Image properties: %s" % args)
        # Create image object with specified properties.
        image = connection.images.create(**args)
        # Find where vm files are located
        vm_dir = self.find_vm_files()
        STREAM.debug("Vm directory: %s" % vm_dir)
        if vm_dir is None:
            return
        # Find specified disk format in vm directory.
        disk = None
        for fil in os.listdir(vm_dir):
            if fil.endswith(args["disk_format"]):
                disk = os.path.join(vm_dir, fil)
        if disk is None:
            STREAM.error("%s disk not found in %s" % (args["disk_format"], vm_dir))
            STREAM.error("Export in openstack passed.")
            return
        STREAM.debug("Vm virtual hard drive location: %s" % disk)
        # Uploading image.
        connection.images.upload(image.id, open(disk, 'rb'))
        STREAM.success(" -> Uploading complete.")

    def get_images(self, connection):
        images = connection.images.list()
        for im in images:
            print im


if __name__ == "__main__":
    Keyword().main()
