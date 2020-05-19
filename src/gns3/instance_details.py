import json
from abc import abstractmethod, ABC

from gns3.flows.gns3_helper import GNS3Error


class BaseInstanceDetails(ABC):
    def __init__(self, deploy_action):
        self._deploy_action = deploy_action
        self._deployment_path = deploy_action.actionParams.deployment.deploymentPath
        self._deploy_attribs = deploy_action.actionParams.deployment.attributes
        self._app_resource = deploy_action.actionParams.appResource.attributes

    @property
    def app_name(self):
        return self._deploy_action.actionParams.appName

    @property
    def ram(self):
        return int(self._deploy_attribs.get("{}.Ram".format(self._deployment_path), 512))

    @property
    def user(self):
        return self._app_resource.get("User", "")

    @property
    def password(self):
        return self._app_resource.get("Password", "")

    @property
    def server(self):
        return self._deploy_attribs.get("{}.Server".format(self._deployment_path), "")

    @abstractmethod
    def get_request_data(self, helper):
        pass


class TemplateInstanceDetails(BaseInstanceDetails):
    @property
    def template_name(self):
        return self._deploy_attribs.get("{}.Template Name".format(self._deployment_path), "")

    @property
    def additional_config(self):
        response = self._deploy_attribs.get("{}.Additional Configuration".format(self._deployment_path), "")
        result = {}
        if response:
            result = json.loads(response)
        return result

    def get_request_data(self, helper):
        return self.additional_config


class QemuInstanceDetails(BaseInstanceDetails):
    @property
    def node_type(self):
        return "qemu"

    @property
    def hda_disk_image(self):
        return self._deploy_attribs.get("{}.HDA Disk Image".format(self._deployment_path), "")

    @property
    def qemu_path(self):
        return self._deploy_attribs.get("{}.QEMU Path".format(self._deployment_path), "qemu-system-x86_64")

    @property
    def additional_config(self):
        response = self._deploy_attribs.get("{}.Additional Configuration".format(self._deployment_path), "")
        result = {}
        if response:
            result = json.loads(response)
        return result

    def get_request_data(self, helper):
        data = {"node_type": self.node_type,
                "compute_id": helper.get_compute_node(self.server),
                "name": self.app_name,
                "first_port_name": "mgmt0/0"
                }
        properties = {"hda_disk_image": self.hda_disk_image,
                              "ram": self.ram,
                              "adapters": 4,
                              "adapter_type": "e1000",
                              "qemu_path": self.qemu_path}
        data.update(self.additional_config)
        properties.update(data.get("properties", {}))
        data["properties"] = properties
        return data


class DynamipsInstanceDetails(BaseInstanceDetails):
    @property
    def node_type(self):
        return "dynamips"

    @property
    def image(self):
        return self._deploy_attribs.get("{}.Image".format(self._deployment_path), "")

    @property
    def platform(self):
        return self._deploy_attribs.get("{}.Platform".format(self._deployment_path), "")

    @property
    def slot1(self):
        return self._deploy_attribs.get("{}.Slot 1".format(self._deployment_path), "")

    @property
    def slot2(self):
        return self._deploy_attribs.get("{}.Slot 2".format(self._deployment_path), "")

    @property
    def slot3(self):
        return self._deploy_attribs.get("{}.Slot 3".format(self._deployment_path), "")

    @property
    def slot4(self):
        return self._deploy_attribs.get("{}.Slot 4".format(self._deployment_path), "")

    @property
    def slot5(self):
        return self._deploy_attribs.get("{}.Slot 5".format(self._deployment_path), "")

    @property
    def slot6(self):
        return self._deploy_attribs.get("{}.Slot 6".format(self._deployment_path), "")

    def _get_slots(self):
        response = {}
        if self.slot1:
            response["slot1"] = self.slot1
        if self.slot2:
            response["slot2"] = self.slot2
        if self.slot3:
            response["slot3"] = self.slot3
        if self.slot4:
            response["slot4"] = self.slot4
        if self.slot5:
            response["slot5"] = self.slot5
        if self.slot6:
            response["slot6"] = self.slot6
        return response

    def get_request_data(self, helper):
        response = {"node_type": self.node_type,
                    "compute_id": helper.get_compute_node(self.server),
                    "name": self.app_name,
                    "properties":
                        {"image": self.image,
                         "ram": self.ram,
                         "platform": self.platform
                         }
                    }
        response["properties"].update(self._get_slots())
        return response


DEPLOYMENT_PATH_MAP = {"QEMU": QemuInstanceDetails,
                       "Dynamips": DynamipsInstanceDetails,
                       "Template": TemplateInstanceDetails
                       }


def create_vm_instance_details(deploy_action):
    deployment_path = deploy_action.actionParams.deployment.deploymentPath.lower()
    instance = next((DEPLOYMENT_PATH_MAP.get(k) for k in DEPLOYMENT_PATH_MAP if k.lower() in deployment_path), None)
    if instance:
        return instance(deploy_action)
    else:
        raise GNS3Error("Failed to locate {} Deployment Path".format(deployment_path))
