from occi.core import Kind, Resource, Link

class DataObject(object):
    """A data object transferred using the OCCI protocol.

    A data object cat represent a resource instance, an action invocation,
    filter parameters, etc. It is up to the handler of the particular request/response
    to interpret the contents of a `DataObject`.
    """

    class DataObjectError(Exception):
        pass
    class Invalid(DataObjectError):
        pass

    def __init__(self, categories=None, attributes=None, links=None,
            location=None):
        self.categories = categories or []
        self.links = links or []
        self.attributes = attributes or []
        self.location = location

    def load_from_entity(self, entity, id2location=None, convert_attr=False):
        """Load `DataObject` with the contents of the specified Entity instance.

        >>> from occi.ext.infrastructure import *
        >>> compute = ComputeKind.entity_type(ComputeKind)
        >>> compute.id = 'compute/123'
        >>> compute.set_occi_attributes([('occi.compute.speed', 7.0/3)], validate=False)
        >>> storage = StorageKind.entity_type(StorageKind)
        >>> storage.id = 'storage/234'
        >>> storage.set_occi_attributes([('title', 'My Disk')], validate=False)
        >>> link = StorageLinkKind.entity_type(StorageLinkKind)
        >>> link.id = 'link/storage/345'
        >>> link.target = storage
        >>> link.set_occi_attributes([('occi.storagelink.deviceid', 'ide:0:1')], validate=False)
        >>> compute.links.append(link)
        >>> d = DataObject()
        >>> d.load_from_entity(compute, convert_attr=True)
        >>> d.location
        'compute/123'
        >>> d.categories
        [Kind('compute', 'http://schemas.ogf.org/occi/infrastructure#')]
        >>> d.attributes
        [('occi.compute.speed', '2.33')]
        >>> [(l.target_location, l.target_categories, l.target_title) for l in d.links]
        [('storage/234', [Kind('storage', 'http://schemas.ogf.org/occi/infrastructure#')], 'My Disk')]
        >>> [(l.link_location, l.link_categories, l.link_attributes) for l in d.links]
        [('link/storage/345', [Kind('storagelink', 'http://schemas.ogf.org/occi/infrastructure#')], [('occi.storagelink.deviceid', 'ide:0:1')])]

        """
        id2location = id2location or (lambda x: x)
        self.categories = entity.list_occi_categories()
        self.attributes = entity.get_occi_attributes(convert=convert_attr)
        self.location = id2location(entity.id)

        # Links
        if isinstance(entity, Resource):
            for link in entity.links:
                l = LinkRepr(
                        target_location=id2location(link.target.id),
                        target_categories=link.target.list_occi_categories(),
                        target_title=link.target.get_occi_attribute('title'),
                        link_location=id2location(link.id))
                link_attributes = link.get_occi_attributes(
                        convert=convert_attr,
                        exclude=('source', 'target'))
                if link_attributes:
                    l.link_categories = link.list_occi_categories()
                    l.link_attributes = link_attributes

                self.links.append(l)

    def save_to_entity(self, entity=None, location2id=None, category_registry=None,
            validate_attr=True, save_links=False):
        """Save the `DataObject` contents into an Entity instance.

        >>> from occi.ext.infrastructure import *
        >>> d = DataObject()
        >>> d.location = 'compute/123'
        >>> #d.categories = [Kind('compute', 'http://schemas.ogf.org/occi/infrastructure#')]
        >>> d.categories = [ComputeKind]
        >>> d.attributes = [('occi.compute.speed', '2.33')]
        >>> #l = LinkRepr(target_location='storage/234', target_categories=[Kind('storage', 'http://schemas.ogf.org/occi/infrastructure#')])
        >>> l = LinkRepr(target_location='storage/234', target_categories=[StorageKind])
        >>> l.link_location = 'link/storage/345'
        >>> #l.link_categories = [Kind('storagelink', 'http://schemas.ogf.org/occi/infrastructure#')]
        >>> l.link_categories = [StorageLinkKind]
        >>> l.link_attributes = [('occi.storagelink.deviceid', 'ide:0:1')]
        >>> d.links.append(l)
        >>> entity = d.save_to_entity(save_links=True)
        >>> entity.list_occi_categories()
        [Kind('compute', 'http://schemas.ogf.org/occi/infrastructure#')]
        >>> round(entity.get_occi_attribute('occi.compute.speed')*1000)
        2330.0
        >>> entity.links[0].list_occi_categories()
        [Kind('storagelink', 'http://schemas.ogf.org/occi/infrastructure#')]
        >>> entity.links[0].get_occi_attributes()
        [('source', 'compute/123'), ('target', 'storage/234'), ('occi.storagelink.deviceid', 'ide:0:1')]
        >>> entity.links[0].target.list_occi_categories()
        [Kind('storage', 'http://schemas.ogf.org/occi/infrastructure#')]
        >>> entity.links[0].target.get_occi_attributes()
        []
        """

        location2id = location2id or (lambda x: x)

        # Resolve categories
        kind, mixins = self._resolve_categories(self.categories, category_registry)

        # Create new entity if not specified already
        if not entity:
            # Kind instance required
            if not entity and not kind:
                raise self.Invalid('Kind instance not specified, cannot create Entity')
            entity = kind.entity_type(kind, mixins)
        else:
            if kind and str(kind) != str(entity.get_occi_kind()):
                raise self.Invalid('Cannot change Kind of existing Entity')
            [entity.add_occi_mixin(mixin) for mixin in mixins]

        # Load attributes
        entity.set_occi_attributes(self.attributes, validate=validate_attr)

        # Load Link relations
        if save_links and self.links:
            if not isinstance(entity, Resource):
                raise self.Invalid('Links only applicable to the Resource type')
            for link_repr in self.links:
                # Initialise target Resource
                t_kind, t_mixins = self._resolve_categories(
                        link_repr.target_categories, category_registry)
                target = t_kind.entity_type(t_kind, t_mixins)
                if not isinstance(target, Resource):
                    raise self.Invalid('Link target must be a Resource type')
                target.id = location2id(link_repr.target_location)

                # Initialise Link instance
                try:
                    l_kind, l_mixins = self._resolve_categories(
                            link_repr.link_categories, category_registry)
                except self.Invalid:
                    l_kind = LinkKind
                    l_mixins = []
                link = l_kind.entity_type(l_kind, l_mixins)
                if not isinstance(link, Link):
                    raise self.Invalid('Relation must be a Link type')
                link.id = location2id(link_repr.link_location)
                link.target = target
                default_attr = [
                        ('source', self.location),
                        ('target', link_repr.target_location)
                ]
                link.set_occi_attributes(
                        default_attr + link_repr.link_attributes,
                        validate=validate_attr)

                # Add Link instance to the Resource's list of links
                entity.links.append(link)

        return entity

    def _resolve_categories(self, categories, category_registry=None):
        """Extract `Kind` and `Mixin`s from a list of Categories. If specified,
        resolve each `Category` through the `CategoryRegistry`.
        """
        kind = None
        mixins = []

        # Resolve Categories and extract Kind
        for category in categories:
            if category_registry:
                category = category_registry.lookup_id(str(category))
            if isinstance(category, Kind):
                if kind is not None:
                    raise self.Invalid('Only one Kind instance allowed to define a resource')
                kind = category
            else:
                mixins.append(category)

        return kind, mixins

class LinkRepr(object):
    def __init__(self,
            target_location=None, target_title=None, target_categories=None,
            link_location=None, link_categories=None, link_attributes=None):
        self.target_location = target_location
        self.target_title = target_title
        self.target_categories = target_categories or []
        self.link_location = link_location
        self.link_categories = link_categories or []
        self.link_attributes = link_attributes or []


if __name__ == "__main__":
    import doctest
    doctest.testmod()
