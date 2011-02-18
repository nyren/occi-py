#
# Copyright (C) 2009-2011  Ralf Nyren <ralf@nyren.net>
# All rights reserved.
#

try:
    from ordereddict import OrderedDict
except ImportError:
    OrderedDict = dict

class Attribute(object):
    class Invalid(Exception):
        def __init__(self, name, value):
            self.name = name
            self.value = value

        def __str__(self):
            return "%s='%s': invalid attribute value" % (self.name, self.value)

    def __init__(self, name, required=True, mutable=False):
        self.name = name
        self.required = required
        self.mutable = mutable

    def from_string(self, s):
        return s

    def to_string(self, v):
        return str(v)

    def __repr__(self):
        return "%s('%s', required=%s, mutable=%s)" % (self.__class__.__name__, self.name, self.required, self.mutable)

class IntAttribute(Attribute):
    def from_string(self, s):
        try:
            return int(s)
        except ValueError:
            raise self.Invalid(self.name, s)

class FloatAttribute(Attribute):
    def from_string(self, s):
        try:
            return float(s)
        except ValueError:
            raise self.Invalid(self.name, s)

    def to_string(self, v):
        return '%.2f' % v

class BoolAttribute(Attribute):
    def from_string(self, s):
        if s == 'y':
            return True
        elif s == 'n':
            return False
        else:
            raise self.Invalid(self.name, s)

    def to_string(self, value):
        if value:
            return 'y'
        return 'n'

class Category(object):
    """The OCCI Category type."""

    class CategoryError(Exception):
        pass
    class Invalid(CategoryError):
        pass
    class DoesNotExist(CategoryError):
        pass

    def __init__(self, term, scheme, title=None, related=None, attributes=None):
        self.term = term
        self.scheme = scheme
        self.title = title
        self.related = related
        self.attributes = []
        self.unique_attributes = []

        # Attributes
        if related:
            self.attributes.extend(related.attributes)
        if attributes:
            self.attributes.extend(attributes)
            self.unique_attributes = attributes

    def __repr__(self):
        return "%s('%s', '%s')" % (self.__class__.__name__, self.term, self.scheme)

    def __str__(self):
        return self.scheme + self.term

    def __cmp__(self, other):
        return cmp(str(self), str(other))

    def is_related(self, category):
        current = self
        while current:
            if category == current:
                return True
            current = current.related
        return False

class CategoryRegistry(object):
    """Registry of all Category/Kind/Mixin instances currently known to the
    OCCI server or client.

    >>> reg = CategoryRegistry()
    >>> from occi.core import Category, ExtCategory, Kind, Mixin
    >>> from occi.ext.infrastructure import *
    >>> reg.register(ComputeKind)
    >>> reg.register(StorageKind)
    >>> reg.register(StorageLinkKind)
    >>> fooKind = Kind('foo', 'http://#', related=ResourceKind, location='compute/')
    >>> reg.register(fooKind)
    Traceback (most recent call last):
    Invalid: compute/: location path already defined
    >>> reg.lookup_id(ComputeKind)
    Kind('compute', 'http://schemas.ogf.org/occi/infrastructure#')
    >>> reg.lookup_location('storage/')
    Kind('storage', 'http://schemas.ogf.org/occi/infrastructure#')
    >>> reg.unregister(StorageKind)
    >>> reg.unregister(ComputeKind)
    >>> reg.unregister(EntityKind) ; reg.unregister(ResourceKind) ; reg.unregister(LinkKind)
    >>> reg.all()
    [Kind('storagelink', 'http://schemas.ogf.org/occi/infrastructure#')]

    """

    def __init__(self):
        self._categories = OrderedDict()
        self._locations = {}

        # Always register OCCI Core types
        self.register(EntityKind)
        self.register(ResourceKind)
        self.register(LinkKind)

    def register(self, category):
        """Register a new Category/Kind/Mixin."""
        s = str(category)
        if s in self._categories:
            self.unregister(s)

        # Location
        if hasattr(category, 'location') and category.location:
            if category.location in self._locations:
                raise Category.Invalid('%s: location path already defined' % category.location)
            self._locations[category.location] = category

        # Register category
        self._categories[s] = category

        # Register actions
        if hasattr(category, 'actions'):
            for action in category.actions:
                if hasattr(action, 'actions'):
                    raise Category.Invalid(
                            '%s: Only the base Category type allowed to identify Actions' % action)
                self.register(action)

    def unregister(self, category):
        """Unregister a previously registered Category/Kind/Mixin."""
        try:
            category = self._categories[str(category)]
        except KeyError:
            raise Category.Invalid("%s: Category not registered" % category)

        # Unregister category
        del self._categories[str(category)]

        # Remove location entry
        if hasattr(category, 'location') and category.location:
            self._locations.pop(category.location, None)

        # Remove additional action categories
        if hasattr(category, 'actions'):
            for action in category.actions:
                self.unregister(action)

    def lookup_id(self, identifier):
        try:
            return self._categories[str(identifier)]
        except KeyError:
            raise Category.DoesNotExist('"%s": Category does not exist' % identifier)

    def lookup_location(self, path):
        loc = path.lstrip('/')
        return self._locations.get(loc)

    def all(self):
        return self._categories.values()

