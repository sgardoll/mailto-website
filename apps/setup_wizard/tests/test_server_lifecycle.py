"""
Unit tests for setup.server lifecycle functions.
Tests: find_free_port, check_write_permission, _shutdown_server, exit_wizard
"""
import signal
import socket
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from apps.setup_wizard.server import find_free_port, check_write_permission


def test_find_free_port_returns_preferred():
    """When socket.bind succeeds for 7331, find_free_port() returns 7331."""
    mock_sock = MagicMock()
    with patch('socket.socket') as mock_socket_cls:
        mock_socket_cls.return_value.__enter__ = lambda s: mock_sock
        mock_socket_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_sock.bind = MagicMock()  # succeeds
        mock_sock.getsockname.return_value = ('', 7331)
        result = find_free_port()
    assert result == 7331


def test_find_free_port_falls_back():
    """When first bind raises OSError, falls back to OS-assigned port 54321."""
    call_count = [0]

    def side_effect(addr):
        call_count[0] += 1
        if call_count[0] == 1:
            raise OSError("Port in use")
        # second call: no-op (OS assigns port)

    mock_sock = MagicMock()
    mock_sock.bind.side_effect = side_effect
    mock_sock.getsockname.return_value = ('', 54321)

    with patch('socket.socket') as mock_socket_cls:
        mock_socket_cls.return_value.__enter__ = lambda s: mock_sock
        mock_socket_cls.return_value.__exit__ = MagicMock(return_value=False)
        result = find_free_port()
    assert result == 54321


def test_check_write_permission_true():
    """When os.access returns True, check_write_permission returns True."""
    with patch('os.access', return_value=True):
        result = check_write_permission(Path('/any'))
    assert result is True


def test_check_write_permission_false():
    """When os.access returns False, check_write_permission returns False."""
    with patch('os.access', return_value=False):
        result = check_write_permission(Path('/any'))
    assert result is False


def test_shutdown_sends_sigint():
    """_shutdown_server() must call os.kill(os.getpid(), signal.SIGINT)."""
    from apps.setup_wizard.server import _shutdown_server
    with patch('os.getpid', return_value=9999), \
         patch('os.kill') as mock_kill:
        _shutdown_server()
    mock_kill.assert_called_once_with(9999, signal.SIGINT)


def test_exit_route_returns_ok():
    """POST /exit returns 200 with {"ok": true}. Thread fires but process does not exit."""
    from apps.setup_wizard.server import app
    with patch('apps.setup_wizard.server._shutdown_server'):
        with app.test_client() as client:
            response = client.post('/exit')
    assert response.status_code == 200
    assert response.get_json() == {"ok": True}
