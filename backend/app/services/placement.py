"""
Zone-Aware Replica Placement Engine
Distributes object chunks across failure domains (ZONE_A and ZONE_B).
Prevents placing all replicas in a single zone and load-balances across nodes.
"""

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.app.models.node import StorageNode


def determine_replica_placement(
    available_nodes: List[StorageNode],
    replication_factor: int = 3,
) -> List[StorageNode]:
    """
    Pure, independently testable placement function.
    Given a list of healthy candidate StorageNode instances:
    - Enforces failure domain distribution across ZONE_A and ZONE_B.
    - For RF=2: Exactly 1 from Zone A and 1 from Zone B (when cross-zone nodes available).
    - For RF=3: Spreads replicas across both zones (2 in Zone A + 1 in Zone B, or 1 in Zone A + 2 in Zone B).
    - Prioritizes nodes with lowest load (replica_count asc, used_bytes asc).
    """
    if len(available_nodes) <= replication_factor:
        return list(available_nodes)

    # Group by zone
    zone_a = [n for n in available_nodes if n.zone == "ZONE_A"]
    zone_b = [n for n in available_nodes if n.zone == "ZONE_B"]

    # Sort each zone by least load (replica_count asc, used_bytes asc, port asc for determinism)
    zone_a.sort(key=lambda n: (n.replica_count, n.used_bytes, n.port))
    zone_b.sort(key=lambda n: (n.replica_count, n.used_bytes, n.port))

    selected: List[StorageNode] = []

    if replication_factor == 1:
        # Choose the single least loaded node across both zones
        all_sorted = sorted(available_nodes, key=lambda n: (n.replica_count, n.used_bytes, n.port))
        return [all_sorted[0]]

    if replication_factor == 2:
        # Exactly 1 from Zone A and 1 from Zone B
        if zone_a and zone_b:
            selected.append(zone_a[0])
            selected.append(zone_b[0])
        else:
            fallback = sorted(available_nodes, key=lambda n: (n.replica_count, n.used_bytes, n.port))
            selected = fallback[:2]
        return selected

    if replication_factor == 3:
        # Cross-zone requirement: spread across both ZONE_A and ZONE_B.
        # Prefer 2 from the zone with lower total load, 1 from the other zone.
        total_replicas_a = sum(n.replica_count for n in zone_a)
        total_replicas_b = sum(n.replica_count for n in zone_b)

        if total_replicas_a <= total_replicas_b:
            # 2 from Zone A, 1 from Zone B
            if len(zone_a) >= 2 and len(zone_b) >= 1:
                selected.extend(zone_a[:2])
                selected.append(zone_b[0])
            elif len(zone_b) >= 2 and len(zone_a) >= 1:
                selected.append(zone_a[0])
                selected.extend(zone_b[:2])
            else:
                fallback = sorted(available_nodes, key=lambda n: (n.replica_count, n.used_bytes, n.port))
                selected = fallback[:3]
        else:
            # 2 from Zone B, 1 from Zone A
            if len(zone_b) >= 2 and len(zone_a) >= 1:
                selected.extend(zone_b[:2])
                selected.append(zone_a[0])
            elif len(zone_a) >= 2 and len(zone_b) >= 1:
                selected.extend(zone_a[:2])
                selected.append(zone_b[0])
            else:
                fallback = sorted(available_nodes, key=lambda n: (n.replica_count, n.used_bytes, n.port))
                selected = fallback[:3]
        return selected

    # Default round-robin between zones for RF > 3
    turn = 0
    idx_a = 0
    idx_b = 0
    while len(selected) < replication_factor and (idx_a < len(zone_a) or idx_b < len(zone_b)):
        if turn % 2 == 0 and idx_a < len(zone_a):
            selected.append(zone_a[idx_a])
            idx_a += 1
        elif idx_b < len(zone_b):
            selected.append(zone_b[idx_b])
            idx_b += 1
        elif idx_a < len(zone_a):
            selected.append(zone_a[idx_a])
            idx_a += 1
        turn += 1

    return selected


async def select_replica_nodes(
    db: AsyncSession,
    replication_factor: int = 3,
    exclude_node_ids: Optional[List[str]] = None,
) -> List[StorageNode]:
    """
    Queries DB for available healthy nodes and determines zone-aware placement.
    """
    exclude = set(exclude_node_ids or [])

    stmt = select(StorageNode).where(
        StorageNode.status.in_(["HEALTHY", "RECOVERING"]),
        StorageNode.is_simulated_partitioned == False,
    )
    result = await db.execute(stmt)
    nodes = result.scalars().all()

    # Filter out excluded nodes
    available_nodes = [n for n in nodes if n.id not in exclude]

    return determine_replica_placement(available_nodes, replication_factor=replication_factor)
