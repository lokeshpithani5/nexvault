from sqlalchemy import select
from app.core.config import settings
from app.core.database import setup_database_engine, get_engine, get_session_factory, Base
from app.core.security import get_password_hash
from app.core.logging_config import logger
from app.models.user import User
from app.models.policy import Policy
from app.models.storage_node import StorageNode
from app.models.event import Event
import app.models  # ensure all models are registered with Base.metadata


async def init_db():
    """Initializes tables and seeds baseline configuration."""
    engine = await setup_database_engine()

    logger.info("Initializing database schema...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database schema creation verified.")

    session_factory = get_session_factory()
    async with session_factory() as session:
        # 1. Seed Default Durability Policies
        policies = [
            Policy(
                name="standard-rf3",
                type="REPLICATION",
                replication_factor=3,
                min_write_quorum=2,
                min_read_quorum=1,
                description="Default 3-way replication distributed across Zone A and Zone B with quorum write",
            ),
            Policy(
                name="light-rf2",
                type="REPLICATION",
                replication_factor=2,
                min_write_quorum=2,
                min_read_quorum=1,
                description="2-way cross-zone replication for low overhead",
            ),
            Policy(
                name="ec-4-2",
                type="ERASURE_CODING",
                replication_factor=6,
                data_shards=4,
                parity_shards=2,
                min_write_quorum=4,
                min_read_quorum=4,
                description="Reed-Solomon 4 data + 2 parity shards across 6 nodes",
            ),
        ]
        for pol in policies:
            stmt = select(Policy).where(Policy.name == pol.name)
            res = await session.execute(stmt)
            if not res.scalars().first():
                session.add(pol)
                logger.info(f"Seeded durability policy: {pol.name}")

        # 2. Seed 6 Storage Nodes
        # Ports 5001-5003 in Zone A, 5004-5006 in Zone B
        node_configs = [
            ("node-01", 5001, "Zone-A"),
            ("node-02", 5002, "Zone-A"),
            ("node-03", 5003, "Zone-A"),
            ("node-04", 5004, "Zone-B"),
            ("node-05", 5005, "Zone-B"),
            ("node-06", 5006, "Zone-B"),
        ]
        for name, port, zone in node_configs:
            stmt = select(StorageNode).where(StorageNode.port == port)
            res = await session.execute(stmt)
            if not res.scalars().first():
                node = StorageNode(
                    name=name,
                    port=port,
                    zone=zone,
                    host=settings.STORAGE_NODE_HOST,
                    status="HEALTHY",
                    is_simulated_partitioned=False,
                )
                session.add(node)
                logger.info(f"Seeded storage node registry: {name} (Port {port}, {zone})")

        # 3. Seed Default Administrator Account
        admin_email = settings.INITIAL_ADMIN_EMAIL
        stmt = select(User).where(User.email == admin_email)
        res = await session.execute(stmt)
        if not res.scalars().first():
            admin_user = User(
                email=admin_email,
                hashed_password=get_password_hash(settings.INITIAL_ADMIN_PASSWORD),
                full_name=settings.INITIAL_ADMIN_NAME,
                role="ADMIN",
                is_active=True,
            )
            session.add(admin_user)
            logger.info(f"Seeded administrative user: {admin_email}")

        # 4. Log Initialization Event
        init_event = Event(
            severity="INFO",
            category="NODE",
            message="NEXVAULT Control Plane metadata initialized successfully",
            details_json={"environment": settings.ENVIRONMENT, "app_version": settings.APP_VERSION},
        )
        session.add(init_event)

        await session.commit()
    logger.info("Database initialization and baseline seeding complete.")
