from datetime import date, time
from app.services.biometric_import_service import parse_biometric_export, _derive_status

FIXTURE = "tests/fixtures/sample_biometric_export.xls"


def _rows():
    with open(FIXTURE, "rb") as f:
        return parse_biometric_export(f.read())


def test_parses_all_users_and_all_days_in_the_period():
    rows = _rows()
    # 9 employees (User ID 1-9) x 16 days (2026-05-26 .. 2026-06-10 inclusive)
    assert len(rows) == 144
    user_ids = {r["user_id"] for r in rows}
    assert user_ids == {str(i) for i in range(1, 10)}


def test_dates_span_the_full_period_in_order_per_user():
    rows = [r for r in _rows() if r["user_id"] == "1"]
    dates = [r["date"] for r in rows]
    assert dates[0] == date(2026, 5, 26)
    assert dates[-1] == date(2026, 6, 10)
    assert dates == sorted(dates)


def test_takes_earliest_and_latest_punch_regardless_of_vendor_am_pm_ot_bucketing():
    # User 1 on 2026-05-27: the export buckets one punch as "Before Noon Out"
    # (11:26) and another as "Overtime Out" (20:01) - both should still be
    # picked up as this day's time_in/time_out.
    rows = [r for r in _rows() if r["user_id"] == "1" and r["date"] == date(2026, 5, 27)]
    assert len(rows) == 1
    row = rows[0]
    assert row["time_in"] == time(11, 26, 59, 989000)
    assert row["time_out"] == time(20, 1, 59, 861000)
    assert row["punch_count"] == 2


def test_day_with_no_punches_has_none_times():
    rows = [r for r in _rows() if r["user_id"] == "1" and r["date"] == date(2026, 5, 26)]
    assert rows[0]["time_in"] is None
    assert rows[0]["time_out"] is None
    assert rows[0]["punch_count"] == 0


def test_user_with_zero_punches_across_whole_period():
    rows = [r for r in _rows() if r["user_id"] == "5"]
    assert len(rows) == 16
    assert all(r["punch_count"] == 0 for r in rows)


class _FakeShift:
    def __init__(self, hour, minute):
        self.start_time = time(hour, minute)


def test_derive_status_present_within_grace_period():
    shift = _FakeShift(8, 0)
    assert _derive_status(time(8, 15), shift) == "present"


def test_derive_status_late_past_grace_period():
    shift = _FakeShift(8, 0)
    assert _derive_status(time(8, 16), shift) == "late"


def test_derive_status_absent_when_scheduled_but_no_punch():
    shift = _FakeShift(8, 0)
    assert _derive_status(None, shift) == "absent"


def test_derive_status_no_shift_and_punch_is_present_undetermined_lateness():
    assert _derive_status(time(9, 0), None) == "present"


def test_derive_status_no_shift_and_no_punch_is_none_caller_skips():
    assert _derive_status(None, None) is None


def test_closing_shift_grace_period():
    shift = _FakeShift(11, 30)
    assert _derive_status(time(11, 45), shift) == "present"
    assert _derive_status(time(11, 46), shift) == "late"
