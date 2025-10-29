from tkinter import Tk
from unittest.mock import Mock, patch  # type: ignore

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
def mock_tkinter() -> Mock:
    tk_mock = Mock(spec=Tk)
    tk_mock.title = Mock()
    tk_mock.wm_resizable = Mock()
    tk_mock.minsize = Mock()
    tk_mock.bind = Mock()
    tk_mock.update = Mock()
    tk_mock.update_idletasks = Mock()
    return tk_mock


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


@patch("saxs_bluesky.logging.bluesky_logpanel.Text")
@patch("saxs_bluesky.logging.bluesky_logpanel.ttk.Style")
@patch("saxs_bluesky.logging.bluesky_logpanel.ttk.Scrollbar")
def test_logpanel_initialization(
    mock_scrollbar: Mock,
    mock_style: Mock,
    mock_text: Mock,
    connected_messenger: RabbitMQMessenger,
    mock_tkinter: Mock,
) -> None:
    # Configure text widget mock
    text_widget = Mock()
    text_widget.pack = Mock()
    text_widget.tag_config = Mock()
    text_widget.configure = Mock()
    text_widget.yview = Mock()  # Required for scrollbar
    mock_text.return_value = text_widget

    # Configure scrollbar mock
    scrollbar_widget = Mock()
    scrollbar_widget.pack = Mock()
    mock_scrollbar.return_value = scrollbar_widget

    # Create the log panel
    connected_logpanel = BlueskyLogPanel(
        beamline="ixx",
        start=False,
        rabbitmq_messenger=connected_messenger,
        window=mock_tkinter,
    )

    # Verify basic initialization
    assert connected_logpanel.run is True
    assert connected_logpanel.update_interval == 0.025
    assert connected_logpanel.messenger == connected_messenger
    assert connected_logpanel.window == mock_tkinter

    sample_message = {
        "header": {
            "uid": "12345",
            "time": 9999,
            "msg_type": "start",
        },
        "data": {
            "key1": "value1",
            "key2": 42,
        },
    }

    connected_logpanel.messenger.scan_listener.messages.append(sample_message)

    connected_logpanel.run_loop(
        maxiter=5
    )  # Run the loop a few times to verify no errors

    # Test cleanup
    connected_logpanel.on_destroy(None)
    assert not connected_logpanel.run  # verify run flag is set to False
