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

    def __init__(self, term, scheme, title=None, related=None, attributes=None,
            entity_type=None, location=None):
        self.term = term
        self.scheme = scheme
        self.title = title
        self.related = related
        self.attributes = []
        self.unique_attributes = []
        self.entity_type = entity_type
        self.location = location

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
        self.entity_type = entity_type
        self.location = location

        if self.entity_type:
            self.entity_type.set_kind(self)

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

    # Unique Kind instance for this class. Automatically initialised by the
    # Kind class.
    __kind = None

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

    def __init__(self, categories=[], attributes=[], obj=None):
        self.categories = OrderedDict()
        self.attributes = {}
        self.obj = obj

        # Add type Category
        self.add_category(self._category)

        # Add additional Categories
        for category in categories:
            self.add_category(category)

        # Add attributes
        for attr, value in attributes:
            assert(attr not in self.attributes)
            self.attributes[attr] = value

    @classmethod
    def set_kind(cls, kind):
        """Set the identifying Kind"""
        assert(not cls.__kind)       # Must by set once only
        cls.__kind = kind

    @classmethod
    def get_kind(cls):
        """Get the identifying Kind"""
        assert(cls.__kind)
        return cls.__kind

    def add_category(self, category):
        # Resolve Category identifier
        cat_id = str(category)
        try:
            category = Category.find(cat_id)
        except Category.DoesNotExist:
            raise self.UnknownCategory(cat_id)

        # Category can only define this Entity type and no other
        if category.entity and category.entity != self.__class__:
            raise self.InvalidCategory('%s: type defining category mismatch (!= %s)' % (
                category, self._category))

        # Add Category if not already present
        if cat_id not in self.categories:
            self.categories[cat_id] = category

    def list_categories(self):
        #return self.categories.itervalues()
        return self.categories.values()

    def load_request_data(self, categories=[], attributes=[]):
        """Load request data into Entity object.
            categories - list of Category identifier strings
            attributes - list of (key, value) pairs where key is the attribute
                         name and value is a string
        """
        attr_dict = {}
        for attr, value in attributes:
            if attr in attr_dict:
                raise self.DuplicateAttribute(attr)
            attr_dict[attr] = value

        # Add categories
        for cat_id in categories:
            self.add_category(cat_id)

        # Add attributes
        for category in self.list_categories():
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
                    if attribute.mutable or (
                            attribute.required and attribute.name not in self.attributes):
                        # Convert and save new attibute value
                        self.attributes[attribute.name] = attribute.from_string(value)
                    else:
                        raise self.ImmutableAttribute(attribute.name)

                # Check required attribute
                if attribute.required and attribute.name not in self.attributes:
                    raise self.RequiredAttribute(attribute.name)

        # Verify all request attributes have been handled
        if attr_dict:
            raise self.UnknownAttribute(attr_dict.keys()[0])

    def dump_attributes(self):
        attr_list = []
        for category in self.list_categories():
            for attribute in category.attributes:
                try:
                    value = self.attributes[attribute.name]
                except KeyError:
                    pass
                else:
                    attr_list.append((attribute.name, attribute.to_string(value)))
        return attr_list

class Resource(Entity):
    def __init__(self, links=(), **kwargs):
        super(Resource, self).__init__(**kwargs)
        self.links = links

class Link(Entity):
    def __init__(self, target=None, **kwargs):
        super(Link, self).__init__(**kwargs)
        self.target = target

EntityKind = Kind('entity', 'http://schemas.ogf.org/occi/core#',
        title='Entity type',
        entity_type=Entity,
        attributes=(
            Attribute('id', required=False, mutable=False),
            Attribute('title', required=True, mutable=True),
        ),
)

ResourceKind = Kind('resource', 'http://schemas.ogf.org/occi/core#',
        related=EntityKind,
        title='Resource type',
        entity=Resource,
        attributes=(
            Attribute('summary', required=False, mutable=True),
        ),
)

LinkKind = Kind('link', 'http://schemas.ogf.org/occi/core#',
        related=EntityKind,
        title='Link type',
        entity=Link,
        attributes=(
            Attribute('source', required=True, mutable=False),
            Attribute('target', required=True, mutable=True),
        ),
)

ActionCategory = Category('action', 'http://schemas.ogf.org/occi/core#',
        title='Action')


