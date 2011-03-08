from occi.core import (Category, ExtCategory, Kind, Mixin, Resource, Link,
        ResourceKind, LinkKind, Attribute, IntAttribute, FloatAttribute)

#
# Compute Kind
# ============

ComputeStartActionCategory = Category('start', 'http://schemas.ogf.org/occi/infrastructure/compute/action#',
        title='Start Compute Resource',
        attributes=(
            Attribute('method', required=False, mutable=True),
        ))
ComputeStopActionCategory = Category('stop', 'http://schemas.ogf.org/occi/infrastructure/compute/action#',
        title='Stop Compute Resource',
        attributes=(
            Attribute('method', required=False, mutable=True),
        ))
ComputeRestartActionCategory = Category('restart', 'http://schemas.ogf.org/occi/infrastructure/compute/action#',
        title='Restart Compute Resource',
        attributes=(
            Attribute('method', required=False, mutable=True),
        ))
ComputeSuspendActionCategory = Category('suspend', 'http://schemas.ogf.org/occi/infrastructure/compute/action#',
        title='Suspend Compute Resource',
        attributes=(
            Attribute('method', required=False, mutable=True),
        ))

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
        ),
        actions=(
            ComputeStartActionCategory,
            ComputeStopActionCategory,
            ComputeRestartActionCategory,
            ComputeSuspendActionCategory,
        ),
)

#
# Network Kind
# ============

NetworkUpActionCategory = Category('up', 'http://schemas.ogf.org/occi/infrastructure/network/action#',
        title='Bring up Network Resource')
NetworkDownActionCategory = Category('down', 'http://schemas.ogf.org/occi/infrastructure/network/action#',
        title='Take down Network Resource')

NetworkKind = Kind('network', 'http://schemas.ogf.org/occi/infrastructure#',
        title='Network Resource',
        related=ResourceKind,
        entity_type=Resource,
        location='network/',
        attributes=(
            IntAttribute('occi.network.vlan', required=False, mutable=True),
            Attribute('occi.network.label', required=False, mutable=True),
            Attribute('occi.network.state', required=False, mutable=False),
        ),
        actions=(
            NetworkUpActionCategory,
            NetworkDownActionCategory,
        ),
)

#
# IPNetwork Mixin
# ===============

IPNetworkMixin = Mixin('ipnetwork', 'http://schemas.ogf.org/occi/infrastructure/network#',
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

StorageOnlineActionCategory = Category('online',
        'http://schemas.ogf.org/occi/infrastructure/storage/action#',
        title='Bring Storage Resource online')
StorageOfflineActionCategory = Category('offline',
        'http://schemas.ogf.org/occi/infrastructure/storage/action#',
        title='Bring Storage Resource offline')
StorageBackupActionCategory = Category('backup',
        'http://schemas.ogf.org/occi/infrastructure/storage/action#',
        title='Backup Storage Resource')
StorageSnapshotActionCategory = Category('snapshot',
        'http://schemas.ogf.org/occi/infrastructure/storage/action#',
        title='Take snapshot of Storage Resource')
StorageResizeActionCategory = Category('resize',
        'http://schemas.ogf.org/occi/infrastructure/storage/action#',
        title='Resize Storage Resource',
        attributes=(
            Attribute('size', required=True, mutable=True),
        ))

StorageKind = Kind('storage', 'http://schemas.ogf.org/occi/infrastructure#',
        title='Storage Resource',
        related=ResourceKind,
        entity_type=Resource,
        location='storage/',
        attributes=(
            FloatAttribute('occi.storage.size', required=True, mutable=True),
            Attribute('occi.storage.state', required=False, mutable=False),
        ),
        actions=(
            StorageOnlineActionCategory,
            StorageOfflineActionCategory,
            StorageBackupActionCategory,
            StorageSnapshotActionCategory,
            StorageResizeActionCategory,
        ),
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
            Attribute('occi.networkinterface.interface', required=False, mutable=True),
            Attribute('occi.networkinterface.mac', required=False, mutable=True),
            Attribute('occi.networkinterface.state', required=False, mutable=False),
        )
)

#
# IPNetworkInterface Mixin
# ========================

IPNetworkInterfaceMixin = Mixin('ipnetworkinterface', 'http://schemas.ogf.org/occi/infrastructure#',
        title='IPNetworkInterface Link',
        location='link/ipnetworkinterface/',
        attributes=(
            Attribute('occi.networkinterface.ip', required=False, mutable=True),
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
