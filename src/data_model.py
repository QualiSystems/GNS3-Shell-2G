from cloudshell.shell.core.driver_context import ResourceCommandContext, ResourceRemoteCommandContext, \
    AutoLoadDetails, AutoLoadAttribute
from cloudshell.shell.core.session.cloudshell_session import CloudShellSessionContext
from cloudshell.shell.core.session.logging_session import LoggingSessionContext


class Gns3CloudProviderDataModel(object):
    def __init__(self, name, context):
        """
        
        """
        self.attributes = {}
        self.resources = {}
        self._cs_model_name = 'GNS3 Cloud Provider'
        self._name = name
        self._context = context

    @classmethod
    def create_from_context(cls, context):
        """
        Creates an instance of NXOS by given context
        :param context: cloudshell.shell.core.driver_context.ResourceCommandContext
        :type context: ResourceCommandContext, ResourceRemoteCommandContext
        :return:
        :rtype Gns3 Cloud Provider
        """
        result = Gns3CloudProviderDataModel(name=context.resource.name, context=context)
        for attr in context.resource.attributes:
            result.attributes[attr] = context.resource.attributes[attr]
        return result

    @property
    def reservation_id(self):
        if hasattr(self._context, "remote_reservation"):
            reservation = self._context.remote_reservation
        else:
            reservation = self._context.reservation
        return reservation.reservation_id

    @property
    def tags(self):
        if hasattr(self._context, "remote_reservation"):
            reservation = self._context.remote_reservation
        else:
            reservation = self._context.reservation
        return {
            "CreatedBy": "Cloudshell",
            "ReservationId": reservation.reservation_id,
            "Owner": reservation.owner_user,
            "Domain": reservation.domain,
            "Blueprint": reservation.environment_name
        }

    def get_logger(self):
        return LoggingSessionContext(self._context)

    @property
    def remote_instance_id(self):
        """ Retrieve UID of the VM the resource represents
        :return:
        """

        endpoint = self._context.remote_endpoints[0].fullname.split('/')[0]
        parent_connected_resource = self.api.GetResourceDetails(endpoint)
        try:
            instance_id = [attribute.Value for attribute in parent_connected_resource.ResourceAttributes if
                           attribute.Name == 'VM_UUID'][0]
        except Exception:
            instance_id = parent_connected_resource.VmDetails.UID
        return instance_id

    @property
    def api(self):
        return CloudShellSessionContext(self._context).get_api()

    @property
    def cloudshell_model_name(self):
        """
        Returns the name of the Cloudshell model
        :return:
        """
        return self._cs_model_name

    @property
    def networking_type(self):
        """
        :rtype: str
        """
        return self.attributes[
            'Gns3 Cloud Provider.Networking type'] \
            if 'Gns3 Cloud Provider.Networking type' in self.attributes else "Both"

    @networking_type.setter
    def networking_type(self, value):
        """
        networking type that the cloud provider implements- L2 networking (VLANs) or L3 (Subnets)
        :type value: str
        """
        self.attributes['Gns3 Cloud Provider.Networking type'] = value

    @property
    def address(self):
        """
        :rtype: str
        """
        return self._context.resource.address

    @property
    def port(self):
        """
        :rtype: str
        """
        return self.attributes.get("{}.Port".format(self._cs_model_name), 3080)

    @property
    def networks_in_use(self):
        """
        :rtype: str
        """
        return self.attributes[
            'Gns3 Cloud Provider.Networks in use'] if 'Gns3 Cloud Provider.Networks in use' in self.attributes else None

    @networks_in_use.setter
    def networks_in_use(self, value=''):
        """
        Reserved network ranges to be excluded when allocated sandbox networks (for cloud providers with L3 networking).
        The syntax is a comma separated CIDR list. For example "10.0.0.0/24, 10.1.0.0/26"
        :type value: str
        """
        self.attributes['Gns3 Cloud Provider.Networks in use'] = value

    @property
    def vlan_type(self):
        """
        :rtype: str
        """
        return self.attributes[
            'Gns3 Cloud Provider.VLAN Type'] if 'Gns3 Cloud Provider.VLAN Type' in self.attributes else None

    @vlan_type.setter
    def vlan_type(self, value='VLAN'):
        """
        whether to use VLAN or VXLAN (for cloud providers with L2 networking)
        :type value: str
        """
        self.attributes['Gns3 Cloud Provider.VLAN Type'] = value

    @property
    def gns3_version(self):
        """
        :rtype: str
        """
        return self.attributes[
            'Gns3 Cloud Provider.GNS3 Version'] \
            if 'Gns3 Cloud Provider.GNS3 Version' in self.attributes else ""

    @gns3_version.setter
    def gns3_version(self, value):
        """

        :type value: str
        """
        self.attributes['Gns3 Cloud Provider.GNS3 Version'] = value

    @property
    def user(self):
        """
        """
        return self.attributes.get('{}.User'.format(self._cs_model_name), "")

    @property
    def password(self):
        """
        """
        response = self.attributes.get('{}.Password'.format(self._cs_model_name), "")
        return self.api.DecryptPassword(response).Value

    def create_autoload_details(self):
        return AutoLoadDetails([],
                               [AutoLoadAttribute(
                                   relative_address="",
                                   attribute_name="{}.GNS3 Version".format(self._cs_model_name),
                                   attribute_value=self.gns3_version)])
