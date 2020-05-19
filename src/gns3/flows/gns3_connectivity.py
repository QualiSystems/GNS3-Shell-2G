from gns3.rest_client.rest_api_handler import RestJsonClient
from cloudshell.shell.flows.connectivity.basic_flow import AbstractConnectivityFlow


class Gns3Connectivity(AbstractConnectivityFlow):
    def __init__(self, rest_client: RestJsonClient, logger, resource_config):
        super().__init__(logger)
        self._rest_client = rest_client
        self._resource_config = resource_config

    def _add_vlan_flow(self, vlan_range, port_mode, port_name, qnq, c_tag):
        pass

    def _remove_vlan_flow(self, vlan_range, port_name, port_mode):
        pass
