"""
Integration tests for reservation service.

Tests process management, cancellation, and state management.
"""
import pytest
import time
from unittest.mock import Mock, patch

from storage import RedisStorage
from services import TelegramService, ReservationService
from models import UserSession, TrainSearchParams, RunningReservation


class TestReservationService:
    """Test reservation service functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.storage = RedisStorage()
        self.telegram = Mock(spec=TelegramService)
        self.service = ReservationService(self.storage, self.telegram)

    def teardown_method(self):
        """Clean up after each test."""
        # Clean up any running processes
        all_reservations = self.storage.get_all_running_reservations()
        for reservation in all_reservations:
            try:
                import os
                import signal
                os.kill(reservation.process_id, signal.SIGTERM)
            except:
                pass
        self.storage.redis.flushdb()

    @patch('subprocess.Popen')
    def test_start_reservation_process_success(self, mock_popen):
        """Test starting a reservation process successfully."""
        mock_process = Mock()
        mock_process.pid = 12345
        mock_popen.return_value = mock_process

        chat_id = 99999
        search_params = TrainSearchParams(
            dep_date="20991231",
            src_locate="서울",
            dst_locate="부산",
            dep_time="090000",
            max_dep_time="1800",
            train_type="TrainType.KTX",
            train_type_display="KTX",
            special_option="ReserveOption.GENERAL_FIRST",
            special_option_display="GENERAL_FIRST",
            passenger_count=1,
            seat_strategy="consecutive"
        )

        success = self.service.start_reservation_process(
            chat_id=chat_id,
            username="010-1234-5678",
            password="password123",
            search_params=search_params
        )

        assert success is True
        mock_popen.assert_called_once()

        # Check storage
        running = self.storage.get_running_reservation(chat_id)
        assert running is not None
        assert running.process_id == 12345
        assert running.search_params.src_locate == "서울"

    def test_start_reservation_duplicate(self):
        """Test starting reservation when one is already running."""
        chat_id = 99999

        # Create existing reservation
        existing = RunningReservation(
            chat_id=chat_id,
            process_id=11111,
            search_params=TrainSearchParams(
                dep_date="20991231",
                src_locate="서울",
                dst_locate="부산",
                dep_time="090000",
                max_dep_time="1800",
                train_type="TrainType.KTX",
                train_type_display="KTX",
                special_option="ReserveOption.GENERAL_FIRST",
                special_option_display="GENERAL_FIRST",
                passenger_count=1,
                seat_strategy="consecutive"
            )
        )
        self.storage.save_running_reservation(existing)

        search_params = TrainSearchParams(
            dep_date="20991231",
            src_locate="대전",
            dst_locate="광주",
            dep_time="100000",
            max_dep_time="1900",
            train_type="TrainType.KTX",
            train_type_display="KTX",
            special_option="ReserveOption.GENERAL_FIRST",
            special_option_display="GENERAL_FIRST",
            passenger_count=1,
            seat_strategy="consecutive"
        )

        success = self.service.start_reservation_process(
            chat_id=chat_id,
            username="010-1234-5678",
            password="password123",
            search_params=search_params
        )

        # Should fail because one is already running
        assert success is False
        self.telegram.send_message.assert_called_once()
        call_args = self.telegram.send_message.call_args
        assert "이미" in call_args[0][1] or "already" in call_args[0][1].lower()

    @patch('subprocess.Popen')
    def test_cancel_reservation_success(self, mock_popen):
        """Test cancelling a running reservation."""
        # Start a reservation first
        mock_process = Mock()
        mock_process.pid = 12345
        mock_popen.return_value = mock_process

        chat_id = 99999
        search_params = TrainSearchParams(
            dep_date="20991231",
            src_locate="서울",
            dst_locate="부산",
            dep_time="090000",
            max_dep_time="1800",
            train_type="TrainType.KTX",
            train_type_display="KTX",
            special_option="ReserveOption.GENERAL_FIRST",
            special_option_display="GENERAL_FIRST",
            passenger_count=1,
            seat_strategy="consecutive"
        )

        self.service.start_reservation_process(
            chat_id=chat_id,
            username="010-1234-5678",
            password="password123",
            search_params=search_params
        )

        # Now cancel it
        with patch('os.kill') as mock_kill:
            self.service.cancel_reservation(chat_id)

            # Should have killed the process
            mock_kill.assert_called()

            # Should have cleaned up storage
            running = self.storage.get_running_reservation(chat_id)
            assert running is None

            # Should have notified user
            assert self.telegram.send_message.call_count >= 2  # Start + cancel

    def test_cancel_reservation_no_running(self):
        """Test cancelling when no reservation is running."""
        chat_id = 99999

        self.service.cancel_reservation(chat_id)

        # Should send message that nothing was running
        self.telegram.send_message.assert_called_once()
        call_args = self.telegram.send_message.call_args
        assert "없" in call_args[0][1] or "no" in call_args[0][1].lower()

    def test_get_status_no_reservation(self):
        """Test getting status when no reservation is running."""
        chat_id = 99999

        status = self.service.get_status(chat_id)

        assert "없" in status or "no" in status.lower()

    def test_get_status_with_reservation(self):
        """Test getting status with running reservation."""
        chat_id = 99999

        reservation = RunningReservation(
            chat_id=chat_id,
            process_id=12345,
            search_params=TrainSearchParams(
                dep_date="20991231",
                src_locate="서울",
                dst_locate="부산",
                dep_time="090000",
                max_dep_time="1800",
                train_type="TrainType.KTX",
                train_type_display="KTX",
                special_option="ReserveOption.GENERAL_FIRST",
                special_option_display="GENERAL_FIRST",
                passenger_count=1,
                seat_strategy="consecutive"
            )
        )
        self.storage.save_running_reservation(reservation)

        status = self.service.get_status(chat_id)

        assert "서울" in status
        assert "부산" in status
        assert "20991231" in status

    @patch('subprocess.Popen')
    def test_cancel_all_reservations(self, mock_popen):
        """Test cancelling all reservations."""
        mock_process1 = Mock()
        mock_process1.pid = 11111
        mock_process2 = Mock()
        mock_process2.pid = 22222

        mock_popen.side_effect = [mock_process1, mock_process2]

        # Start two reservations
        search_params = TrainSearchParams(
            dep_date="20991231",
            src_locate="서울",
            dst_locate="부산",
            dep_time="090000",
            max_dep_time="1800",
            train_type="TrainType.KTX",
            train_type_display="KTX",
            special_option="ReserveOption.GENERAL_FIRST",
            special_option_display="GENERAL_FIRST",
            passenger_count=1,
            seat_strategy="consecutive"
        )

        self.service.start_reservation_process(11111, "010-1111-1111", "pass1", search_params)
        self.service.start_reservation_process(22222, "010-2222-2222", "pass2", search_params)

        # Cancel all
        with patch('os.kill') as mock_kill:
            count = self.service.cancel_all_reservations(99999)

            assert count == 2
            assert mock_kill.call_count == 2

            # All should be cleaned up
            all_reservations = self.storage.get_all_running_reservations()
            assert len(all_reservations) == 0

    def test_process_cleanup_on_invalid_pid(self):
        """Test cleanup when process PID is invalid."""
        chat_id = 99999

        # Manually create reservation with invalid PID
        reservation = RunningReservation(
            chat_id=chat_id,
            process_id=999999999,  # Invalid PID
            search_params=TrainSearchParams(
                dep_date="20991231",
                src_locate="서울",
                dst_locate="부산",
                dep_time="090000",
                max_dep_time="1800",
                train_type="TrainType.KTX",
                train_type_display="KTX",
                special_option="ReserveOption.GENERAL_FIRST",
                special_option_display="GENERAL_FIRST",
                passenger_count=1,
                seat_strategy="consecutive"
            )
        )
        self.storage.save_running_reservation(reservation)

        # Try to cancel - should handle gracefully
        self.service.cancel_reservation(chat_id)

        # Should still clean up storage
        running = self.storage.get_running_reservation(chat_id)
        assert running is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
