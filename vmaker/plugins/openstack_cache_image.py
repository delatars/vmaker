# -*- coding: utf-8 -*-
import os
import sys
from keystoneauth1 import loading, session
from novaclient.client import Client
from ConfigParser import ConfigParser
from vmaker.init.settings import LoadSettings
from vmaker.utils.logger import STREAM
from vmaker.utils.auxilary import exception_interceptor


class Keyword(object):
    """
    This plugin create a hot cache of virtual machine in Openstack cluster.
    Arguments of user configuration file:
    vm_name = name of the virtual machine in Virtual Box (example: vm_name = ubuntu1610-amd64)
    openstack_cluster = <path to configuration file which contains cluster connection settings>::<target_section>
        if path not specified connection settings will be searched in the vmaker.ini
        (example:
            openstack_cluster = /home/user/clusters.ini::openstack_cluster_1
            openstack_cluster = openstack_cluster_1 (target section will be searched in vmaker.ini)
    openstack_image_name = name of the virtual machine in Openstack cluster (example: openstack_image_name = ubuntu1610)
    openstack_flavor =
    openstack_network =
    """
    REQUIRED_CONFIG_ATTRS = ["openstack_cluster", "openstack_image_name", "openstack_flavor", "openstack_network"]

    @exception_interceptor
    def main(self):
        self.openstack_cluster = self.openstack_cluster
        self.openstack_image_name = self.openstack_image_name
        self.openstack_flavor = self.openstack_flavor
        self.openstack_network = self.openstack_network
        # List of available clusters
        self.clusters = {}
        target_cluster = self.openstack_credentials_harvester()
        nova = self.cluster_connect(target_cluster)
        STREAM.info("==> Creating cache for image %s" % self.openstack_image_name)
        # Check for already created instance with current name
        images = self.get_running_instances(nova)
        for image in images:
            if image.name == "vmaker-"+self.openstack_image_name:
                # if instance exists delete it
                STREAM.debug(" -> Detected instance with the same name.")
                self.delete_instance(nova, image)
                STREAM.debug(" -> Deleted instance that already exist.")
        server = self.create_instance(nova)
        # if cycle will not breaked, then plugin will be terminated by vmaker timeout.
        while True:
            if self.get_instance_status(nova, server.id) == "ACTIVE":
                self.delete_instance(nova, server)
                STREAM.success(" -> Image has been cached.")
                break

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
            STREAM.error(" -> There are no connection settings for the Openstack clusters found!\nMake sure"
                         "that parameter(openstack_cluster) specified correctly.")
            STREAM.error(" -> Export in Openstack passed.")
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
        nova = Client('2', session=sess)
        return nova

    def create_instance(self, connection):
        image = connection.glance.find_image(self.openstack_image_name)
        flavor = connection.flavors.find(name=self.openstack_flavor)
        network = connection.neutron.find_network(name=self.openstack_network)
        instance = connection.servers.create(name="vmaker-"+self.openstack_image_name,
                                             image=image.id,
                                             flavor=flavor.id,
                                             nics=[{'net-id': network.id}])
        return instance

    def get_instance_status(self, connection, id):
        instance = connection.servers.find(id=id)
        return instance.status

    def delete_instance(self, connection, server):
        connection.servers.force_delete(server)

    def get_running_instances(self, connection):
        """Method to get images from the openstack cluster"""
        images = connection.servers.list()
        return images


if __name__ == "__main__":
    pass
