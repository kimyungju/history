import pytest
from unittest.mock import patch, AsyncMock, MagicMock


@pytest.fixture
def mock_gcp():
    """Patch GCP services so FastAPI app can be imported without real credentials."""
    mock_driver = MagicMock()
    mock_driver.verify_connectivity = AsyncMock()
    mock_driver.close = AsyncMock()

    with (
        patch("neo4j.AsyncGraphDatabase.driver", return_value=mock_driver),
        patch("vertexai.init"),
    ):
        yield {"neo4j_driver": mock_driver}
