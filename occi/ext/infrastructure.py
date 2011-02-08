from occi.core import (Category, Kind, Mixin, Resource, Link, ResourceKind,
        LinkKind, Attribute, IntAttribute, FloatAttribute)

#
# Compute Kind
# ============

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

ComputeStartActionCategory = Category('start', 'http://schemas.ogf.org/occi/infrastructure/compute/action#',
        title='Start Compute Resource')
ComputeStopActionCategory = Category('stop', 'http://schemas.ogf.org/occi/infrastructure/compute/action#',
        title='Stop Compute Resource')

#
# Network Kind
# ============

NetworkKind = Kind('network', 'http://schemas.ogf.org/occi/infrastructure#',
        title='Network Resource',
        related=ResourceKind,
        entity_type=Resource,
        location='network/',
        attributes=(
            IntAttribute('occi.network.vlan', required=False, mutable=True),
            Attribute('occi.network.vlan', required=False, mutable=True),
            Attribute('occi.network.state', required=False, mutable=False),
        )
)

#
# IPNetwork Mixin
# ===============

NetworkKind = Mixin('ipnetwork', 'http://schemas.ogf.org/occi/infrastructure#',
        title='IPNetworking Mixin',
        location='ipnetwork/',
        attributes=(
            Attribute('occi.network.address', required=False, mutable=True),
            Attribute('occi.network.gateway', required=False, mutable=True),
            Attribute('occi.network.allocation', required=False, mutable=True),
        )
)

#
# Storage Kind
# ============

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

#
# NetworkInterface Kind
# =====================

NetworkInterfaceKind = Kind('networkinterface', 'http://schemas.ogf.org/occi/infrastructure#',
        title='NetworkInterface Link',
        related=LinkKind,
        entity_type=Link,
        location='link/networkinterface/',
        attributes=(
            Attribute('occi.networkinterface.interface', required=True, mutable=True),
            Attribute('occi.networkinterface.mac', required=True, mutable=True),
            Attribute('occi.networkinterface.state', required=False, mutable=False),
        )
)

#
# IPNetworkInterface Mixin
# ========================

NetworkInterfaceKind = Mixin('ipnetworkinterface', 'http://schemas.ogf.org/occi/infrastructure#',
        title='IPNetworkInterface Link',
        location='link/ipnetworkinterface/',
        attributes=(
            Attribute('occi.networkinterface.address', required=True, mutable=True),
            Attribute('occi.networkinterface.gateway', required=False, mutable=True),
            Attribute('occi.networkinterface.allocation', required=True, mutable=True),
        )
)
#
# Storage Kind
# ============

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
