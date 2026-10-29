// SPDX-License-Identifier: MIT - see the LICENSE file
// script.js - SimClock web page logic
(function () {
  "use strict";
  var $ = function (id) { return document.getElementById(id); };

  // ---- fill the select boxes -------------------------------------------
  function addOption(sel, value, label) {
    var o = document.createElement("option");
    o.value = value;
    o.textContent = label;
    sel.appendChild(o);
  }
  var h, m;
  for (h = 1; h <= 12; h++) addOption($("hour"), h, String(h));
  for (m = 0; m < 60; m++) addOption($("minute"), m, (m < 10 ? "0" : "") + m);

  // ---- pre-fill from THIS device's clock ---------------------------------
  function pad(n) { return (n < 10 ? "0" : "") + n; }

  function fillFromDevice() {
    var now = new Date();
    var h24 = now.getHours();
    $("hour").value = String(h24 % 12 || 12);
    $("minute").value = String(now.getMinutes());
    $("ampm").value = h24 < 12 ? "AM" : "PM";
    $("date").value = now.getFullYear() + "-" + pad(now.getMonth() + 1) + "-" + pad(now.getDate());
  }
  fillFromDevice();

  // ---- status line --------------------------------------------------------
  var statusTimer = null;
  function setStatus(msg, isError) {
    var el = $("status");
    el.textContent = msg;
    el.className = isError ? "error" : "";
    clearTimeout(statusTimer);
    statusTimer = setTimeout(function () { el.textContent = ""; }, 4000);
  }

  function post(url, data) {
    return fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data || {})
    }).then(function (r) {
      return r.json().then(function (j) { return { ok: r.ok && j.ok, json: j }; });
    });
  }

  // ---- Set button -----------------------------------------------------------
  $("set-form").addEventListener("submit", function (e) {
    e.preventDefault();
    var d = $("date").value;
    if (!d) { setStatus("Please choose a date.", true); return; }
    var p = d.split("-");
    var hour = Number($("hour").value) % 12;
    if ($("ampm").value === "PM") hour += 12;
    post("/api/set", {
      y: Number(p[0]), mo: Number(p[1]), d: Number(p[2]),
      h: hour, mi: Number($("minute").value)
    }).then(function (res) {
      if (res.ok) setStatus("Clock set.");
      else setStatus((res.json && res.json.error) || "Could not set the clock.", true);
    }).catch(function () { setStatus("Could not reach the clock.", true); });
  });

  // ---- Fast-forward button ------------------------------------------------
  $("ff-btn").addEventListener("click", function () {
    post("/api/ff").then(function (res) {
      if (res.ok) setStatus("Skipped ahead 5 minutes.");
      else setStatus("Could not fast-forward.", true);
    }).catch(function () { setStatus("Could not reach the clock.", true); });
  });

  // ---- live readout ---------------------------------------------------------
  function poll() {
    fetch("/api/time", { cache: "no-store" })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        $("live-time").textContent = j.time;
        $("live-date").textContent = j.date;
      })
      .catch(function () { $("live-time").textContent = "-- not connected --"; })
      .then(function () { setTimeout(poll, 500); });
  }
  poll();
})();
