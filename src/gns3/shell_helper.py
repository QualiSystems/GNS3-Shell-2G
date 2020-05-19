import jsonpickle
from cloudshell.cp.core.models import VmDetailsProperty, VmDetailsNetworkInterface, VmDetailsData


class Link(object):
    SRC_PORT_ID = 0
    DST_PORT_ID = 1

    def __init__(self, link_list):
        self._link_list = link_list

    @property
    def src_node_id(self):
        return self._link_list[self.SRC_PORT_ID].get("node_id")

    @property
    def src_port_number(self):
        return self._link_list[self.SRC_PORT_ID].get("port_number")

    @property
    def src_adapter_number(self):
        return self._link_list[self.SRC_PORT_ID].get("adapter_number")

    @property
    def dst_node_id(self):
        return self._link_list[self.DST_PORT_ID].get("node_id")

    @property
    def dst_port_number(self):
        return self._link_list[self.DST_PORT_ID].get("port_number")

    @property
    def dst_adapter_number(self):
        return self._link_list[self.DST_PORT_ID].get("adapter_number")


class ff(Link):
    def __init__(self, link_list):
        super().__init__(link_list)


def create_vm_details(vm_name, helper, deployment_service_name, instance):
    """ Create the VM Details results used for both Deployment and Refresh VM Details
    :param vm_name:
    :param helper:
    :param deployment_service_name:
    :param instance:
    :return: VmDetailsData
    """

    node_id = instance.get("node_id")
    project_id = instance.get("project_id")
    vm_instance_data = [
        VmDetailsProperty("Node ID", node_id),
        VmDetailsProperty("Node Type", instance.get("node_type")),
        VmDetailsProperty("Storage Name", instance.get("properties", {}).get("hda_disk_image")),
        VmDetailsProperty("Node Ram", "{} MB".format(instance.get("properties", {}).get("ram"))),
    ]

    links = helper.get_connected_project_switches(project_id, instance)
    mgmt_switch = helper.get_management_switch()
    mgmt_switch_id = mgmt_switch.get("node_id")
    vm_network_data = []
    for port in instance.get("ports", []):
        network_id = None
        port_number = port.get("port_number")
        port_adapter = port.get("adapter_number")
        for link in links:
            if link.src_node_id == node_id \
                    and link.src_port_number == port_number \
                    and link.src_adapter_number == port_adapter:
                if link.dst_node_id != mgmt_switch_id:
                    network_id = link.dst_node_id
            elif link.dst_node_id == node_id \
                    and link.dst_port_number == port_number \
                    and link.dst_adapter_number == port_adapter:
                if link.src_node_id != mgmt_switch_id:
                    network_id = link.src_node_id
        if not network_id:
            continue
        vm_nic = VmDetailsNetworkInterface()
        vm_nic.interfaceId = port.get("adapter_number")
        vm_nic.networkId = network_id
        vm_nic.isPrimary = False
        vm_nic.isPredefined = False

        vm_nic.privateIpAddress = ""
        vm_nic.networkData.append(VmDetailsProperty("MAC Address", port.get("mac_address")))
        vm_nic.networkData.append(VmDetailsProperty("VLAN Name", ""))
        vm_network_data.append(vm_nic)
    return VmDetailsData(vm_instance_data, vm_network_data, vm_name)


def set_command_result(result, unpicklable=False):
    """
    Serializes output as JSON and writes it to console output wrapped with special prefix and suffix
    :param result: Result to return
    :param unpicklable: If True adds JSON can be deserialized as real object.
                        When False will be deserialized as dictionary
    """
    # we do not need to serialize an empty response from the vCenter
    if result is None:
        return

    json_result = jsonpickle.encode(result, unpicklable=unpicklable)
    result_for_output = str(json_result)
    return result_for_output
