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
        glance = self.cluster_connect(target_cluster)
        self.get_images(glance)
        # self.upload_image(glance)
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
            STREAM.error(" -> There are no settings for the Openstack cluster found!")
            STREAM.error(" -> Export passed.")
            sys.exit(0)
        STREAM.info(" -> Found settings for %s Openstack clusters" % len(self.clusters))
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
        base_properties = [prop.strip() for prop in self.openstack_image_properties.split(",")]
        base_properties = {key.strip(): value.strip() for key, value in base_properties.split(":")}
        custom_properties = [prop.strip() for prop in self.openstack_image_custom_properties.split(",")]
        custom_properties = {key.strip(): value.strip() for key, value in custom_properties.split(":")}
        args = dict(base_properties, **custom_properties)
        return args

    def delete_image(self, connection, id):
        connection.images.delete(id)

    def upload_image(self, connection):
        args = self.get_image_properties()
        args["name"] = self.vm_name
        STREAM.info("==> Uploading image.")
        # disk_format="vdi", container_format="bare", is_public="True", visibility="public"
        image = connection.images.create(**args)
        connection.images.upload(image.id, open(os.path.join(self.VIRTUAL_BOX_DIR, self.vm_name), 'rb'))
        STREAM.success(" -> Uploading complete.")

    def get_images(self, connection):
        images = connection.images.list()
        for im in images:
            print im


if __name__ == "__main__":
    Keyword().main()
