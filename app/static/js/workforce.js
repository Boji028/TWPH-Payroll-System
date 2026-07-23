// app/static/js/workforce.js
// Polls /workforce/data on an interval and re-renders a table body.
// Shared by the full Workforce page and the dashboard widget - both
// just point it at a different container/URL. No framework, per
// project convention (see CLAUDE.md).
(function () {
  function renderRows(tbody, employees) {
    if (!employees.length) {
      tbody.innerHTML = '<tr><td colspan="4" class="text-muted">No active employees.</td></tr>';
      return;
    }
    var html = '';
    employees.forEach(function (e) {
      html +=
        '<tr>' +
        '<td>' + e.full_name + '<div class="text-muted small">' + e.employee_code + '</div></td>' +
        '<td>' + e.position + '</td>' +
        '<td>' + e.department + '</td>' +
        '<td><span class="badge ' + e.badge_class + '">' + e.status_label + '</span></td>' +
        '</tr>';
    });
    tbody.innerHTML = html;
  }

  function tick(tbody, url, timestampEl) {
    fetch(url)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        renderRows(tbody, data.employees);
        if (timestampEl) {
          var t = new Date(data.generated_at);
          timestampEl.textContent = 'Updated ' + t.toLocaleTimeString();
        }
      })
      .catch(function () {
        // Poll failed silently - keep showing the last good render
        // rather than clearing the table on a transient network blip.
      });
  }

  window.initWorkforceWidget = function (opts) {
    var tbody = document.getElementById(opts.tableBodyId);
    var timestampEl = opts.timestampId ? document.getElementById(opts.timestampId) : null;
    if (!tbody) return;
    tick(tbody, opts.dataUrl, timestampEl);
    setInterval(function () {
      tick(tbody, opts.dataUrl, timestampEl);
    }, opts.intervalMs || 20000);
  };
})();
