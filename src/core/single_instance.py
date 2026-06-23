"""
单实例检测与文件路径转发。

使用 PyQt6.QtNetwork 的 QLocalServer / QLocalSocket 实现：
- 首次启动 → 成为主实例，监听后续请求
- 后续启动 → 将文件路径发给主实例后退出

进程崩溃时 OS 自动清理命名管道/Unix socket，无残留锁问题。
"""

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtNetwork import QLocalServer, QLocalSocket


SERVER_NAME = "MarkdownEditor_CS201"


class SingleInstanceManager(QObject):
    """单实例管理器。

    用法：
        manager = SingleInstanceManager()
        if manager.try_acquire():
            # 主实例 —— 正常启动
            manager.file_received.connect(open_file)
        else:
            # 已有实例在运行 —— 转发文件路径后退出
            manager.send_file_paths(file_paths)
            sys.exit(0)
    """

    file_received = pyqtSignal(str)  # 其他实例发来的文件路径

    def __init__(self, parent=None):
        super().__init__(parent)
        self._server: QLocalServer | None = None
        self._is_primary: bool = False

    @property
    def is_primary(self) -> bool:
        """当前实例是否是主实例。"""
        return self._is_primary

    def try_acquire(self) -> bool:
        """尝试成为主实例。

        Returns:
            True — 当前是主实例，应正常启动。
            False — 已有实例在运行，调用方应转发文件路径后退出。
        """
        # 先尝试移除可能残留的旧 socket（上一次不正常退出时遗留）
        QLocalServer.removeServer(SERVER_NAME)

        self._server = QLocalServer(self)
        if self._server.listen(SERVER_NAME):
            self._is_primary = True
            self._server.newConnection.connect(self._on_new_connection)
            return True
        else:
            self._is_primary = False
            return False

    def send_file_paths(self, paths: list[str]) -> bool:
        """将文件路径列表发给主实例。

        Args:
            paths: 文件绝对路径列表。

        Returns:
            True 如果发送成功。
        """
        if not paths:
            return False

        socket = QLocalSocket()
        socket.connectToServer(SERVER_NAME)
        if not socket.waitForConnected(3000):
            return False

        # 一行一个路径，以换行分隔
        data = "\n".join(paths).encode("utf-8")
        socket.write(data)
        if not socket.waitForBytesWritten(3000):
            socket.disconnectFromServer()
            return False

        # 短暂等待让主实例读完数据
        socket.waitForDisconnected(1000)
        return True

    def _on_new_connection(self) -> None:
        """主实例收到新连接 —— 读取文件路径并发射信号。"""
        if self._server is None:
            return

        client = self._server.nextPendingConnection()
        if client is None:
            return

        # 进程退出时 QLocalServer 可能触发假的 connection 事件
        if not client.waitForReadyRead(3000):
            client.disconnectFromServer()
            return

        data = bytes(client.readAll()).decode("utf-8", errors="replace")
        client.disconnectFromServer()

        # 解析文件路径
        for line in data.strip().split("\n"):
            path = line.strip()
            if path:
                self.file_received.emit(path)
