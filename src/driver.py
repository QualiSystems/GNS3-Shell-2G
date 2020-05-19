import json

import jsonpickle
from cloudshell.cp.core.drive_request_parser import DriverRequestParser
from cloudshell.shell.core.resource_driver_interface import ResourceDriverInterface
from cloudshell.cp.core.models import DriverResponse, DeployApp, PrepareCloudInfraResult, PrepareSubnetActionResult, \
    CreateKeysActionResult, ActionResultBase, ConnectSubnet
from cloudshell.shell.core.driver_context import InitCommandContext, AutoLoadCommandContext, AutoLoadDetails, \
    ResourceRemoteCommandContext
from cloudshell.shell.core.session.cloudshell_session import CloudShellSessionContext
from cloudshell.shell.core.session.logging_session import LoggingSessionContext

from data_model import Gns3CloudProviderDataModel
from gns3.flows.gns3_autoload import GNS3Autoload
from gns3.flows.gns3_deployment import GNS3Deployment
from gns3.flows.gns3_helper import Gns3Helper
from gns3.flows.gns3_state_flows import GNS3StateFlow
from gns3.instance_details import create_vm_instance_details
from gns3.rest_client.rest_api_handler import RestJsonClient
from gns3.shell_helper import create_vm_details, set_command_result


