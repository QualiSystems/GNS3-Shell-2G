from gns3.rest_client.rest_api_handler import RestJsonClient


class GNS3StateFlow(object):
    def __init__(self, rest_client: RestJsonClient, logger=None):
        self._rest_client = rest_client
        self._logger = logger

    def start_vm(self, project_id, node_id):
        url = "/v2/projects/{project_id}/nodes/{node_id}/start".format(
            project_id=project_id,
            node_id=node_id
        )
        self._rest_client.request_post(url)

    def stop_vm(self, project_id, node_id):
        url = "/v2/projects/{project_id}/nodes/{node_id}/stop".format(
            project_id=project_id,
            node_id=node_id
        )
        self._rest_client.request_post(url)