class ExtCategory(Category):
    def __init__(self, term, scheme, actions=None, location=None, **kwargs):
        super(ExtCategory, self).__init__(term, scheme, **kwargs)
        self._location = None
        self.actions = actions or ()
        self.location = location

    def get_location(self):
        return self._location
    def set_location(self, loc):
        if not loc:
            loc = None
        elif loc[-1] != '/':
            raise Category.Invalid("%s: invalid location path, must end with '/'" % loc)
        else:
            loc = loc.lstrip('/')
        if not loc:
            loc = None
        self._location = loc
    location = property(get_location, set_location)

class Kind(ExtCategory):
    """The OCCI Kind type.

    A Kind instance uniquely identifies an Entity sub-type.
    """
    def __init__(self, term, scheme, entity_type=None, **kwargs):
        super(Kind, self).__init__(term, scheme, **kwargs)
        self.entity_type = entity_type or Entity

        if self.related and not isinstance(self.related, Kind):
            raise Category.Invalid("Kind instance can only be related to other Kind instances")

class Mixin(ExtCategory):
    """The OCCI Mixin type.

    A Mixin instance adds additional capabilities (attributes and actions) to
    an existing resource instance. A 'resource instance' is an instance of a
    sub-type of Entity.
    """
    def __init__(self, term, scheme, **kwargs):
        super(Mixin, self).__init__(term, scheme, **kwargs)

        if self.related and not isinstance(self.related, Mixin):
            raise Category.Invalid("Mixin instance can only be related to other Mixin instances")

