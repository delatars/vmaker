# -*- coding: utf-8 -*-
import os
import sys
from keystoneauth1 import loading, session
from novaclient.client import Client
from ConfigParser import ConfigParser
from vmaker.init.settings import LoadSettings
from vmaker.utils.logger import STREAM
from vmaker.utils.auxilary import exception_interceptor
from multiprocessing import Process


class Keyword(object):
    """
    This plugin create a hot cache of VirtualMachine in Openstack cluster.
    Arguments of user configuration file:
    vm_name = name of the VirtualMachine in Virtual Box (example: vm_name = ubuntu1610-amd64)
    openstack_cluster = <path to configuration file which contains cluster connection settings>::<target_section>
        if path not specified connection settings will be searched in the vmaker.ini
        (example:
            openstack_cluster = /home/user/clusters.ini::openstack_cluster_1
            openstack_cluster = openstack_cluster_1 (target section will be searched in vmaker.ini)
    openstack_image_name = name of the VirtualMachine in Openstack cluster (example: openstack_image_name = ubuntu1610)
    openstack_flavor =
    openstack_network =
    """
    REQUIRED_CONFIG_ATTRS = ["openstack_cluster", "openstack_image_name", "openstack_flavor", "openstack_network"]
    THREADS = 4

    @exception_interceptor
    def main(self):
        # - Attributes taken from config
        self.openstack_cluster = self.openstack_cluster
        self.openstack_image_name = self.openstack_image_name
        self.openstack_flavor = self.openstack_flavor
        self.openstack_network = self.openstack_network
        # - Optional attribute taken from config
        try:
            self.openstack_availability_zone = getattr(self, "openstack_availability_zone")
            nodes = self.get_nodes(self.openstack_availability_zone)
        except:
            self.openstack_availability_zone = None
            nodes = None
        # --------------------------------
        # List of available clusters
        self.clusters = {}
        target_cluster = self.openstack_credentials_harvester()
        nova = self.cluster_connect(target_cluster)
        STREAM.info("==> Creating cache for image %s" % self.openstack_image_name)
        # Check for already created instance with current name
        STREAM.debug(" -> Check for running instances with the same name")
        self.check_for_running_instances(nova)
        if self.openstack_availability_zone is None:
            self.cache_image(nova)
        else:
            self.cache_image_multi(nova, nodes)

    def cache_image(self, nova):
        server = self.create_instance(nova)
        STREAM.debug(" -> Created instance: %s" % server)
        # if recursion will not breaked, whatever plugin will be terminated by vmaker timeout.
        while True:
            status = self.get_instance_status(nova, server.id)
            STREAM.debug(" -> Creation status: %s" % status)
            if status == "ACTIVE":
                self.delete_instance(nova, server)
                STREAM.success(" -> Image has been cached.")
                break
            elif status == "ERROR":
                self.delete_instance(nova, server)
                STREAM.warning(" -> Unexpected error while launch instance")
                STREAM.warning(" -> Trying to cache image again.")
                self.cache_image(nova)

    # To do
    def cache_image_multi(self, nova, nodes):
        pass

    def check_for_running_instances(self, nova):
        images = self.get_running_instances(nova)
        STREAM.debug(" -> Running instances: %s" % images)
        for image in images:
            if image.name == "vmaker-"+self.openstack_image_name:
                # if instance exists delete it
                STREAM.debug(" -> Detected instance with the same name.")
                self.delete_instance(nova, image)
                STREAM.debug(" -> Deleted instance that already exist.")

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

    def create_instance(self, connection, node=None):
        image = connection.glance.find_image(self.openstack_image_name)
        flavor = connection.flavors.find(name=self.openstack_flavor)
        network = connection.neutron.find_network(name=self.openstack_network)
        instance = connection.servers.create(name="vmaker-"+self.openstack_image_name,
                                             image=image.id,
                                             flavor=flavor.id,
                                             nics=[{'net-id': network.id}],
                                             availability_zone=node)
        return instance

    def delete_instance(self, connection, server):
        try:
            connection.servers.delete(server)
        except:
            connection.servers.force_delete(server)

    def get_instance_status(self, connection, id):
        instance = connection.servers.find(id=id)
        return instance.status

    def get_nodes(self, zone):
        return [node.strip() for node in zone.split(",")]

    def get_running_instances(self, connection):
        """Method to get images from the openstack cluster"""
        images = connection.servers.list()
        return images

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


if __name__ == "__main__":
    pass
