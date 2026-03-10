"""Infrastructure integration tests.

These tests verify that the Docker Compose stack is running correctly.
Run with: pytest tests/integration/test_infrastructure.py -m integration
"""


import httpx
import pytest


@pytest.mark.integration
@pytest.mark.slow
class TestConsulCluster:
    """Tests for Consul cluster health."""

    @pytest.fixture
    def consul_url(self) -> str:
        """Consul API URL."""
        return "http://localhost:8500"

    async def test_consul_is_reachable(self, consul_url: str) -> None:
        """Consul HTTP API should be reachable."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{consul_url}/v1/status/leader")

        assert response.status_code == 200
        # Leader should be elected
        leader = response.json()
        assert leader, "Consul cluster should have a leader"

    async def test_consul_cluster_has_three_members(self, consul_url: str) -> None:
        """Consul cluster should have 3 members."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{consul_url}/v1/agent/members")

        assert response.status_code == 200
        members = response.json()
        assert len(members) == 3, f"Expected 3 Consul members, got {len(members)}"

    async def test_consul_kv_operations(self, consul_url: str) -> None:
        """Consul KV store should support basic operations."""
        async with httpx.AsyncClient() as client:
            # PUT
            put_response = await client.put(
                f"{consul_url}/v1/kv/test/infrastructure",
                content=b"test-value",
            )
            assert put_response.status_code == 200

            # GET
            get_response = await client.get(f"{consul_url}/v1/kv/test/infrastructure")
            assert get_response.status_code == 200

            # DELETE (cleanup)
            delete_response = await client.delete(f"{consul_url}/v1/kv/test/infrastructure")
            assert delete_response.status_code == 200


@pytest.mark.integration
@pytest.mark.slow
class TestKafka:
    """Tests for Kafka broker."""

    async def test_kafka_is_reachable(self) -> None:
        """Kafka broker should be reachable via admin API."""
        # Use aiokafka to test connection
        from aiokafka.admin import AIOKafkaAdminClient

        admin = AIOKafkaAdminClient(bootstrap_servers="localhost:19092")
        try:
            await admin.start()
            # List topics to verify connection
            topics = await admin.list_topics()
            assert isinstance(topics, set)
        finally:
            await admin.close()

    async def test_can_create_topic(self) -> None:
        """Should be able to create a Kafka topic."""
        from aiokafka.admin import AIOKafkaAdminClient, NewTopic

        admin = AIOKafkaAdminClient(bootstrap_servers="localhost:19092")
        try:
            await admin.start()

            # Create test topic
            topic = NewTopic(
                name="test.infrastructure.topic",
                num_partitions=1,
                replication_factor=1,
            )
            await admin.create_topics([topic])

            # Verify topic exists
            topics = await admin.list_topics()
            assert "test.infrastructure.topic" in topics

            # Cleanup
            await admin.delete_topics(["test.infrastructure.topic"])
        finally:
            await admin.close()


@pytest.mark.integration
@pytest.mark.slow
class TestPostgreSQL:
    """Tests for PostgreSQL database."""

    @pytest.fixture
    def database_url(self) -> str:
        """PostgreSQL connection URL."""
        return "postgresql://registry:registry_dev_password@localhost:15432/registry"

    async def test_postgres_is_reachable(self, database_url: str) -> None:
        """PostgreSQL should be reachable."""
        import asyncpg

        conn = await asyncpg.connect(database_url)
        try:
            # Simple query to verify connection
            result = await conn.fetchval("SELECT 1")
            assert result == 1
        finally:
            await conn.close()

    async def test_can_create_table(self, database_url: str) -> None:
        """Should be able to create a table."""
        import asyncpg

        conn = await asyncpg.connect(database_url)
        try:
            # Create test table
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS test_infrastructure (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            """
            )

            # Insert and query
            await conn.execute(
                "INSERT INTO test_infrastructure (name) VALUES ($1)",
                "test-value",
            )

            result = await conn.fetchval(
                "SELECT name FROM test_infrastructure WHERE name = $1",
                "test-value",
            )
            assert result == "test-value"

            # Cleanup
            await conn.execute("DROP TABLE test_infrastructure")
        finally:
            await conn.close()


@pytest.mark.integration
@pytest.mark.slow
class TestRegistryService:
    """Tests for the Registry Service container."""

    @pytest.fixture
    def registry_url(self) -> str:
        """Registry Service API URL."""
        return "http://localhost:8080"

    async def test_registry_service_is_healthy(self, registry_url: str) -> None:
        """Registry service should be healthy."""
        async with httpx.AsyncClient() as client:
            # Check liveness
            live_response = await client.get(f"{registry_url}/health/live")
            assert live_response.status_code == 200
            assert live_response.json()["status"] == "alive"

            # Check readiness
            ready_response = await client.get(f"{registry_url}/health/ready")
            assert ready_response.status_code == 200
            assert ready_response.json()["status"] == "ready"

    async def test_registry_service_openapi(self, registry_url: str) -> None:
        """Registry service should expose OpenAPI docs."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{registry_url}/openapi.json")

        assert response.status_code == 200
        openapi = response.json()
        assert openapi["info"]["title"] == "VentureStrat Registry Service"
