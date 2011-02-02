from occi.core import (Category, Kind, Mixin, Resource, Link, ResourceKind,
        LinkKind, Attribute, IntAttribute, FloatAttribute)

ComputeStartActionCategory = Category('start', 'http://schemas.ogf.org/occi/infrastructure/compute/action#',
        title='Start Compute Resource')
ComputeStopActionCategory = Category('stop', 'http://schemas.ogf.org/occi/infrastructure/compute/action#',
        title='Stop Compute Resource')

ComputeKind = Kind('compute', 'http://schemas.ogf.org/occi/infrastructure#',
        title='Compute Resource',
        related=ResourceKind,
        entity_type=Resource,
        location='compute/',
        attributes=(
            Attribute('occi.compute.architecture', required=False, mutable=False),
            IntAttribute('occi.compute.cores', required=False, mutable=True),
            Attribute('occi.compute.hostname', required=False, mutable=True),
            FloatAttribute('occi.compute.speed', required=False, mutable=True),
            FloatAttribute('occi.compute.memory', required=False, mutable=True),
            Attribute('occi.compute.state', required=False, mutable=False),
        )
)

StorageKind = Kind('storage', 'http://schemas.ogf.org/occi/infrastructure#',
        title='Storage Resource',
        related=ResourceKind,
        entity_type=Resource,
        location='storage/',
        attributes=(
            FloatAttribute('occi.storage.size', required=True, mutable=True),
            Attribute('occi.storage.state', required=False, mutable=False),
        )
)

StorageLinkKind = Kind('storagelink', 'http://schemas.ogf.org/occi/infrastructure#',
        title='Storage Link', 
        related=LinkKind,
        entity_type=Link,
        location='link/storage/',
        attributes=(
            Attribute('occi.storagelink.deviceid', required=True, mutable=True),
            Attribute('occi.storagelink.mountpoint', required=False, mutable=True),
            Attribute('occi.storagelink.state', required=False, mutable=False),
        )
)
