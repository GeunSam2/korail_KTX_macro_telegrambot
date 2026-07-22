"""Windows desktop application entry point."""
import sys
import traceback
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMessageBox

from gui.main_window import MainWindow


LOG_PATH = Path.home() / "KorailKTXDesktop" / "gui_error.log"


def handle_exception(exc_type, exc_value, exc_traceback) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    details = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    LOG_PATH.write_text(details, encoding="utf-8")
    QMessageBox.critical(
        None,
        "KTX 자동예약 오류",
        f"예상하지 못한 오류가 발생했습니다.\n오류 로그: {LOG_PATH}\n\n{exc_value}",
    )


def main() -> int:
    app = QApplication(sys.argv)
    sys.excepthook = handle_exception
    app.setApplicationName("KTX 자동예약")
    app.setOrganizationName("Celenort")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