class Action(object):
    """The OCCI Action type.

    An instance of Action represents a operation (on a resource instance) to be
    invoked. An Action instance consist of its defining Category and a set of
    attribute (parameter) values. The available parameters are defined by the Category.

    >>> startAction = Category('start', 'http://example.com/occi/foo/action#', attributes=[Attribute('example.com.bar', required=True)])
    >>> action = Action(startAction, parameters=[('example.com.bar', 'foobar')])
    >>> action.parameters
    [('example.com.bar', 'foobar')]
    >>> action = Action(startAction, parameters=[('example.com.unknown', 'blah'), ('example.com.bar', 'foobar')])
    Traceback (most recent call last):
    UnknownParameter: "example.com.unknown": Unknown parameter
    >>> action = Action(startAction, parameters=[('example.com.unknown', 'blah')])
    Traceback (most recent call last):
    RequiredParameter: "example.com.bar": Required parameter
    """

    class ActionError(Exception):
        def __init__(self, item=None, message=None):
            self.item = item
            self.message = message
        def __str__(self):
            s = ''
            if self.item:
                s += '"%s": ' % self.item
            if hasattr(self, '_name'):
                s += self._name
            else:
                s += self.__class__.__name__
            if self.message:
                s += ': %s' % self.message
            return s
    class UnknownParameter(ActionError):
        _name = 'Unknown parameter'
    class RequiredParameter(ActionError):
        _name = 'Required parameter'

    def __init__(self, category, parameters=None):
        """Setup Action instance given its defining Category and a list of
        parameter values.

        :param category: Category instance defining the Action.
        :keyword parameters: List of parameter name-value pairs.
        """
        self._occi_category = category
        self._occi_parameters = {}

        # Load supplied parameters into a dictionary
        param_dict = {}
        for param, value in parameters or ():
            if param in param_dict:
                raise self.DuplicateAttribute(param)
            param_dict[param] = value

        # Setup the parameters for the Action instance
        for attribute in self._occi_category.attributes:
            try:
                value = param_dict[attribute.name]
                del param_dict[attribute.name]
            except KeyError:
                pass
            else:
                self._occi_parameters[attribute.name] = attribute.from_string(value)

            # Check required parameters
            if attribute.required and attribute.name not in self._occi_parameters:
                raise self.RequiredParameter(attribute.name)

        # Verify all supplied attributes have been handled
        if param_dict:
            raise self.UnknownParameter(param_dict.keys()[0])

    def _get_occi_category(self):
        return self._occi_category
    category = property(_get_occi_category)

    def _get_occi_parameters(self):
        params = []
        for attribute in self._occi_category.attributes:
            try:
                params.append((attribute.name, self._occi_parameters[attribute.name]))
            except KeyError:
                pass
        return params
    parameters = property(_get_occi_parameters)


