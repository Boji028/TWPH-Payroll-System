# Fix Dashboard Pay Trend Chart

## What
The "Pay trend" chart on the admin dashboard rendered a broken-looking
y-axis (₱1, ₱0.9, ₱0.8 ... ₱0.1) with a flat line at zero whenever no
payroll run had been processed yet.

## Root cause
`pay_trend` totals come from summing `Payslip.net_pay` per `PayrollRun`
(`dashboard_service.py`). With every run still in Draft status, no
Payslips exist yet, so every point in the trend is `0`. Chart.js has no
real range to scale against in that case and falls back to an arbitrary
0-1 axis in 0.1 steps, which the existing tick callback then prefixed
with the peso sign - producing fractional peso labels on a meaningless
flat line.

## Fix
- `dashboard_service.py`: added `has_pay_trend_data` (`any(p["total"] > 0
  for p in pay_trend)`) to the stats dict.
- `dashboard.html`: `payWrap` now shows a "No processed payroll runs
  yet" message instead of the canvas when `has_pay_trend_data` is
  false. The chart-init script is guarded with `if (payCanvas)` so it
  only runs when the canvas actually exists, and the y-axis ticks now
  use `precision: 0` so whole-peso labels are enforced even once real,
  possibly small, net-pay data exists.

## Testing
Manually verified three scenarios against a local copy of the dev DB:
no payroll runs, draft-only runs with no payslips (the bug case), and
a processed run with a real payslip. Full suite re-run after the
change: 77 passed, 1 skipped (pre-existing WeasyPrint/Pango gap,
unrelated to this fix).

## Modified files
- `app/services/dashboard_service.py`
- `app/templates/main/dashboard.html`