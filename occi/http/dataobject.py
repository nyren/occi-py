
class DataObject(object):
    """A data object transferred using the OCCI protocol.

    A data object cat represent a resource instance, an action invocation,
    filter parameters, etc. It is up to the handler of the particular request/response
    to interpret the contents of a `DataObject`.
    """
    def __init__(self, categories=None, attributes=None, links=None,
            location=None):
        self.categories = categories or []
        self.links = links or []
        self.attributes = attributes or []
        self.location = location

class LinkRepr(object):
    def __init__(self,
            target_location=None, target_title=None, target_categories=None,
            link_location=None, link_categories=None, link_attributes=None):
        self.target_location = target_location
        self.target_title = target_title
        self.target_categories = target_categories or ()
        self.link_location = link_location
        self.link_categories = link_categories or ()
        self.link_attributes = link_attributes or ()