class Entity(object):
    """The OCCI Entity (abstract) type.

    The abstract Entity type is inherited by the Resource and Link types. The
    Entity type and any sub-type thereof MUST have its own unique identifying
    Kind instance.

    A 'resource instance' is an instance of a sub-type of Entity.
    """

    class EntityError(Exception):
        def __init__(self, item=None, message=None):
            self.item = item
            self.message = message
        def __str__(self):
            s = ''
            if self.item:
                s += '"%s": ' % self.item
            if hasattr(self, '_name'):
                s += self._name
            else:
                s += self.__class__.__name__
            if self.message:
                s += ': %s' % self.message
            return s
    class DoesNotExist(EntityError):
        _name = 'Resource instance does not exist'
    class UnknownCategory(EntityError):
        _name = 'Unknown Category'
    class InvalidCategory(EntityError):
        _name = 'Invalid Category'
    class UnknownAttribute(EntityError):
        _name = 'Unknown attribute'
    class DuplicateAttribute(EntityError):
        _name = 'Duplicate attribute'
    class ImmutableAttribute(EntityError):
        _name = 'Immutable attribute'
    class RequiredAttribute(EntityError):
        _name = 'Required attribute'

    def __init__(self, kind, mixins=[]):
        self.id = None
        self._occi_kind = None
        self._occi_mixins = {}
        self._occi_attributes = {}
        self._occi_actions_available = {}
        self._occi_actions_applicable = {}

        # Set the Kind of this resource instance
        if not kind or not isinstance(kind, Kind) or not kind.is_related(EntityKind):
            raise self.InvalidCategory(kind, 'not a valid Kind instance')
        self._occi_kind = kind
        self._add_actions_available(kind.actions)

        # Add additional Mixins
        for mixin in mixins:
            self.add_occi_mixin(mixin)

    def _add_actions_available(self, actions=[]):
        for category in actions:
            cat_id = str(category)
            self._occi_actions_available[cat_id] = category

    def _remove_actions_available(self, actions=[]):
        for category in actions:
            cat_id = str(category)
            self._occi_actions_available.pop(cat_id, None)
            self._occi_actions_applicable.pop(cat_id, None)

    def get_occi_kind(self):
        return self._occi_kind

    def add_occi_mixin(self, mixin):
        cat_id = str(mixin)

        # Must be a Mixin type
        if not isinstance(mixin, Mixin):
            raise self.InvalidCategory(mixin, 'not a Mixin instance')

        # Save mixin
        self._occi_mixins[cat_id] = mixin
        self._add_actions_available(mixin.actions)

    def remove_occi_mixin(self, mixin):
        try:
            mixin = self._occi_mixins.pop(str(mixin))
            self._remove_actions_available(mixin.actions)
        except KeyError:
            raise self.UnknownCategory(mixin, 'not found')

    def list_occi_categories(self):
        return [self._occi_kind] + self._occi_mixins.values()

    def get_occi_attribute(self, name):
        """Get single OCCI attribute value."""
        return self._occi_attributes.get(name)

    def get_occi_attributes(self, convert=False, exclude=()):
        """Get list of OCCI attribute key-value pairs.

        Optionally convert to attribute value from OCCI native format to a
        string.
        """
        attr_list = []
        for category in self.list_occi_categories():
            for attribute in category.attributes:
                if attribute.name in exclude:
                    continue
                try:
                    value = self._occi_attributes[attribute.name]
                except KeyError:
                    pass
                else:
                    if convert:
                        value = attribute.to_string(value)
                    attr_list.append((attribute.name, value))
        return attr_list

    def set_occi_attributes(self, attr_list, validate=True):
        """Set the values of the OCCI attributes defined for this resource
        instance.

        :param attr_list: List of key-value tuples
        :param validate: Boolean whether to validate the attribute set

        >>> fooKind = Kind('foo', 'http://example.com/occi#', title='Foo', related=ResourceKind, attributes=[Attribute('com.example.bar', required=True, mutable=True)])
        >>> entity = Entity(fooKind)
        >>> attrs = [('summary', 'blah blah')]
        >>> entity.set_occi_attributes(attrs, validate=True)
        Traceback (most recent call last):
            File "core.py", line 362, in set_occi_attributes
                raise self.RequiredAttribute(attribute.name)
        RequiredAttribute: "com.example.bar": Required attribute
        >>> attrs += [('title', 'A "tiny" resource instance')]
        >>> attrs += [('com.example.bar', 'Bar')]
        >>> entity.set_occi_attributes(attrs, validate=True)
        >>> entity.get_occi_attributes(convert=True)
        [('title', 'A "tiny" resource instance'), ('summary', 'blah blah'), ('com.example.bar', 'Bar')]
        >>> attrs += [('summary', 'duplicate')]
        >>> entity.set_occi_attributes(attrs, validate=True)
        Traceback (most recent call last):
            File "core.py", line 256, in set_occi_attributes
                raise self.DuplicateAttribute(attr)
        DuplicateAttribute: "summary": Duplicate attribute

        """
        # Load supplied attributes into a dictionary
        attr_dict = {}
        for attr, value in attr_list:
            if attr in attr_dict:
                raise self.DuplicateAttribute(attr)
            attr_dict[attr] = value

        # Add attributes to the Entity instance
        for category in self.list_occi_categories():
            for attribute in category.attributes:
                try:
                    value = attr_dict[attribute.name]
                    del attr_dict[attribute.name]
                except KeyError:
                    pass
                else:
                    # Attribute mutable if:
                    #  - attribute.mutable == True
                    #  - attribute.required == True and attribute.mutable == False and attribute not yet specified (write once)
                    if not validate or attribute.mutable or (
                            attribute.required and attribute.name not in self._occi_attributes):
                        # Convert and save new attibute value
                        self._occi_attributes[attribute.name] = attribute.from_string(value)
                    else:
                        raise self.ImmutableAttribute(attribute.name)

                # Check required attribute
                if validate and attribute.required and attribute.name not in self._occi_attributes:
                    raise self.RequiredAttribute(attribute.name)

        # Verify all supplied attributes have been handled
        if attr_dict:
            raise self.UnknownAttribute(attr_dict.keys()[0])

    def occi_list_actions(self):
        """Return a list of Category instances which define the Actions
        _available_ to this resource instance.
        """
        return self._occi_actions_available.values()

    def occi_list_applicable_actions(self):
        """Return a list of Category instances which define the Actions
        currently _applicable_ to this resource instance.
        """
        return [self._occi_actions_available[cat_id] for cat_id in self._occi_actions_applicable.keys()]

    def occi_is_applicable_action(self, action_category):
        """Return whether the given Category instance correspond to a currently
        applicable Action.
        """
        cat_id = str(action_category)
        return cat_id in self._occi_actions_applicable and cat_id in self._occi_actions_available

    def occi_set_applicable_action(self, action_category, applicable=True):
        """Set 'applicable' state of an action. By default all actions defined
        for a resource instance are non-applicable.

        :param action_category: The Category instance defining the Action.
        :keyword applicable: Boolean, whether action is currently applicable or not.

        >>> startAction = Category('start', 'http://example.com/occi/foo/action#')
        >>> fooKind = Kind('foo', 'http://example.com/occi#', title='Foo', related=ResourceKind, attributes=[Attribute('com.example.bar', required=True, mutable=True)], actions=[startAction])
        >>> entity = Entity(fooKind)
        >>> entity.occi_list_actions()
        [Category('start', 'http://example.com/occi/foo/action#')]
        >>> entity.occi_list_applicable_actions()
        []
        >>> entity.occi_is_applicable_action(startAction)
        False
        >>> entity.occi_set_applicable_action(startAction)
        >>> entity.occi_is_applicable_action(startAction)
        True
        >>> entity.occi_list_applicable_actions()
        [Category('start', 'http://example.com/occi/foo/action#')]
        >>> stopAction = Category('stop', 'http://example.com/occi/foo/action#')
        >>> entity.occi_is_applicable_action(stopAction)
        False
        >>> entity.occi_set_applicable_action(stopAction)
        Traceback (most recent call last):
        UnknownCategory: "http://example.com/occi/foo/action#stop": Unknown Category: Action not defined for this resource instance

        """
        cat_id = str(action_category)
        if cat_id not in self._occi_actions_available:
            raise self.UnknownCategory(cat_id, 'Action not defined for this resource instance')
        if applicable:
            self._occi_actions_applicable[cat_id] = True
        else:
            self._occi_actions_applicable.pop(cat_id, None)

class Resource(Entity):
    def __init__(self, kind, links=None, **kwargs):
        super(Resource, self).__init__(kind, **kwargs)
        self.links = links or []

class Link(Entity):
    def __init__(self, kind, target=None, **kwargs):
        super(Link, self).__init__(kind, **kwargs)
        self.target = target

EntityKind = Kind('entity', 'http://schemas.ogf.org/occi/core#',
        title='Entity type',
        entity_type=Entity,
        attributes=(
            Attribute('title', required=False, mutable=True),
        ),
)

ResourceKind = Kind('resource', 'http://schemas.ogf.org/occi/core#',
        related=EntityKind,
        title='Resource type',
        entity_type=Resource,
        attributes=(
            Attribute('summary', required=False, mutable=True),
        ),
)

LinkKind = Kind('link', 'http://schemas.ogf.org/occi/core#',
        related=EntityKind,
        title='Link type',
        entity_type=Link,
        attributes=(
            Attribute('source', required=True, mutable=False),
            Attribute('target', required=True, mutable=True),
        ),
)

ActionCategory = Category('action', 'http://schemas.ogf.org/occi/core#',
        title='Action')


if __name__ == "__main__":
    import doctest
    doctest.testmod()
