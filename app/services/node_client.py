from typing import Optional, Tuple, Dict, Any
import httpx
from app.core.exceptions import StorageNodeUnavailableError, DataIntegrityError
from app.core.logging_config import logger


class NodeClient:
    """Async client interfacing with physical storage node processes."""

    def __init__(self, timeout: float = 5.0):
        self.timeout = timeout

    async def put_chunk(self, host: str, port: int, replica_id: str, data: bytes) -> Dict[str, Any]:
        url = f"http://{host}:{port}/chunks/{replica_id}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.put(url, content=data)
                if res.status_code != 201:
                    raise StorageNodeUnavailableError(
                        message=f"Node {host}:{port} returned error {res.status_code} during chunk write",
                        details={"node": f"{host}:{port}", "replica_id": replica_id},
                    )
                return res.json()
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to storage node {host}:{port}: {e}")
            raise StorageNodeUnavailableError(
                message=f"Storage node at {host}:{port} is unreachable",
                details={"host": host, "port": port, "error": str(e)},
            )

    async def get_chunk(self, host: str, port: int, replica_id: str) -> Tuple[bytes, str]:
        """Fetch raw bytes from node and extract SHA-256 header."""
        url = f"http://{host}:{port}/chunks/{replica_id}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.get(url)
                if res.status_code == 404:
                    raise StorageNodeUnavailableError(
                        message=f"Replica {replica_id} not found on node {host}:{port}",
                        details={"node": f"{host}:{port}", "replica_id": replica_id},
                    )
                if res.status_code != 200:
                    raise StorageNodeUnavailableError(
                        message=f"Storage node {host}:{port} returned HTTP {res.status_code}",
                        details={"node": f"{host}:{port}", "replica_id": replica_id},
                    )
                data = res.content
                checksum = res.headers.get("X-Checksum-SHA256", "")
                return data, checksum
        except httpx.RequestError as e:
            logger.error(f"Failed to read from storage node {host}:{port}: {e}")
            raise StorageNodeUnavailableError(
                message=f"Storage node at {host}:{port} is unreachable",
                details={"host": host, "port": port, "error": str(e)},
            )

    async def delete_chunk(self, host: str, port: int, replica_id: str) -> bool:
        url = f"http://{host}:{port}/chunks/{replica_id}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.delete(url)
                return res.status_code == 200
        except httpx.RequestError:
            return False

    async def check_health(self, host: str, port: int) -> Optional[Dict[str, Any]]:
        url = f"http://{host}:{port}/health"
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                res = await client.get(url)
                if res.status_code == 200:
                    return res.json()
        except httpx.RequestError:
            return None
        return None

    async def corrupt_chunk_on_disk(self, host: str, port: int, replica_id: str) -> bool:
        url = f"http://{host}:{port}/chunks/{replica_id}/corrupt"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(url)
                return res.status_code == 200
        except httpx.RequestError:
            return False

    async def take_node_offline(self, host: str, port: int) -> bool:
        url = f"http://{host}:{port}/chaos/offline"
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                res = await client.post(url)
                return res.status_code == 200
        except httpx.RequestError:
            return False

    async def bring_node_online(self, host: str, port: int) -> bool:
        url = f"http://{host}:{port}/chaos/online"
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                res = await client.post(url)
                return res.status_code == 200
        except httpx.RequestError:
            return False


node_client = NodeClient()
