import json

from cloudshell.cp.core.models import DeployAppResult, Attribute, ConnectToSubnetActionResult

from gns3.flows.gns3_helper import Gns3Helper
from gns3.flows.gns3_state_flows import GNS3StateFlow
from gns3.instance_details import TemplateInstanceDetails
from gns3.helpers.shell_helper import create_vm_details
from gns3.rest_client.rest_api_handler import RestJsonClient


class GNS3Deployment(object):
    def __init__(self, rest_client: RestJsonClient, logger, resource_config):
        self._rest_client = rest_client
        self._logger = logger
        self._resource_config = resource_config
        self._helper = Gns3Helper(rest_client=self._rest_client, logger=logger, resource_config=resource_config)

    def deploy(self, deploy_action, cancellation_context, vm_instance_details, subnet_actions):
        attributes = []
        network_results = []
        self._logger.info("Starting Deployment from Image")

        project_id = self._helper.get_project_id()
        attributes.append(Attribute("User", vm_instance_details.user))
        #ToDo decrypt password!
        attributes.append(Attribute("Password", vm_instance_details.password))

        if isinstance(vm_instance_details, TemplateInstanceDetails):
            template_id = self._helper.get_template_id_by_name(vm_instance_details.template_name)
            interfaces_count = None
            if vm_instance_details.should_shrink_interfaces:
                interfaces_count = len(subnet_actions) + 1
            result = self._helper.create_node_from_template(project_id=project_id,
                                                            name=vm_instance_details.app_name,
                                                            template_id=template_id,
                                                            interfaces_count=interfaces_count,
                                                            data=vm_instance_details.additional_config)
            # result = self._helper.create_from_template(project_id=project_id,
            #                                            name=vm_instance_details.app_name,
            #                                            template_id=template_id,
            #                                            data={"properties": {"adapters": len(subnet_actions) + 1}})
        else:
            result = self.deploy_node(project_id=project_id,
                                      vm_instance_details=vm_instance_details)
        node_id = result.get("node_id")
        app_name = "{}-{}".format(vm_instance_details.app_name, node_id.split("-")[-1])
        node = self._helper.update_vm_name(new_name=app_name, node_id=node_id, project_id=project_id)
        node_id = node.get("node_id")
        ports = node.get("ports", [])
        try:
            if vm_instance_details.should_connect_mgmt:
                switch_port = ports[0]
                port = switch_port.get("port_number")
                adapter = switch_port.get("adapter_number")
                self._helper.connect_management_switch(project_id, node_id=node_id, node_port=port, node_adapter=adapter)
                ports.remove(switch_port)

            for subnet in subnet_actions:

                for port in ports:
                    name = port.get("name")
                    short_name = port.get("short_name")
                    index = ports.index(port)
                    if vm_instance_details.should_connect_mgmt:
                        index = ports.index(port) + 1
                    v_name = subnet.actionParams.vnicName
                    if v_name and v_name != name and v_name != short_name and v_name != str(index):
                        continue

                    switch = self._helper.get_switch(project_id, subnet.actionParams.subnetId)
                    node_port = port.get("port_number")
                    node_adapter = port.get("adapter_number")
                    self._helper.connect_nodes(project_id=project_id,
                                               project_switch=switch,
                                               node_port=node_port,
                                               node_adapter=node_adapter,
                                               node_id=node_id)

                    interface_json = json.dumps({
                        'Interface ID': name,
                        'MAC Address': "",
                    })
                    network_results.append(
                        ConnectToSubnetActionResult(actionId=subnet.actionId, interface=interface_json))
                    ports.remove(port)
                    break
            GNS3StateFlow(self._rest_client).start_vm(project_id, node_id)
        except Exception:
            self.delete_node(project_id, node_id)

        resource_address = "{}:{}".format(node.get("console_host", self._resource_config.address),
                                          node.get("console"))
        deploy_result = DeployAppResult(actionId=deploy_action.actionId,
                                        infoMessage="Deployment Completed Successfully",
                                        vmUuid=node_id,
                                        vmName=app_name,
                                        deployedAppAddress=resource_address,
                                        deployedAppAttributes=attributes,
                                        vmDetailsData=create_vm_details(
                                            app_name,
                                            self._helper,
                                            deploy_action.actionParams.deployment.deploymentPath,
                                            node))
        if cancellation_context.is_cancelled:
            self.delete_node(project_id, node_id)
            return "deployment cancelled and deleted successfully"

        action_results = [deploy_result]
        action_results.extend(network_results)
        return action_results

    def deploy_node(self, project_id, vm_instance_details):
        return self._rest_client.request_post("v2/projects/{}/nodes".format(project_id),
                                              vm_instance_details.get_request_data(self._helper))

    def delete_node(self, project_id, node_id):
        uri = "v2/projects/{}/nodes/{}".format(project_id, node_id)
        self._rest_client.request_delete(uri)
