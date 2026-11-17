function drawHistoryChart(samples) {
  const canvas = document.getElementById("chart");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const w = canvas.width;
  const h = canvas.height;
  ctx.clearRect(0, 0, w, h);

  // Grid lines
  ctx.strokeStyle = "#1e2b45";
  ctx.lineWidth = 1;
  for (let y = 30; y < h; y += 45) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(w, y);
    ctx.stroke();
  }

  // 65°C Thermal Clamp Reference Line
  const y65 = h - ((65 - 25) / 65) * (h - 30) - 15;
  ctx.strokeStyle = "rgba(244, 63, 94, 0.45)";
  ctx.setLineDash([4, 4]);
  ctx.beginPath();
  ctx.moveTo(0, y65);
  ctx.lineTo(w, y65);
  ctx.stroke();
  ctx.setLineDash([]);

  if (!samples || samples.length < 2) return;

  ctx.strokeStyle = "#00e5ff";
  ctx.lineWidth = 2.5;
  ctx.beginPath();
  samples.forEach((s, i) => {
    const x = (i / (samples.length - 1)) * (w - 24) + 12;
    const temp = Math.max(25, Math.min(90, s.temp_c || 40));
    const y = h - ((temp - 25) / 65) * (h - 30) - 15;
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();
}

async function refreshDashboard() {
  try {
    const res = await fetch(chrome.runtime.getURL("telemetry.json") + "?t=" + Date.now(), { cache: "no-store" });
    if (res.ok) {
      const d = await res.json();
      document.getElementById("hdr-sub").textContent = `${d.os_name || "NulKast OS 150"} • ${d.cpu_model || "Intel Core i7-8500Y"} (${d.board || "nocturne"}) • Updated ${d.ts || "live"}`;
      document.getElementById("hdr-badge").textContent = `${d.tier || "COOL_TURBO"} • ${d.temp_c ?? "--"}°C`;
      document.getElementById("d-temp").textContent = `${d.temp_c ?? "--"} °C`;
      document.getElementById("d-temp-sub").textContent = `Tier: ${d.tier || "COOL_TURBO"} (Clamp at 65°C)`;
      document.getElementById("d-freq").textContent = `${d.freq_mhz ?? "--"} MHz`;
      document.getElementById("d-watts").textContent = `RAPL Package: ${d.watts ?? "--"} W (PL1 ${d.pl1_w ?? 9}W)`;
      document.getElementById("d-ram").textContent = `${d.mem_used_mb ?? "--"} MB`;
      document.getElementById("d-ram-sub").textContent = `Free: ${d.mem_avail_mb ?? "--"} MB / ${d.mem_total_mb ?? 15948} MB`;
      const stripped = (d.debloated_daemons || 10) + (d.debloated_arcvm_pkgs || 20);
      document.getElementById("d-bloat").textContent = `${stripped} Stripped`;
      document.getElementById("d-bloat-sub").textContent = `${d.debloated_daemons || 10} Daemons + ${d.debloated_arcvm_pkgs || 20} ARCVM Apps + ${d.sinkholed_domains || 28} Hosts`;
    }
  } catch (e) {}

  try {
    const hRes = await fetch(chrome.runtime.getURL("history.json") + "?t=" + Date.now(), { cache: "no-store" });
    if (hRes.ok) {
      const samples = await hRes.json();
      drawHistoryChart(samples);
      const tbody = document.getElementById("history-rows");
      tbody.innerHTML = "";
      samples.slice().reverse().slice(0, 15).forEach((s) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td>${s.ts || ""}</td>
          <td>${s.tier || "COOL_TURBO"}</td>
          <td>${s.temp_c ?? "--"} °C</td>
          <td>${s.freq_mhz ?? "--"} MHz</td>
          <td>${s.watts ?? "--"} W</td>
          <td>${s.load_1m ?? "--"}</td>
          <td>${s.mem_used_mb ?? "--"} / ${s.mem_total_mb ?? 15948} MB</td>
        `;
        tbody.appendChild(tr);
      });
    }
  } catch (e) {}
}

refreshDashboard();
setInterval(refreshDashboard, 3000);
