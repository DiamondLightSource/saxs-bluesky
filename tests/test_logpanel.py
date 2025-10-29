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
def mock_text() -> Mock:
    text_mock = Mock()
    text_mock.pack = Mock()
    text_mock.tag_config = Mock()
    text_mock.configure = Mock()
    return text_mock


@pytest.fixture
def mock_scrollbar() -> Mock:
    scrollbar_mock = Mock()
    scrollbar_mock.pack = Mock()
    return scrollbar_mock


@pytest.fixture
def mock_style() -> Mock:
    return Mock()


@pytest.fixture
def mock_tkinter(mock_text: Mock, mock_scrollbar: Mock, mock_style: Mock) -> Mock:
    tk_mock = Mock(spec=Tk)
    tk_mock.title = Mock()
    tk_mock.wm_resizable = Mock()
    tk_mock.minsize = Mock()
    tk_mock.bind = Mock()

    # Setup Text widget mocking
    def setup_mocks():
        return tk_mock

    return setup_mocks()


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


# @pytest.fixture
# def connected_logpanel(
#     connected_messenger: RabbitMQMessenger,
#     mock_tkinter: Tk,
# ) -> BlueskyLogPanel:
#     connected_logpanel = BlueskyLogPanel(
#         beamline="ixx",
#         start=False,
#         rabbitmq_messenger=connected_messenger,
#         window=mock_tkinter,
#     )

#     return connected_logpanel


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
    mock_text.return_value = Mock()
    mock_text.return_value.pack = Mock()
    mock_text.return_value.tag_config = Mock()
    mock_text.return_value.configure = Mock()

    # Create the log panel
    connected_logpanel = BlueskyLogPanel(
        beamline="ixx",
        start=False,
        rabbitmq_messenger=connected_messenger,
        window=mock_tkinter,
    )

    assert isinstance(connected_logpanel, BlueskyLogPanel)

    # Verify basic initialization
    assert connected_logpanel.run is True
    assert connected_logpanel.update_interval == 0.025
    assert connected_logpanel.messenger == connected_messenger
    assert connected_logpanel.window == mock_tkinter

    # Verify window configuration
    mock_tkinter.title.assert_called_once_with("Bluesky Log Panel")
    mock_tkinter.wm_resizable.assert_called_once_with(True, True)
    mock_tkinter.minsize.assert_called_once_with(1400, 400)

    # Test cleanup
    connected_logpanel.on_destroy(None)
    assert not connected_logpanel.run  # verify run flag is set to False
