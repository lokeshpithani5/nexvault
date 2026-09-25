from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.policy import Policy
from app.repositories.event_repository import EventRepository
from app.schemas.policy import PolicyResponse, PolicyUpdateRequest
from app.core.exceptions import ResourceNotFoundError, ConflictError


class PolicyService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.event_repo = EventRepository(session)

    async def list_policies(self) -> List[PolicyResponse]:
        stmt = select(Policy).order_by(Policy.name.asc())
        res = await self.session.execute(stmt)
        policies = list(res.scalars().all())
        return [PolicyResponse.model_validate(p) for p in policies]

    async def get_policy(self, policy_id: str) -> PolicyResponse:
        stmt = select(Policy).where(Policy.id == policy_id)
        res = await self.session.execute(stmt)
        policy = res.scalars().first()
        if not policy:
            raise ResourceNotFoundError(message=f"Policy '{policy_id}' not found")
        return PolicyResponse.model_validate(policy)

    async def update_policy_safe(self, policy_id: str, update_in: PolicyUpdateRequest) -> PolicyResponse:
        stmt = select(Policy).where(Policy.id == policy_id)
        res = await self.session.execute(stmt)
        policy = res.scalars().first()
        if not policy:
            raise ResourceNotFoundError(message=f"Policy '{policy_id}' not found")

        rf = update_in.replication_factor if update_in.replication_factor is not None else policy.replication_factor
        w_quorum = update_in.min_write_quorum if update_in.min_write_quorum is not None else policy.min_write_quorum
        r_quorum = update_in.min_read_quorum if update_in.min_read_quorum is not None else policy.min_read_quorum

        if w_quorum > rf:
            raise ConflictError(
                message=f"Invalid quorum: min_write_quorum ({w_quorum}) cannot exceed replication factor ({rf})"
            )
        if r_quorum > rf:
            raise ConflictError(
                message=f"Invalid quorum: min_read_quorum ({r_quorum}) cannot exceed replication factor ({rf})"
            )

        changes = {}
        if update_in.description is not None:
            policy.description = update_in.description
            changes["description"] = update_in.description
        if update_in.replication_factor is not None:
            policy.replication_factor = update_in.replication_factor
            changes["replication_factor"] = update_in.replication_factor
        if update_in.min_write_quorum is not None:
            policy.min_write_quorum = update_in.min_write_quorum
            changes["min_write_quorum"] = update_in.min_write_quorum
        if update_in.min_read_quorum is not None:
            policy.min_read_quorum = update_in.min_read_quorum
            changes["min_read_quorum"] = update_in.min_read_quorum
        if update_in.availability_mode is not None:
            policy.availability_mode = update_in.availability_mode
            changes["availability_mode"] = update_in.availability_mode

        await self.session.flush()

        await self.event_repo.log_event(
            severity="INFO",
            category="POLICY",
            message=f"Storage policy '{policy.name}' updated safely",
            details_json={"policy_id": policy.id, "policy_name": policy.name, "changes": changes},
        )

        return PolicyResponse.model_validate(policy)