class Gns3CloudProviderDriver(ResourceDriverInterface):
    SHELL_NAME = "GNS3 Cloud Provider"

    def initialize(self, context):
        """
        Called every time a new instance of the driver is created

        This method can be left unimplemented but this is a good place to load and cache the driver configuration,
        initiate sessions etc.
        Whatever you choose, do not remove it.

        :param InitCommandContext context: the context the command runs on
        """
        pass

    # <editor-fold desc="Mandatory Commands">

    # <editor-fold desc="Discovery">

    def get_inventory(self, context):
        """
        Called when the cloud provider resource is created
        in the inventory.

        Method validates the values of the cloud provider attributes, entered by the user as part of the cloud provider resource creation.
        In addition, this would be the place to assign values programmatically to optional attributes that were not given a value by the user.

        If one of the validations failed, the method should raise an exception

        :param AutoLoadCommandContext context: the context the command runs on
        :return Attribute and sub-resource information for the Shell resource you can return an AutoLoadDetails object
        :rtype: AutoLoadDetails
        """

        resource_config = Gns3CloudProviderDataModel.create_from_context(context)
        with resource_config.get_logger() as logger:
            rest_client = RestJsonClient(resource_config)
            result = GNS3Autoload(rest_client, logger=logger, resource_config=resource_config)
            result.discover()
            return resource_config.create_autoload_details()

    def PowerCycle(self, context, ports, delay):
        """ please leave it as is """
        pass

    def cleanup(self):
        pass

    def Deploy(self, context, request=None, cancellation_context=None):
        """  """

        actions = DriverRequestParser().convert_driver_request_to_actions(request)
        resource_config = Gns3CloudProviderDataModel.create_from_context(context)
        with LoggingSessionContext(context) as logger:

            deploy_action = None
            subnet_actions = list()
            for action in actions:
                if isinstance(action, DeployApp):
                    deploy_action = action
                if isinstance(action, ConnectSubnet):
                    subnet_actions.append(action)

            if deploy_action:
                vm_instance_details = create_vm_instance_details(deploy_action)
                rest_client = RestJsonClient(resource_config)
                deployer = GNS3Deployment(rest_client=rest_client, logger=logger, resource_config=resource_config)
                results = deployer.deploy(deploy_action, cancellation_context, vm_instance_details, subnet_actions)
                return DriverResponse(results).to_driver_response_json()
            else:
                raise Exception('Failed to deploy VM')

    def DeleteInstance(self, context, ports):
        """ Delete a VM
        :param context: ResourceRemoteCommandContext
        :param ports: sub-resources to delete
        :return:
        """

        # Code to delete instance based on remote command context
        resource_config = Gns3CloudProviderDataModel.create_from_context(context)
        with resource_config.get_logger() as logger:
            rest_client = RestJsonClient(resource_config)
            helper = Gns3Helper(rest_client=rest_client, logger=logger, resource_config=resource_config)
            deployer = GNS3Deployment(rest_client=rest_client, logger=logger, resource_config=resource_config)
            deployer.delete_node(helper.get_project_id(), resource_config.remote_instance_id)
            name = context.remote_endpoints[0].fullname.split('/')[0]

            return "Successfully terminated instance " + name

    def ApplyConnectivityChanges(self, context, request):
        """
        Respond to CloudShell Server's request to apply L2 Connectivity changes 
        Implemented as empty implementation (always succeeds)
        :param context: ResourceCommandContext
        :param request: Changes to perform
        :return: 
        """
        api = CloudShellSessionContext(context).get_api()
        resource_config = Gns3CloudProviderDataModel.create_from_context(context)
        with resource_config.get_logger() as logger:
            logger.info("-"*10)
            logger.info(request)
            logger.info("-"*10)
            logger.info(type(request))
            logger.info("-"*10)

        # Write request
        request_json = json.loads(request)

        # Build Response
        action_results = [
            {
                "actionId": str(actionResult['actionId']),
                "type": str(actionResult['type']),
                "infoMessage": "",
                "errorMessage": "",
                "success": "True",
                "updatedInterface": "None",
            } for actionResult in request_json['driverRequest']['actions']
        ]

        return set_command_result(str({"driverResponse": {"actionResults": action_results}}), False)

    def remote_refresh_ip(self, context, cancellation_context, ports):
        """ Refresh the IP of the resource from the VM
        :type context ResourceRemoteCommandContext
        """

        # resource_config = Gns3CloudProviderDataModel.create_from_context(context)
        #
        # oci_ops = OciOps(resource_config)
        # instance_id = resource_config.remote_instance_id
        # name = context.remote_endpoints[0].fullname.split('/')[0]
        # vnic = oci_ops.get_primary_vnic(instance_id)
        # resource_config.api.UpdateResourceAddress(name, vnic.private_ip)
        # try:
        #     resource_config.api.SetAttributeValue(name, "Public IP",
        #                                           vnic.public_ip)
        # except:
        #     pass
        pass

    def PowerOff(self, context, ports):
        """ Power Off the VM represented by the resource
        :param context: ResourceRemoteCommandContext
        :param list[string] ports: the ports of the connection between the remote resource and the local resource, NOT IN USE!!!

        :type context ResourceRemoteCommandContext
        """

        resource_config = Gns3CloudProviderDataModel.create_from_context(context)
        with resource_config.get_logger() as logger:
            rest_client = RestJsonClient(resource_config)

            gns_helper = Gns3Helper(rest_client=rest_client,
                                    logger=logger,
                                    resource_config=resource_config)

            instance_id = resource_config.remote_instance_id
            project_id = gns_helper.get_project_id()
            logger.info("Instance id: {}".format(instance_id))
            GNS3StateFlow(rest_client).stop_vm(project_id=project_id, node_id=instance_id)
            name = context.remote_endpoints[0].fullname.split('/')[0]


            try:
                resource_config.api.SetResourceLiveStatus(name, 'OCOffline',
                                                          'Resource is powered off')
            except:  # if "OCOnline" live status is missing, revert to "Offline" live status
                resource_config.api.SetResourceLiveStatus(name, 'Offline',
                                                          'Resource is powered off')

        return "VM stopped successfully"

    # the name is by the Qualisystems conventions
    def PowerOn(self, context, ports):
        """ Powers on the remote vm
        :param ResourceRemoteCommandContext context: the context the command runs on
        :param list[string] ports: the ports of the connection between the remote resource and the local resource, NOT IN USE!!!

        :type context ResourceRemoteCommandContext
        """

        resource_config = Gns3CloudProviderDataModel.create_from_context(context)
        with resource_config.get_logger() as logger:
            rest_client = RestJsonClient(resource_config)

            gns_helper = Gns3Helper(rest_client=rest_client, 
                                    logger=logger, 
                                    resource_config=resource_config)

            instance_id = resource_config.remote_instance_id
            project_id = gns_helper.get_project_id()
            logger.info("Instance id: {}".format(instance_id))
            GNS3StateFlow(rest_client).start_vm(project_id=project_id, node_id=instance_id)
            name = context.remote_endpoints[0].fullname.split('/')[0]

            try:
                resource_config.api.SetResourceLiveStatus(name, 'OCOnline',
                                                          'Resource is powered on')
            except:  # if "OCOnline" live status is missing, revert to "Offline" live status
                resource_config.api.SetResourceLiveStatus(name, 'Online',
                                                          'Resource is powered on')

        return "VM started  successfully"

    def get_vm_uuid(self, context, vm_name):
        """
        :param context: ResourceRemoteCommandContext
        :param vm_name: full resource name of the resource
        :return: UID of the VM in OCI
        """

        resource_config = Gns3CloudProviderDataModel.create_from_context(context)

        res_details = resource_config.api.GetResourceDetails(vm_name)
        return str(jsonpickle.encode(res_details.VmDetails.UID, unpicklable=False))

    def GetVmDetails(self, context, cancellation_context, requests):
        """
        Return VM Details JSON to the Quali Server for refreshing the VM Details pane
        :param context: ResourceRemoteCommandContext
        :param cancellation_context: bool - will become True if action is cancelled
        :param requests: str JSON - requests for VMs to refresh
        :return:
        """

        resource_config = Gns3CloudProviderDataModel.create_from_context(context)
        requests_json = json.loads(requests)
        vm_details_results = []
        with resource_config.get_logger() as logger:
            logger.info(requests)
            for refresh_request in requests_json["items"]:
                vm_name = refresh_request["deployedAppJson"]["name"]
                deployment_service = refresh_request["appRequestJson"]["deploymentService"][
                    "name"]
                rest_client = RestJsonClient(resource_config)

                instance_id = refresh_request["deployedAppJson"]["vmdetails"]["uid"]
                # instance_id = resource_config.api.GetResourceDetails(vm_name).VmDetails.UID
                helper = Gns3Helper(rest_client=rest_client, logger=logger, resource_config=resource_config)
                project_id = helper.get_project_id()
                instance = helper.get_node_by_id(project_id=project_id, node_id=instance_id)
                vm_details_results.append(
                    create_vm_details(vm_name=vm_name,
                                      helper=helper,
                                      deployment_service_name=deployment_service,
                                      instance=instance))
        return str(jsonpickle.encode(vm_details_results, unpicklable=False))

    def PrepareSandboxInfra(self, context, request, cancellation_context):
        """
        Called by CloudShell Orchestration during the Setup process in order to populate information about the networking environment used by the sandbox
        :param context: ResourceRemoteCommandContext
        :param request: Actions to be performed to prepare the networking environment sent by CloudShell Server
        :param cancellation_context:
        :return:
        """

        with LoggingSessionContext(context) as logger:
            logger.info(request)
            resource_config = Gns3CloudProviderDataModel.create_from_context(context)

            json_request = json.loads(request)
            resource_config.api.WriteMessageToReservationOutput(resource_config.reservation_id,
                                                                'Preparing Sandbox Connectivity...')
            subnet_results = []
            subnet_dict = {}
            for action in json_request["driverRequest"]["actions"]:
                if action["type"] == "prepareCloudInfra":
                    vcn_action_id = action.get("actionId")
                elif action["type"] == "prepareSubnet":
                    subnet_action_id = action.get("actionId")
                    subnet_cidr = action.get("actionParams", {}).get("cidr")
                    default_alias = "Subnet {}".format(subnet_cidr)
                    subnet_alias = action.get("actionParams", {}).get("alias", None)
                    if not subnet_alias:
                        subnet_alias = default_alias
                    subnet_dict[subnet_action_id] = subnet_alias
                elif action["type"] == "createKeys":
                    keys_action_id = action.get("actionId")

            rest_client = RestJsonClient(resource_config)

            gns_helper = Gns3Helper(rest_client=rest_client,
                                    logger=logger,
                                    resource_config=resource_config)
            project_id = gns_helper.create_project()

            prepare_network_result = PrepareCloudInfraResult(vcn_action_id)
            prepare_network_result.securityGroupId = ""

            for action_id in subnet_dict:
                switch = gns_helper.create_switch(project_id, subnet_dict.get(action_id))
                subnet_result = PrepareSubnetActionResult()
                subnet_result.actionId = action_id
                subnet_result.subnetId = switch.get("node_id")
                subnet_result.infoMessage = "Success"
                subnet_results.append(subnet_result)

        prepare_network_result.infoMessage = 'PrepareConnectivity finished successfully'
        prepare_network_result.networkId = project_id
        create_key_result = CreateKeysActionResult(actionId=keys_action_id, infoMessage='',
                                                   accessKey="")

        results = [prepare_network_result, create_key_result]
        results.extend(subnet_results)

        result = DriverResponse(results).to_driver_response_json()
        return result

    def CleanupSandboxInfra(self, context, request):
        """

        :param context:
        :param request:
        :return:
        """

        json_request = json.loads(request)
        resource_config = Gns3CloudProviderDataModel.create_from_context(context)
        cleanup_action_id = next(action["actionId"] for action in json_request["driverRequest"]["actions"] if
                                 action["type"] == "cleanupNetwork")
        with resource_config.get_logger() as logger:
            rest_client = RestJsonClient(resource_config)

            helper = Gns3Helper(rest_client=rest_client, logger=logger, resource_config=resource_config)
            try:
                helper.delete_project()
            finally:
                if helper.get_project_id():
                    raise Exception("Failed to remove project")

            cleanup_result = ActionResultBase("cleanupNetwork", cleanup_action_id)

            return set_command_result({'driverResponse': {'actionResults': [cleanup_result]}})