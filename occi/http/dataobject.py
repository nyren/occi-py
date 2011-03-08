import urlparse

from occi.core import Category, Kind, Resource, Link, Action

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
            location=None, translator=None):
        self.categories = categories or []
        self.links = links or []
        self.attributes = attributes or []
        self.location = location

        self.translator = translator or LocationTranslator('')
        self.parse_flags = {}
        self.render_flags = {}

    def load_from_entity(self, entity, convert_attr=False):
        """Load `DataObject` with the contents of the specified Entity instance.

        >>> from occi.ext.infrastructure import *
        >>> compute = ComputeKind.entity_type(ComputeKind)
        >>> compute.id = 'compute/123'
        >>> compute.set_occi_attributes([('occi.compute.speed', 7.0/3)], validate=False)
        >>> compute.occi_set_applicable_action(ComputeStartActionCategory)
        >>> storage = StorageKind.entity_type(StorageKind)
        >>> storage.id = 'storage/234'
        >>> storage.set_occi_attributes([('title', 'My Disk')], validate=False)
        >>> link = StorageLinkKind.entity_type(StorageLinkKind)
        >>> link.id = 'link/storage/345'
        >>> link.target = storage
        >>> link.set_occi_attributes([('occi.storagelink.deviceid', 'ide:0:1')], validate=False)
        >>> compute.links.append(link)
        >>> d = DataObject(translator=LocationTranslator('/api/'))
        >>> d.load_from_entity(compute, convert_attr=True)
        >>> d.location
        '/api/compute/123'
        >>> d.categories
        [Kind('compute', 'http://schemas.ogf.org/occi/infrastructure#')]
        >>> d.attributes
        [('occi.compute.speed', '2.33')]
        >>> [(l.target_location, l.target_categories, l.target_title) for l in d.links]
        [('/api/storage/234', [Kind('storage', 'http://schemas.ogf.org/occi/infrastructure#')], 'My Disk'), ('/api/compute/123?action=start', [Category('start', 'http://schemas.ogf.org/occi/infrastructure/compute/action#')], 'Start Compute Resource')]
        >>> [(l.link_location, l.link_categories, l.link_attributes) for l in d.links]
        [('/api/link/storage/345', [Kind('storagelink', 'http://schemas.ogf.org/occi/infrastructure#')], [('occi.storagelink.deviceid', 'ide:0:1')]), (None, [], [])]

        """
        self.categories = entity.list_occi_categories()
        self.attributes = entity.get_occi_attributes(convert=convert_attr)
        self.location = self.translator.id2location(entity.id)

        # Links
        if isinstance(entity, Resource):
            for link in entity.links:
                l = LinkRepr(
                        target_location=self.translator.id2location(link.target.id),
                        target_categories=link.target.list_occi_categories(),
                        target_title=link.target.get_occi_attribute('title'),
                        link_location=self.translator.id2location(link.id))
                link_attributes = link.get_occi_attributes(
                        convert=convert_attr,
                        exclude=('source', 'target'))
                if link_attributes:
                    l.link_categories = link.list_occi_categories()
                    l.link_attributes = link_attributes

                self.links.append(l)

        # Actions
        for action in entity.occi_list_applicable_actions():
            l = LinkRepr(
                    target_location='%s?action=%s' % (self.location, action.term),
                    target_categories=[action],
                    target_title=action.title)
            self.links.append(l)

    def save_to_entity(self, entity=None, category_registry=None,
            validate_attr=True, save_links=False):
        """Save the `DataObject` contents into an Entity instance.

        >>> from occi.ext.infrastructure import *
        >>> d = DataObject(translator=LocationTranslator('/api'))
        >>> d.location = '/api/compute/123'
        >>> d.categories = [ComputeKind]
        >>> d.attributes = [('occi.compute.speed', '2.33')]
        >>> l = LinkRepr(target_location='/api/storage/234', target_categories=[StorageKind])
        >>> l.link_location = '/api/link/storage/345'
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

        # Resolve categories
        try:
            kind, mixins = self._resolve_categories(self.categories,
                    category_registry=category_registry)
        except Category.DoesNotExist as e:
            raise self.Invalid(e)

        # Create new entity if not specified already
        if not entity:
            # Kind instance required
            if not kind:
                raise self.Invalid('Kind not specified, cannot create Entity')
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
                target.id = self.translator.location2id(link_repr.target_location)

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
                link.id = self.translator.location2id(link_repr.link_location)
                link.target = target
                default_attr = [
                        ('source', self.translator.location2id(self.location)),
                        ('target', self.translator.location2id(link_repr.target_location))
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
                    raise self.Invalid('%s: Only one Kind allowed to define a resource' % category)
                kind = category
            elif isinstance(category, Mixin):
                mixins.append(category)
            else:
                raise self.Invalid('%s: Is neither a Kind nor a Mixin' % category)

        return kind, mixins

    def save_as_action(self, category_registry=None):
        """Save the `DataObject` contents as an Action instance.

        >>> from occi.ext.infrastructure import *
        >>> d = DataObject()
        >>> d.categories = [ComputeStartActionCategory]
        >>> d.attributes = [('method', 'acpioff')]
        >>> action = d.save_as_action()
        >>> action.category
        Category('start', 'http://schemas.ogf.org/occi/infrastructure/compute/action#')
        >>> action.parameters
        [('method', 'acpioff')]
        >>> d.attributes.append(('foo', 'bar'))
        >>> d.save_as_action()
        Traceback (most recent call last):
        Invalid: "foo": Unknown parameter
        """

        # Resolve category
        if len(self.categories) != 1:
            raise self.Invalid('Specify a single Category to identify an Action')
        if category_registry:
            try:
                category = category_registry.lookup_id(self.categories[0])
            except Category.DoesNotExist as e:
                raise self.Invalid(e)
        else:
            category = self.categories[0]

        # Create new Action instance
        try:
            action = Action(category, self.attributes)
        except Action.ActionError as e:
            raise self.Invalid(e)

        return action

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

class LocationTranslator(object):
    """Translates between Entity ID and Location URL"""
    def __init__(self, base_url):
        t = urlparse.urlparse(base_url.rstrip('/'))
        self.base_url = t.geturl()
        self.base_path = t.path.rstrip('/')

    def id2location(self, entity_id, path_only=False):
        if path_only:
            return '%s/%s' % (self.base_path, entity_id)
        return '%s/%s' % (self.base_url, entity_id)

    def location2id(self, location):
        i = 0
        if location.startswith(self.base_url):
            i = len(self.base_url)
        elif location.startswith(self.base_path):
            i = len(self.base_path)
        return location[i:].lstrip('/')

if __name__ == "__main__":
    import doctest
    doctest.testmod()
