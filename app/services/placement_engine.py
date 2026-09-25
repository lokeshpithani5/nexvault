from typing import List
from app.models.storage_node import StorageNode
from app.models.policy import Policy
from app.core.exceptions import QuorumNotReachedError


class PlacementEngine:
    """Zone-aware replica placement engine balancing across failure domains."""

    @staticmethod
    def select_nodes_for_placement(
        available_nodes: List[StorageNode],
        policy: Policy,
    ) -> List[StorageNode]:
        rf = policy.replication_factor
        write_quorum = policy.min_write_quorum

        # Filter strictly healthy and reachable nodes
        healthy_nodes = [
            n for n in available_nodes
            if n.status == "HEALTHY" and not n.is_simulated_partitioned
        ]

        if len(healthy_nodes) < write_quorum:
            raise QuorumNotReachedError(
                message=f"Insufficient healthy nodes to satisfy write quorum. Needed {write_quorum}, available {len(healthy_nodes)}",
                details={"needed_quorum": write_quorum, "available_healthy": len(healthy_nodes)},
            )

        # Segregate into failure domains
        zone_a = [n for n in healthy_nodes if n.zone == "Zone-A"]
        zone_b = [n for n in healthy_nodes if n.zone == "Zone-B"]

        # Sort within zone by least used capacity
        zone_a.sort(key=lambda n: n.used_capacity_bytes)
        zone_b.sort(key=lambda n: n.used_capacity_bytes)

        selected: List[StorageNode] = []

        if rf == 3:
            # Optimal distribution: 2 in Zone A and 1 in Zone B, or 1 in Zone A and 2 in Zone B
            if len(zone_a) >= 2 and len(zone_b) >= 1:
                selected = [zone_a[0], zone_a[1], zone_b[0]]
            elif len(zone_b) >= 2 and len(zone_a) >= 1:
                selected = [zone_a[0], zone_b[0], zone_b[1]]
            elif len(zone_a) >= 1 and len(zone_b) >= 1:
                # Degraded distribution: 1 in A, 1 in B
                selected = [zone_a[0], zone_b[0]]
            else:
                # Fallback to whatever healthy nodes exist
                selected = healthy_nodes[:rf]
        elif rf == 2:
            # 1 in Zone A, 1 in Zone B
            if zone_a and zone_b:
                selected = [zone_a[0], zone_b[0]]
            else:
                selected = healthy_nodes[:rf]
        else:
            # General distribution
            idx_a, idx_b = 0, 0
            while len(selected) < rf and (idx_a < len(zone_a) or idx_b < len(zone_b)):
                if idx_a < len(zone_a) and len(selected) < rf:
                    selected.append(zone_a[idx_a])
                    idx_a += 1
                if idx_b < len(zone_b) and len(selected) < rf:
                    selected.append(zone_b[idx_b])
                    idx_b += 1

        if len(selected) < write_quorum:
            raise QuorumNotReachedError(
                message=f"Selected {len(selected)} nodes, below required write quorum of {write_quorum}",
                details={"selected": len(selected), "quorum": write_quorum},
            )

        return selected


placement_engine = PlacementEngine()
