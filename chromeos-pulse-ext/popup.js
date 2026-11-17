async function loadTelemetry() {
  try {
    const res = await fetch(chrome.runtime.getURL("telemetry.json") + "?t=" + Date.now(), { cache: "no-store" });
    if (!res.ok) return;
    const d = await res.json();
    document.getElementById("os-sub").textContent = `${d.os_name || "NulKast OS"} • ${d.cpu_model || "i7-8500Y"}`;
    const tierBadge = document.getElementById("tier-badge");
    tierBadge.textContent = d.tier || "COOL_TURBO";
    if ((d.temp_c || 0) >= 65) {
      tierBadge.style.color = "#f43f5e";
      tierBadge.style.borderColor = "#f43f5e";
    } else if ((d.temp_c || 0) >= 55) {
      tierBadge.style.color = "#f59e0b";
      tierBadge.style.borderColor = "#f59e0b";
    } else {
      tierBadge.style.color = "#10b981";
      tierBadge.style.borderColor = "#10b981";
    }
    document.getElementById("val-temp").textContent = `${d.temp_c ?? "--"} °C`;
    document.getElementById("sub-temp").textContent = `Load 1m: ${d.load_1m ?? "--"} | Ceiling: 65°C`;
    document.getElementById("val-freq").textContent = `${d.freq_mhz ?? "--"} MHz`;
    document.getElementById("sub-watts").textContent = `RAPL: ${d.watts ?? "--"} W (PL1 ${d.pl1_w ?? 9}W)`;
    document.getElementById("val-ram").textContent = `${d.mem_used_mb ?? "--"} MB`;
    document.getElementById("sub-ram").textContent = `of ${d.mem_total_mb ?? 15948} MB (${d.mem_avail_mb ?? "--"} MB Free)`;
    const totalStripped = (d.debloated_daemons || 10) + (d.debloated_arcvm_pkgs || 20);
    document.getElementById("val-debloat").textContent = `${totalStripped} Stripped`;
    document.getElementById("sub-debloat").textContent = `${d.debloated_daemons || 10} Daemons + ${d.debloated_arcvm_pkgs || 20} Bloat Apps`;
  } catch (e) {
    // Fallback when telemetry.json is initializing
  }
}

document.getElementById("btn-refresh").addEventListener("click", loadTelemetry);
document.getElementById("btn-dashboard").addEventListener("click", () => {
  chrome.tabs.create({ url: chrome.runtime.getURL("dashboard.html") });
});

loadTelemetry();
setInterval(loadTelemetry, 3000);
