"""Tests for the update coordinator."""
from datetime import timedelta
import logging

from asynctest import CoroutineMock, Mock
import pytest

from homeassistant.helpers import update_coordinator
from homeassistant.util.dt import utcnow

from tests.common import async_fire_time_changed

LOGGER = logging.getLogger(__name__)


@pytest.fixture
def crd(hass):
    """Coordinator mock."""
    calls = []

    async def refresh():
        calls.append(None)
        return len(calls)

    crd = update_coordinator.DataUpdateCoordinator(
        hass, LOGGER, "test", refresh, timedelta(seconds=10),
    )
    return crd


async def test_async_refresh(crd):
    """Test async_refresh for update coordinator."""
    assert crd.data is None
    await crd.async_refresh()
    assert crd.data == 1
    assert crd.failed_last_update is False

    updates = []

    def update_callback():
        updates.append(crd.data)

    crd.async_add_listener(update_callback)

    await crd.async_refresh()

    assert updates == [2]

    crd.async_remove_listener(update_callback)

    await crd.async_refresh()

    assert updates == [2]


async def test_request_refresh(crd):
    """Test request refresh for update coordinator."""
    assert crd.data is None
    await crd.async_request_refresh()
    assert crd.data == 1
    assert crd.failed_last_update is False

    # Second time we hit the debonuce
    await crd.async_request_refresh()
    assert crd.data == 1
    assert crd.failed_last_update is False


async def test_refresh_fail(crd, caplog):
    """Test a failing update function."""
    crd.update_method = CoroutineMock(side_effect=update_coordinator.UpdateFailed)

    await crd.async_refresh()

    assert crd.data is None
    assert crd.failed_last_update is True
    assert "Error fetching test data" in caplog.text

    crd.update_method = CoroutineMock(return_value=1)

    await crd.async_refresh()

    assert crd.data == 1
    assert crd.failed_last_update is False

    crd.update_method = CoroutineMock(side_effect=ValueError)
    caplog.clear()

    await crd.async_refresh()

    assert crd.data == 1  # value from previous fetch
    assert crd.failed_last_update is True
    assert "Unexpected error fetching test data" in caplog.text


async def test_update_interval(hass, crd):
    """Test update interval works."""
    # Test we don't update without subscriber
    async_fire_time_changed(hass, utcnow() + crd.update_interval)
    await hass.async_block_till_done()
    assert crd.data is None

    # Add subscriber
    update_callback = Mock()
    crd.async_add_listener(update_callback)

    # Test twice we update with subscriber
    async_fire_time_changed(hass, utcnow() + crd.update_interval)
    await hass.async_block_till_done()
    assert crd.data == 1

    async_fire_time_changed(hass, utcnow() + crd.update_interval)
    await hass.async_block_till_done()
    assert crd.data == 2

    # Test removing listener
    crd.async_remove_listener(update_callback)

    async_fire_time_changed(hass, utcnow() + crd.update_interval)
    await hass.async_block_till_done()

    # Test we stop updating after we lose last subscriber
    assert crd.data == 2
