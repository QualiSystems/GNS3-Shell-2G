from gns3.rest_client.rest_api_handler import RestJsonClient


class GNS3Autoload(object):
    def __init__(self, rest_client: RestJsonClient, logger, resource_config):
        self._rest_client = rest_client
        self._logger = logger
        self._resource_config = resource_config

    def discover(self):
        self._resource_config.gns3_version = self._get_version().get("version")

    def _get_version(self):
        return self._rest_client.request_get("/v2/version")
