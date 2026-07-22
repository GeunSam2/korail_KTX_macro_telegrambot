"""Telegram-free local command line interface for Korail reservations."""
from __future__ import annotations

import argparse
import getpass
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from korail2 import ReserveOption, TrainType

from config.settings import settings
from services.korail_service import DuplicateReservationError, KorailService


LOG_PATH = Path(__file__).resolve().parents[1] / "local_notifications.log"


def notify(title: str, message: str, *, urgent: bool = False) -> None:
    """Send the best available local notification and always append a log."""
    timestamp = datetime.now().isoformat(timespec="seconds")
    with LOG_PATH.open("a", encoding="utf-8") as log_file:
        log_file.write(f"[{timestamp}] {title}: {message}\n")

    delivered = False
    powershell = shutil.which("powershell.exe")
    if powershell:
        safe_title = title.replace("'", "''")
        safe_message = message.replace("'", "''")
        icon = "Error" if urgent else "Information"
        script = (
            "Add-Type -AssemblyName PresentationFramework; "
            f"[System.Windows.MessageBox]::Show('{safe_message}', '{safe_title}', "
            f"'OK', '{icon}') | Out-Null"
        )
        try:
            subprocess.Popen(
                [powershell, "-NoProfile", "-Command", script],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            delivered = True
        except OSError:
            pass

    if not delivered and shutil.which("notify-send"):
        try:
            subprocess.run(
                ["notify-send", "--urgency", "critical" if urgent else "normal", title, message],
                check=False,
                timeout=5,
            )
            delivered = True
        except (OSError, subprocess.TimeoutExpired):
            pass

    print(f"\n\a[{title}] {message}", flush=True)


def valid_date(value: str) -> str:
    try:
        parsed = datetime.strptime(value, "%Y%m%d")
    except ValueError as exc:
        raise argparse.ArgumentTypeError("날짜는 YYYYMMDD 형식이어야 합니다.") from exc
    if parsed.date() < datetime.now().date():
        raise argparse.ArgumentTypeError("과거 날짜는 선택할 수 없습니다.")
    return value


def valid_time(value: str) -> str:
    normalized = value.replace(":", "")
    if len(normalized) not in (4, 6) or not normalized.isdigit():
        raise argparse.ArgumentTypeError("시간은 HHMM 또는 HHMMSS 형식이어야 합니다.")
    normalized = normalized[:4] + (normalized[4:] if len(normalized) == 6 else "00")
    try:
        datetime.strptime(normalized, "%H%M%S")
    except ValueError as exc:
        raise argparse.ArgumentTypeError("유효한 시간을 입력하세요.") from exc
    return normalized


def valid_max_time(value: str) -> str:
    normalized = value.replace(":", "")
    if normalized == "2400":
        return normalized
    if len(normalized) != 4 or not normalized.isdigit():
        raise argparse.ArgumentTypeError("시간은 HHMM 형식이어야 합니다.")
    try:
        datetime.strptime(normalized, "%H%M")
    except ValueError as exc:
        raise argparse.ArgumentTypeError("유효한 시간을 입력하세요.") from exc
    return normalized


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="텔레그램 없이 KTX 좌석을 검색하고 예약하며 로컬 알림을 보냅니다."
    )
    parser.add_argument("--user", default=os.environ.get("KORAIL_USER"), help="코레일 회원번호/아이디")
    parser.add_argument(
        "--credentials-file",
        type=Path,
        help="1행 회원번호, 2행 비밀번호 형식의 파일",
    )
    parser.add_argument("--from", dest="source", required=True, help="출발역 (예: 서울)")
    parser.add_argument("--to", dest="destination", required=True, help="도착역 (예: 부산)")
    parser.add_argument("--date", required=True, type=valid_date, help="출발일 YYYYMMDD")
    parser.add_argument("--after", default="000000", type=valid_time, help="최소 출발시간 HHMM")
    parser.add_argument("--before", default="2400", type=valid_max_time, help="최대 출발시간 HHMM (미포함)")
    parser.add_argument("--passengers", type=int, choices=range(1, 10), default=1)
    parser.add_argument("--all-trains", action="store_true", help="KTX 외 열차도 검색")
    parser.add_argument(
        "--seat",
        choices=("general-first", "general-only", "special-first", "special-only"),
        default="general-first",
    )
    parser.add_argument("--strategy", choices=("consecutive", "random"), default="consecutive")
    parser.add_argument("--max-attempts", type=int, help="테스트용 최대 조회 횟수")
    return parser


def read_credentials(path: Path) -> tuple[str, str]:
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except OSError as exc:
        raise ValueError(f"자격정보 파일을 읽을 수 없습니다: {path}") from exc
    if len(lines) < 2 or not lines[0].strip() or not lines[1].strip():
        raise ValueError("자격정보 파일은 1행 회원번호, 2행 비밀번호 형식이어야 합니다.")
    return lines[0].strip(), lines[1].strip()


def main() -> int:
    args = build_parser().parse_args()
    if args.credentials_file:
        try:
            username, password = read_credentials(args.credentials_file)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 2
    else:
        username = args.user or input("코레일 회원번호/아이디: ").strip()
        password = getpass.getpass("코레일 비밀번호(표시되지 않음): ")
    if not username or not password:
        print("아이디와 비밀번호가 필요합니다.", file=sys.stderr)
        return 2

    option_map = {
        "general-first": ReserveOption.GENERAL_FIRST,
        "general-only": ReserveOption.GENERAL_ONLY,
        "special-first": ReserveOption.SPECIAL_FIRST,
        "special-only": ReserveOption.SPECIAL_ONLY,
    }
    service = KorailService()
    print("코레일에 로그인 중...")
    if not service.login(username, password):
        notify("코레일 로그인 실패", "회원정보와 계정 상태를 확인하세요.", urgent=True)
        return 1

    summary = f"{args.date} {args.source}→{args.destination}, {args.after[:4]}~{args.before}, {args.passengers}명"
    notify("자동 예약 시작", summary)
    try:
        reservation = service.search_and_reserve_loop(
            dep_date=args.date,
            src_locate=args.source.removesuffix("역"),
            dst_locate=args.destination.removesuffix("역"),
            dep_time=args.after,
            max_dep_time=args.before,
            train_type=TrainType.ALL if args.all_trains else TrainType.KTX,
            reserve_option=option_map[args.seat],
            passenger_count=args.passengers,
            seat_strategy=args.strategy,
            max_attempts=args.max_attempts,
        )
    except KeyboardInterrupt:
        notify("자동 예약 중단", summary)
        return 130
    except DuplicateReservationError:
        notify("기존 예약 감지", "동일한 예약이 이미 있습니다. 코레일 예약 내역을 확인하세요.", urgent=True)
        return 3
    except Exception as exc:
        notify("자동 예약 오류", f"{type(exc).__name__}: {exc}", urgent=True)
        return 1

    if not reservation:
        notify("자동 예약 종료", "설정한 조회 횟수 내에 예약하지 못했습니다.")
        return 4

    message = (
        f"예약 성공: {reservation}\n\n"
        f"{settings.PAYMENT_TIMEOUT_MINUTES}분 이내에 코레일 사이트/앱에서 결제하세요.\n"
        f"{settings.KORAIL_PAYMENT_URL}"
    )
    notify("코레일 예약 성공", message, urgent=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
