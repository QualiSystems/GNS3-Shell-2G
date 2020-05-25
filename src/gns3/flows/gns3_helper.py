import json

from gns3.rest_client.rest_api_handler import RestJsonClient, RestClientException
from gns3.helpers.shell_helper import Link
from gns3.uri_templates import api_templates


class GNS3Error(Exception):
    pass


class Gns3Helper(object):
    def __init__(self, rest_client: RestJsonClient, logger, resource_config):
        self._rest_client = rest_client
        self._logger = logger
        self._resource_config = resource_config

    def get_project_id(self):
        response = self._rest_client.request_get(api_templates.PROJECTS)
        project_id = next((project.get("project_id")
                           for project in response
                           if project.get("name") == self._resource_config.reservation_id),
                          None)
        return project_id

    def get_switch(self, project_id, node_id):
        url = f"/v2/projects/{project_id}/nodes/{node_id}"
        return self._rest_client.request_get(url)

    def get_connected_project_switches(self, project_id, switch):
        current_links = self._rest_client.request_get(f"v2/projects/{project_id}/links")

        links = [Link(x.get("nodes"))
                 for x in current_links
                 for n in x.get("nodes")
                 if n.get("node_id") == switch.get("node_id")]
        return links

    def get_node_by_id(self, project_id, node_id):
        return self._rest_client.request_get(f"v2/projects/{project_id}/nodes/{node_id}")

    def get_available_switch_port(self, project_id, switch):
        mgmt_id = switch.get("node_id")
        current_links = self._rest_client.request_get(f"v2/projects/{project_id}/links")
        switch_ports = {x.get("port_number"): x.get("adapter_number")
                        for x in switch.get("ports")}
        links = {n.get("port_number"): n.get("adapter_number")
                 for x in current_links for n in x.get("nodes") if n.get("node_id") == mgmt_id}
        available_port = next((x for x in switch_ports
                               if not links.get(x) == switch_ports.get(x) and not links.get(x)),
                              None)
        return available_port, switch_ports.get(available_port)

    def get_management_switch(self, project_id=None):
        if not project_id:
            project_id = self.get_project_id()
        return self.get_project_node_by_name(project_id, self._resource_config.reservation_id)

    def get_links(self, project_id=None):
        if not project_id:
            project_id = self.get_project_id()
        url = f"/v2/projects/{project_id}/links"
        return self._rest_client.request_get(url)

    def get_links_per_node(self, project_id, node_id):
        current_links = self.get_links(project_id)
        links = [Link(x.get("nodes"))
                 for x in current_links
                 for n in x.get("nodes")
                 if n.get("node_id") == node_id]
        return links

    def check_if_link_is_connected(self, project_id, node_id, port_number, adapter_number, switch_id):
        for link in self.get_links_per_node(project_id=project_id, node_id=node_id):
            if link.src_node_id == switch_id \
                    and link.dst_port_number == port_number \
                    and link.dst_adapter_number == adapter_number:
                return True
            elif link.dst_node_id == switch_id \
                    and link.src_port_number == port_number \
                    and link.src_adapter_number == adapter_number:
                return True

    def get_compute_node(self, name):
        url = "/v2/computes"
        response = self._rest_client.request_get(url)
        result = next((compute.get("compute_id")
                       for compute in response
                       if compute.get("compute_id") == name or compute.get("name") == name),
                      None)
        if not result:
            raise GNS3Error(f"Unable to find {name} Compute node")
        return result

    def get_project_node_by_name(self, project_id, name):
        if not project_id:
            project_id = self.get_project_id()
        url = f"/v2/projects/{project_id}/nodes"
        response = self._rest_client.request_get(url)
        return next((project
                     for project in response
                     if project.get("name") == name),
                    None)

    def get_template_id_by_name(self, name):
        url = "/v2/templates"
        response = self._rest_client.request_get(url)
        result = next((template.get("template_id")
                       for template in response
                       if template.get("name") == name),
                      None)
        if not result:
            raise GNS3Error(f"Failed to get Template ID, for {name}")
        return result

    def create_project(self):
        response = self._rest_client.request_post(api_templates.PROJECTS,
                                                  {"name": self._resource_config.reservation_id,
                                                   "auto_close": False})
        project_id = response.get("project_id")
        if not project_id:
            raise GNS3Error("Failed to create project")
        x = -150
        y = -150
        data = {"compute_id": "local",
                "x": x,
                "y": y
                }
        url = f"/v2/projects/{project_id}/templates/39e257dc-8412-3174-b6b3-0ee3ed6a43e9"
        cloud = self._rest_client.request_post(url, data=data)
        cloud_id = cloud.get("node_id")
        cloud_port = cloud.get("ports", [])[0].get("port_number")
        cloud_adapter = cloud.get("ports", [])[0].get("adapter_number")
        switch = self.create_switch(project_id, self._resource_config.reservation_id)
        self.connect_nodes(project_id=project_id,
                           project_switch=switch,
                           node_port=cloud_port,
                           node_adapter=cloud_adapter,
                           node_id=cloud_id)

        return project_id

    def create_switch(self, project_id, name):
        data = {"compute_id": "local"}
        template_id = "1966b864-93e7-32d5-965f-001384eec461"
        # url = f"/v2/projects/{project_id}/templates/1966b864-93e7-32d5-965f-001384eec461"
        switch = self.create_from_template(project_id=project_id, name=name, template_id=template_id, data=data)
        return switch

    def create_node_from_template(self, project_id, name, template_id, interfaces_count=None, data=None):
        duplicate_url = f"/v2/templates/{template_id}/duplicate"
        if interfaces_count:
            duplicate_template_response = self._rest_client.request_post(duplicate_url)
            if not duplicate_template_response:
                raise GNS3Error(f"Failed to create node from template for app {name}")
            template_id = duplicate_template_response.get("template_id")
            request_data = {"adapters": interfaces_count, "name": f"{name}-{project_id[-4:]}"}
            if data:
                request_data.update(data)
            self._rest_client.request_put(f"v2/templates/{template_id}", data=json.dumps(request_data))

        result = self.create_from_template(project_id, name, template_id)
        if interfaces_count:
            self._rest_client.request_delete(f"/v2/templates/{template_id}")
        return result

    def create_from_template(self, project_id, name, template_id, data=None):
        request_data = {
            "name": name,
            "x": 10,
            "y": 10
        }
        if data:
            request_data.update(data)
        self._logger.debug(f"Request data: {request_data}")
        url = f"/v2/projects/{project_id}/templates/{template_id}"
        switch = self._rest_client.request_post(url, data=request_data)
        switch_id = switch.get("node_id")
        self.update_vm_name(project_id, switch_id, name)
        return switch

    def connect_nodes(self, project_id, project_switch, node_port, node_adapter, node_id, max_retries=5):
        project_switch_id = project_switch.get("node_id")
        is_connected = False
        retry = 1
        while not is_connected and retry < max_retries:
            try:
                project_switch_port, project_switch_adapter = self.get_available_switch_port(project_id, project_switch)
                self._connect_nodes(project_id,
                                    src_node_id=project_switch_id,
                                    src_node_port=project_switch_port,
                                    src_adapter_num=project_switch_adapter,
                                    dst_node_id=node_id,
                                    dst_node_port=node_port,
                                    dst_adapter_num=node_adapter)
                is_connected = True
            except RestClientException as e:
                self._logger.exception("Failed to connect to a switch. retrying...")
                if e.status_code == 409:
                    is_connected = self.check_if_link_is_connected(project_id=project_id,
                                                                   node_id=node_id,
                                                                   port_number=node_port,
                                                                   adapter_number=node_adapter,
                                                                   switch_id=project_switch_id
                                                                   )
                    if not is_connected:
                        retry += 1
                else:
                    raise

    def _connect_nodes(self, project_id, src_node_id, dst_node_id,
                       src_node_port, dst_node_port, src_adapter_num, dst_adapter_num):
        link_data = {
            "capture_compute_id": "local",
            "nodes": [
                {
                    "adapter_number": src_adapter_num,
                    "port_number": src_node_port,
                    "node_id": src_node_id
                },
                {
                    "adapter_number": dst_adapter_num,
                    "port_number": dst_node_port,
                    "node_id": dst_node_id
                }

            ]

        }
        url = f"/v2/projects/{project_id}/links"

        self._rest_client.request_post(url, data=link_data)

    def connect_management_switch(self, project_id, node_id, node_port, node_adapter):
        management_switch = self.get_management_switch(project_id)
        self.connect_nodes(project_id=project_id,
                           project_switch=management_switch,
                           node_port=node_port,
                           node_adapter=node_adapter,
                           node_id=node_id)

    def delete_project(self, project_id=None):
        if not project_id:
            project_id = self.get_project_id()
        response = self._rest_client.request_delete(f"v2/projects/{project_id}")
        return response

    def update_vm_name(self, project_id, node_id, new_name):
        data = {"name": new_name}
        response = self._rest_client.request_put(f"v2/projects/{project_id}/nodes/{node_id}", json.dumps(data))
        return response
