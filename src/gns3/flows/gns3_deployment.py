import json

from cloudshell.cp.core.models import DeployAppResult, Attribute, ConnectToSubnetActionResult

from gns3.flows.gns3_helper import Gns3Helper
from gns3.instance_details import TemplateInstanceDetails
from gns3.shell_helper import create_vm_details
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
        attributes.append(Attribute("Password", vm_instance_details.password))

        if isinstance(vm_instance_details, TemplateInstanceDetails):
            template_id = self._helper.get_template_id_by_name(project_id,
                                                               vm_instance_details.template_name)
            result = self._helper.create_from_template(project_id=project_id,
                                                       name=vm_instance_details.app_name,
                                                       template_id=template_id)
        else:
            result = self.deploy_node(project_id=project_id,
                                      vm_instance_details=vm_instance_details)
        node_id = result.get("node_id")
        app_name = "{}-{}".format(vm_instance_details.app_name, node_id.split("-")[-1])
        node = self._helper.update_vm_name(new_name=app_name, node_id=node_id, project_id=project_id)
        node_id = node.get("node_id")
        port = node.get("ports", [])[0].get("port_number")
        adapter = node.get("ports", [])[0].get("adapter_number")
        self._helper.connect_management_switch(project_id, node_id=node_id, node_port=port, node_adapter=adapter)

        port_index = 0
        for subnet in subnet_actions:
            port_index += 1
            switch = self._helper.get_switch(project_id, subnet.actionParams.subnetId)
            node_port = node.get("ports", [])[port_index].get("port_number")
            node_adapter = node.get("ports", [])[port_index].get("adapter_number")
            self._helper.connect_nodes(project_id=project_id,
                                       project_switch=switch,
                                       node_port=node_port,
                                       node_adapter=node_adapter,
                                       node_id=node_id)

            interface_json = json.dumps({
                'interface_id': node.get("ports", [])[port_index].get("name"),
                'MAC Address': "",
            })
            network_results.append(
                ConnectToSubnetActionResult(actionId=subnet.actionId, interface=interface_json))
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
