#
# Copyright (C) 2009-2011  Ralf Nyren <ralf@nyren.net>
# All rights reserved.
#

from ordereddict import OrderedDict

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

class Kind(Category):
    """The OCCI Kind type.

    A Kind instance uniquely identifies an Entity sub-type.
    """
    def __init__(self, term, scheme, actions=None, entity_type=None, location=None, **kwargs):
        super(Kind, self).__init__(term, scheme, **kwargs)
        self.actions = actions
        self.entity_type = entity_type or Entity
        self.location = location

        if self.related and not isinstance(self.related, Kind):
            raise Category.Invalid("Kind instance can only be related to other Kind instances")

class Mixin(Category):
    """The OCCI Mixin type.

    A Mixin instance adds additional capabilities (attributes and actions) to
    an existing resource instance. A 'resource instance' is an instance of a
    sub-type of Entity.
    """
    def __init__(self, term, scheme, actions=None, location=None, **kwargs):
        super(Mixin, self).__init__(term, scheme, **kwargs)
        self.actions = actions
        self.location = location

        if self.related and not isinstance(self.related, Mixin):
            raise Category.Invalid("Mixin instance can only be related to other Mixin instances")

class Action(object):
    """The OCCI Action type.

    An Action represents an invocable operation on a resource instance.
    """
    pass

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

        # Set the Kind of this resource instance
        if not kind or not isinstance(kind, Kind) or not kind.is_related(EntityKind):
            raise self.InvalidCategory(kind, 'not a valid Kind instance')
        self._occi_kind = kind

        # Add additional Mixins
        for mixin in mixins:
            self.add_occi_mixin(mixin)

    def get_occi_kind(self):
        return self._occi_kind

    def add_occi_mixin(self, mixin):
        cat_id = str(mixin)

        # Must be a Mixin type
        if not isinstance(mixin, Mixin):
            raise self.InvalidCategory(mixin, 'not a Mixin instance')

        # Save mixin
        self._occi_mixins[cat_id] = mixin

    def remove_occi_mixin(self, mixin):
        try:
            del self._occi_mixins[str(mixin)]
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

        >>> entity = Entity(ResourceKind)
        >>> attrs = [('summary', 'blah blah')]
        >>> entity.set_occi_attributes(attrs, validate=True)
        Traceback (most recent call last):
            File "core.py", line 273, in set_occi_attributes
                raise self.RequiredAttribute(attribute.name)
        RequiredAttribute: "title": Required attribute
        >>> attrs += [('title', 'A "tiny" resource instance')]
        >>> entity.set_occi_attributes(attrs, validate=True)
        >>> entity.get_occi_attributes(convert=True)
        [('title', 'A "tiny" resource instance'), ('summary', 'blah blah')]
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
