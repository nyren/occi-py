#
# Copyright (C) 2010-2011  Ralf Nyren <ralf@nyren.net>
#
# This file is part of the occi-py library.
#
# The occi-py library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# The occi-py library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with the occi-py library.  If not, see <http://www.gnu.org/licenses/>.
#

import urlparse
import uuid

from occi.core import Attribute, Category, Kind, Mixin, Entity, Resource, Link, Action, EntityTranslator, EntityKind

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
            actions=None, location=None, translator=None):
        self.categories = categories or []
        self.links = links or []
        self.actions = actions or []
        self.attributes = attributes or []
        self.location = location

        self.translator = translator or URLTranslator('')
        self.parse_flags = {}
        self.render_flags = {}

    def load_from_entity(self, entity):
        """Load `DataObject` with the contents of the specified Entity instance.

        >>> from occi.ext.infrastructure import *
        >>> compute = ComputeKind.entity_type(ComputeKind)
        >>> compute.occi_import_attributes([('occi.core.id', '10000000-0000-4000-0000-000000000000'), ('occi.compute.speed', 7.0/3)], validate=False)
        >>> compute.occi_set_applicable_action(ComputeStartActionCategory)
        >>> storage = StorageKind.entity_type(StorageKind)
        >>> storage.occi_import_attributes([('occi.core.id', '20000000-0000-4000-0000-000000000000'), ('occi.core.title', 'My Disk')], validate=False)
        >>> link = StorageLinkKind.entity_type(StorageLinkKind)
        >>> link.occi_import_attributes([('occi.core.id', '30000000-0000-4000-0000-000000000000'), ('occi.storagelink.deviceid', 'ide:0:1')], validate=False)
        >>> link.occi_set_attribute('occi.core.source', compute)
        >>> link.occi_set_attribute('occi.core.target', storage)
        >>> compute.links.append(link)
        >>> d = DataObject(translator=URLTranslator('/api/'))
        >>> d.load_from_entity(compute)
        >>> d.location
        '/api/compute/10000000-0000-4000-0000-000000000000'
        >>> d.categories
        [Kind('compute', 'http://schemas.ogf.org/occi/infrastructure#')]
        >>> d.attributes
        [('occi.core.id', 'urn:uuid:10000000-0000-4000-0000-000000000000'), ('occi.compute.speed', 2.3333333333333335)]
        >>> [(l.target_location, l.target_categories, l.target_title) for l in d.links]
        [('/api/storage/20000000-0000-4000-0000-000000000000', [Kind('storage', 'http://schemas.ogf.org/occi/infrastructure#')], 'My Disk')]
        >>> [(l.link_location, l.link_categories, l.link_attributes) for l in d.links]
        [('/api/link/storage/30000000-0000-4000-0000-000000000000', [Kind('storagelink', 'http://schemas.ogf.org/occi/infrastructure#')], [('occi.storagelink.deviceid', 'ide:0:1')])]
        >>> [(a.target_location, a.target_categories, a.target_title) for a in d.actions]
        [('/api/compute/10000000-0000-4000-0000-000000000000?action=start', [Category('start', 'http://schemas.ogf.org/occi/infrastructure/compute/action#')], 'Start Compute Resource')]

        """
        # Set location translator for Entity instance
        entity.occi_set_translator(self.translator)

        # Get Entity Kind, Mixins, Attributes and ID
        self.categories = entity.occi_list_categories()
        self.attributes = entity.occi_export_attributes(convert=True)
        self.location = self.translator.from_native(entity)

        # Links
        if isinstance(entity, Resource):
            for link in entity.links:
                link.occi_set_translator(self.translator)
                target = link.occi_get_attribute('occi.core.target')
                if not target:
                    # Ignore incomplet Link object
                    print "%s: occi.core.target not defined" % link.id
                    continue
                l = LinkRepr(
                        target_location=link.occi_get_attribute('occi.core.target', convert=True),
                        target_categories=target.occi_list_categories(),
                        target_title=target.occi_get_attribute('occi.core.title'),
                        link_location=self.translator.from_native(link))
                link_attributes = link.occi_export_attributes(convert=True,
                        exclude=('occi.core.id', 'occi.core.source', 'occi.core.target'))
                if link_attributes:
                    l.link_categories = link.occi_list_categories()
                    l.link_attributes = link_attributes

                self.links.append(l)

        # Actions
        for action in entity.occi_list_applicable_actions():
            l = LinkRepr(
                    target_location='%s?action=%s' % (
                        self.translator.from_native(entity, path_only=True),
                        action.term),
                    target_categories=[action],
                    target_title=action.title)
            self.actions.append(l)

    def save_to_entity(self, entity=None, category_registry=None,
            validate_attr=True, save_links=False):
        """Save the `DataObject` contents into an Entity instance.

        >>> from occi.ext.infrastructure import *
        >>> d = DataObject(translator=URLTranslator('/api'))
        >>> d.location = '/api/compute/10000000-0000-4000-0000-000000000000'
        >>> d.categories = [ComputeKind]
        >>> d.attributes = [('occi.compute.speed', '2.33')]
        >>> l = LinkRepr(target_location='/api/storage/20000000-0000-4000-0000-000000000000', target_categories=[StorageKind])
        >>> l.link_location = '/api/link/storage/30000000-0000-4000-0000-000000000000'
        >>> l.link_categories = [StorageLinkKind]
        >>> l.link_attributes = [('occi.storagelink.deviceid', 'ide:0:1')]
        >>> d.links.append(l)
        >>> entity = d.save_to_entity(save_links=True)
        >>> entity.occi_list_categories()
        [Kind('compute', 'http://schemas.ogf.org/occi/infrastructure#')]
        >>> round(entity.occi_get_attribute('occi.compute.speed')*1000)
        2330.0
        >>> entity.links[0].occi_list_categories()
        [Kind('storagelink', 'http://schemas.ogf.org/occi/infrastructure#')]
        >>> attr = entity.links[0].occi_export_attributes(convert=False)
        >>> attr[0]
        ('occi.core.id', UUID('30000000-0000-4000-0000-000000000000'))
        >>> attr[1][0]
        'occi.core.source'
        >>> attr[1][1].id
        UUID('10000000-0000-4000-0000-000000000000')
        >>> attr[2][0]
        'occi.core.target'
        >>> attr[2][1].id
        UUID('20000000-0000-4000-0000-000000000000')
        >>> attr[3:]
        [('occi.storagelink.deviceid', 'ide:0:1')]
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
            entity = kind.entity_type(kind, mixins=mixins)
        else:
            if kind and str(kind) != str(entity.occi_get_kind()):
                raise self.Invalid('Cannot change Kind of existing Entity')
            [entity.occi_add_mixin(mixin) for mixin in mixins]

        # Set location translator for Entity instance
        entity.occi_set_translator(self.translator)

        # Load attributes
        try:
            entity.occi_import_attributes(self.attributes, validate=validate_attr)
        except (Entity.EntityError, Attribute.Invalid) as e:
            raise self.Invalid(e)

        # Load Link relations
        if save_links and self.links:
            if not isinstance(entity, Resource):
                raise self.Invalid('Links only applicable to the Resource type')
            for link_repr in self.links:
                # Initialise Link instance
                try:
                    l_kind, l_mixins = self._resolve_categories(
                            link_repr.link_categories, category_registry)
                except self.Invalid:
                    l_kind = LinkKind
                    l_mixins = []
                link = l_kind.entity_type(l_kind, mixins=l_mixins)
                link.occi_set_translator(self.translator)
                if not isinstance(link, Link):
                    raise self.Invalid('Relation must be a Link type')
                default_attr = [
                        ('occi.core.source', self.location),
                        ('occi.core.target', link_repr.target_location)
                ]
                if link_repr.link_location:
                        link.occi_import_attributes(
                                [('occi.core.id', link_repr.link_location)],
                                validate=False)
                link.occi_import_attributes(
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
                if kind is not None and str(kind) != str(category):
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

class URLTranslator(EntityTranslator):
    """Translates between Entity ID and Location URL

    >>> from occi.ext.infrastructure import *
    >>> translator = URLTranslator('http://example.com/api/')
    >>> compute = ComputeKind.entity_type(ComputeKind)
    >>> compute.occi_import_attributes([('occi.core.id', '10000000-0000-4000-0000-000000000000'), ('occi.compute.cores', 4)], validate=False)
    >>> s = translator.from_native(compute)
    >>> s
    'http://example.com/api/compute/10000000-0000-4000-0000-000000000000'
    >>> entity = translator.to_native(s)
    >>> entity.id
    UUID('10000000-0000-4000-0000-000000000000')
    >>> entity.occi_list_categories()
    [Kind('entity', 'http://schemas.ogf.org/occi/core#')]
    """
    def __init__(self, base_url):
        t = urlparse.urlparse(base_url.rstrip('/'))
        self.base_url = t.geturl()
        self.base_path = t.path.rstrip('/')

    def url_build(self, s, path_only=False):
        if path_only:
            return '%s/%s' % (self.base_path, s)
        return '%s/%s' % (self.base_url, s)

    def url_strip(self, url):
       i = 0
       if url.startswith(self.base_url):
           i = len(self.base_url)
       elif url.startswith(self.base_path):
           i = len(self.base_path)
       return url[i:].lstrip('/')

    def from_native(self, entity, path_only=False):
        s = str(entity.id)
        kind = entity.occi_get_kind()
        if hasattr(kind, 'location') and kind.location:
            s = kind.location + s
        return self.url_build(s, path_only=path_only)

    def to_native(self, location):
        entity_id = None
        location = str(location)
        i = location.rfind('/')
        if i + 1 < len(location):
            entity_id = location[i+1:]
        entity = Entity(EntityKind)
        entity.occi_import_attributes([('occi.core.id', entity_id)], validate=False)
        return entity

if __name__ == "__main__":
    import doctest
    doctest.testmod()
