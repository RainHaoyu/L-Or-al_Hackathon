import pytest

from app.core.config import get_settings
from app.modules.ingredient.repository import init_repository


@pytest.fixture(scope="session")
def repo():
    return init_repository(get_settings().data_dir)


@pytest.fixture(scope="session")
def engine(repo):
    from app.modules.qra2.engine import QRA2Engine
    return QRA2Engine(repo.config)
