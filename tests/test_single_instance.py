"""
单实例检测单元测试。
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, call

# 确保项目根目录在 path 中
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def test_single_instance_constants():
    """验证 SERVER_NAME 常量。"""
    from src.core.single_instance import SERVER_NAME
    assert "MarkdownEditor" in SERVER_NAME
    assert len(SERVER_NAME) > 0


def test_is_primary_after_acquire():
    """成功 listen 后 is_primary 应为 True。"""
    from src.core.single_instance import SingleInstanceManager
    with patch("src.core.single_instance.QLocalServer") as MockServer:
        mock_server = MagicMock()
        mock_server.listen.return_value = True
        MockServer.return_value = mock_server

        manager = SingleInstanceManager()
        result = manager.try_acquire()
        assert result is True
        assert manager.is_primary is True


def test_is_not_primary_after_failed_acquire():
    """listen 失败后 is_primary 应为 False。"""
    from src.core.single_instance import SingleInstanceManager
    with patch("src.core.single_instance.QLocalServer") as MockServer:
        with patch("src.core.single_instance.QLocalServer.removeServer"):
            mock_server = MagicMock()
            mock_server.listen.return_value = False
            MockServer.return_value = mock_server

            manager = SingleInstanceManager()
            result = manager.try_acquire()
            assert result is False
            assert manager.is_primary is False


def test_send_file_paths_no_paths():
    """空路径列表应返回 False。"""
    from src.core.single_instance import SingleInstanceManager
    manager = SingleInstanceManager()
    assert manager.send_file_paths([]) is False


def test_send_file_paths_with_paths():
    """有路径时应向服务器发送数据。"""
    from src.core.single_instance import SingleInstanceManager
    with patch("src.core.single_instance.QLocalSocket") as MockSocket:
        mock_socket = MagicMock()
        mock_socket.waitForConnected.return_value = True
        mock_socket.waitForBytesWritten.return_value = True
        MockSocket.return_value = mock_socket

        manager = SingleInstanceManager()
        paths = ["/home/user/readme.md", "/home/user/notes.md"]
        result = manager.send_file_paths(paths)
        assert result is True
        mock_socket.write.assert_called_once()
        # 验证数据包含文件路径
        written_data = mock_socket.write.call_args[0][0]
        assert b"readme.md" in written_data
        assert b"notes.md" in written_data


def test_send_file_paths_connection_failure():
    """连接失败时应返回 False。"""
    from src.core.single_instance import SingleInstanceManager
    with patch("src.core.single_instance.QLocalSocket") as MockSocket:
        mock_socket = MagicMock()
        mock_socket.waitForConnected.return_value = False
        MockSocket.return_value = mock_socket

        manager = SingleInstanceManager()
        result = manager.send_file_paths(["test.md"])
        assert result is False


def test_file_received_signal():
    """新连接收到数据后应发射 file_received 信号。"""
    from src.core.single_instance import SingleInstanceManager
    with patch("src.core.single_instance.QLocalServer") as MockServer:
        mock_server = MagicMock()
        mock_server.listen.return_value = True
        MockServer.return_value = mock_server

        manager = SingleInstanceManager()
        manager.try_acquire()

        # 创建 mock client
        mock_client = MagicMock()
        mock_client.waitForReadyRead.return_value = True
        mock_client.readAll.return_value = b"/test/readme.md\n"
        mock_server.nextPendingConnection.return_value = mock_client

        # 连接信号
        received = []
        manager.file_received.connect(lambda p: received.append(p))

        # 触发新连接
        mock_server.newConnection.connect.call_args[0][0]()
        assert len(received) == 1
        assert received[0] == "/test/readme.md"


def test_file_received_multiple_paths():
    """多行数据应发射多个信号。"""
    from src.core.single_instance import SingleInstanceManager
    with patch("src.core.single_instance.QLocalServer") as MockServer:
        mock_server = MagicMock()
        mock_server.listen.return_value = True
        MockServer.return_value = mock_server

        manager = SingleInstanceManager()
        manager.try_acquire()

        mock_client = MagicMock()
        mock_client.waitForReadyRead.return_value = True
        mock_client.readAll.return_value = b"/a.md\n/b.md\n/c.md\n"
        mock_server.nextPendingConnection.return_value = mock_client

        received = []
        manager.file_received.connect(lambda p: received.append(p))

        mock_server.newConnection.connect.call_args[0][0]()
        assert len(received) == 3
        assert received == ["/a.md", "/b.md", "/c.md"]


if __name__ == "__main__":
    tests = [
        test_single_instance_constants,
        test_is_primary_after_acquire,
        test_is_not_primary_after_failed_acquire,
        test_send_file_paths_no_paths,
        test_send_file_paths_with_paths,
        test_send_file_paths_connection_failure,
        test_file_received_signal,
        test_file_received_multiple_paths,
    ]

    passed = 0
    failed = 0
    for test_fn in tests:
        try:
            test_fn()
            print(f"  PASS  {test_fn.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {test_fn.__name__} - {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR {test_fn.__name__} - {e}")
            failed += 1

    print(f"\n{'='*40}")
    print(f"Result: {passed} passed, {failed} failed ({passed + failed} total)")
    sys.exit(0 if failed == 0 else 1)
