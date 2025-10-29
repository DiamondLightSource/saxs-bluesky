import unittest
from tkinter import Tk
from unittest.mock import MagicMock, Mock  # type: ignore

import pytest
from stomp.connect import StompConnection11 as Connection  # type: ignore

from saxs_bluesky.logging.bluesky_logpanel import BlueskyLogPanel
from saxs_bluesky.logging.bluesky_messenger import (
    RabbitMQMessenger,
)


@pytest.fixture
def mock_connection() -> Mock:
    return Mock(spec=Connection)


@pytest.fixture
def mock_tkinter() -> MagicMock:
    return MagicMock(spec=Tk)


@pytest.fixture
def connected_messenger(mock_connection: Mock) -> RabbitMQMessenger:
    connected_messenger = RabbitMQMessenger(
        host="http://localhost",
        beamline="ixx",
        port=8080,
        auto_connect=False,
    )
    connected_messenger.conn = mock_connection
    connected_messenger.connect()
    connected_messenger.subscribe()

    return connected_messenger


@pytest.fixture
def connected_logpanel(
    connected_messenger: RabbitMQMessenger,
    mock_tkinter: Tk,
) -> BlueskyLogPanel:
    connected_logpanel = BlueskyLogPanel(
        beamline="ixx",
        start=False,
        rabbitmq_messenger=connected_messenger,
        window=mock_tkinter,
    )

    return connected_logpanel


@unittest.mock.patch("tkinter.Tk")  # type: ignore
def test_logpanel_initialization(connected_logpanel: BlueskyLogPanel):
    # assert isinstance(connected_logpanel, BlueskyLogPanel)
    assert connected_logpanel.messenger is not None
    assert connected_logpanel.logs is not None
    assert connected_logpanel.scrollbar is not None

    connected_logpanel.run_loop()
    connected_logpanel.on_destroy(None)
