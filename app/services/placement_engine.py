from typing import List, Tuple
from app.models.storage_node import StorageNode
from app.models.policy import Policy
from app.core.exceptions import QuorumNotReachedError
from app.core.logging_config import logger


class PlacementEngine:
    """Zone-aware replica placement engine balancing across failure domains and enforcing durability/availability policies."""

    @staticmethod
    def select_nodes_for_placement(
        available_nodes: List[StorageNode],
        policy: Policy,
    ) -> Tuple[List[StorageNode], bool]:
        """
        Selects nodes across failure zones.
        Returns: (selected_nodes, is_degraded)
        """
        rf = policy.replication_factor
        write_quorum = policy.min_write_quorum
        avail_mode = getattr(policy, "availability_mode", "DURABILITY_FIRST")

        # Filter strictly healthy and non-partitioned nodes
        healthy_nodes = [
            n for n in available_nodes
            if n.status == "HEALTHY" and not n.is_simulated_partitioned
        ]

        is_degraded = False

        if len(healthy_nodes) < write_quorum:
            if avail_mode == "AVAILABILITY_FIRST":
                if len(healthy_nodes) == 0:
                    raise QuorumNotReachedError(
                        message="Zero healthy nodes reachable. Storage system completely offline.",
                        details={"healthy_nodes": 0},
                    )
                # In AVAILABILITY_FIRST mode: allow degraded write with fewer replicas
                logger.warning(
                    f"AVAILABILITY_FIRST policy invoked: healthy nodes ({len(healthy_nodes)}) "
                    f"is below write quorum ({write_quorum}). Proceeding in degraded write mode."
                )
                is_degraded = True
                return healthy_nodes[:rf], is_degraded
            else:
                # In DURABILITY_FIRST mode: reject the write to prevent under-replicated data
                raise QuorumNotReachedError(
                    message=(
                        f"DURABILITY_FIRST policy violated: only {len(healthy_nodes)} healthy node(s) "
                        f"available, but policy '{policy.name}' requires a write quorum of {write_quorum}."
                    ),
                    details={
                        "policy": policy.name,
                        "availability_mode": avail_mode,
                        "needed_quorum": write_quorum,
                        "available_healthy": len(healthy_nodes),
                    },
                )

        # Segregate into failure domains (Zone A and Zone B)
        zone_a = [n for n in healthy_nodes if n.zone == "Zone-A"]
        zone_b = [n for n in healthy_nodes if n.zone == "Zone-B"]

        # Sort within zone by least used capacity
        zone_a.sort(key=lambda n: n.used_capacity_bytes)
        zone_b.sort(key=lambda n: n.used_capacity_bytes)

        selected: List[StorageNode] = []

        if rf == 3:
            # Optimal distribution across zones
            if len(zone_a) >= 2 and len(zone_b) >= 1:
                selected = [zone_a[0], zone_a[1], zone_b[0]]
            elif len(zone_b) >= 2 and len(zone_a) >= 1:
                selected = [zone_a[0], zone_b[0], zone_b[1]]
            elif len(zone_a) >= 1 and len(zone_b) >= 1:
                selected = [zone_a[0], zone_b[0]]
                is_degraded = True
            else:
                selected = healthy_nodes[:rf]
                is_degraded = len(selected) < rf
        elif rf == 2:
            # 1 in Zone A, 1 in Zone B
            if zone_a and zone_b:
                selected = [zone_a[0], zone_b[0]]
            else:
                selected = healthy_nodes[:rf]
                is_degraded = (len(zone_a) == 0 or len(zone_b) == 0)
        else:
            # General distribution (e.g. EC 4+2 across all 6 nodes)
            idx_a, idx_b = 0, 0
            while len(selected) < rf and (idx_a < len(zone_a) or idx_b < len(zone_b)):
                if idx_a < len(zone_a) and len(selected) < rf:
                    selected.append(zone_a[idx_a])
                    idx_a += 1
                if idx_b < len(zone_b) and len(selected) < rf:
                    selected.append(zone_b[idx_b])
                    idx_b += 1

        if len(selected) < write_quorum:
            if avail_mode == "AVAILABILITY_FIRST" and len(selected) > 0:
                is_degraded = True
            else:
                raise QuorumNotReachedError(
                    message=f"Selected {len(selected)} nodes, below required write quorum of {write_quorum}",
                    details={"selected": len(selected), "quorum": write_quorum},
                )

        return selected, is_degraded


placement_engine = PlacementEngine()
