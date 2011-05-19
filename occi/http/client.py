
class HTTPClientBackend(object):
    def __init__(self, http_client, user=None):
        self.http_client = http_client

    def get_entity(self, location):
        """Retrieve an OCCI resource instance at the specified URL location.
        """

        return entity

    def save_entity(self, entity):
        return entity

    def delete_entity(self, entity):
        pass

    def exec_entity_action(self, entity, action, payload=None):
        return payload

    def list_entities(self, collection, category_filter=None, attribute_filter=None):
        return entities

    def list_categories(self):
        return categories

    def reload_categories(self):
        pass

