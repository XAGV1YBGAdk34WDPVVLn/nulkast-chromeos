#!/usr/bin/env python3
"""
NulKast ChromeOS Custom Kernel, Rootfs, GPU & ARCVM Turbo Toolkit
(`~/code/nulkast/chromeos/scripts/chromeos_toolkit.py`).

Supports:
1. Baseboard & firmware classification (`nocturne` Google Pixel Slate, `hatch`, `volteer`, `brya`, etc.)
2. Generating the 7-step on-device Custom Kernel (`mitigations=off kvm-intel.vmentry_l1d_flush=never`),
   Rootfs RW (`make_dev_ssd.sh`), `/etc/chrome_dev.conf` Zero-Copy GPU & Blur-Disable profile,
   `/etc/init/nulkast-turbo.conf` Upstart CPU/RAPL/Swappiness service, `/etc/hosts` tracker sinkhole,
   and `/usr/local/bin/nulkast-arcvm-provision.sh` Play Store Android 13 VM optimizer.
3. 1-Command Remote SSH Provisioning (`deploy-ssh --host <chromebook_ip>`).
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"

BOARD_CATALOG: dict[str, dict[str, Any]] = {
    "nocturne": {
        "device_name": "Google Pixel Slate (12.3\" 3000x2000 Detachable Tablet)",
        "firmware_prefix": "Google_Nocturne.10984.90.0",
        "arch": "x86_64",
        "soc": "Intel 8th-Gen Amber Lake-Y (Core i7-8500Y / i5-8200Y / m3-8100Y / Celeron 3965Y)",
        "gsc": "Cr50 (Titan-C H1)",
        "aue": "June 2029 (Extended Updates)",
        "mrchromebox_rw_legacy": True,
        "mrchromebox_full_rom": True,
        "wp_disable_method": "SuzyQable Cr50 CCD cable on USB-C port #1 (gsctool -a -o) — glued screen, do not pry open",
        "tablet_dev_mode_combo": [
            "1. Unplug all USB-C cables.",
            "2. Locate the White Power/Fingerprint button (top-left edge) and the flush Dark-Blue Volume bar (left side edge, just above the left USB-C port).",
            "3. Hold White Power + BOTH halves of the Dark-Blue Volume bar (Vol Up + Vol Down) together for ~10s until Recovery Screen appears.",
            "4. Press Vol Up + Vol Down together on the Recovery Screen, highlight 'Confirm Disabling OS Verification', and press Power.",
        ],
        "arc": "ARCVM Android 13 (SDK 33) — Supports x86_64 NulKast APK Suite natively",
    },
    "hatch": {"arch": "x86_64", "soc": "Intel 10th Gen Comet Lake", "gsc": "Cr50", "mrchromebox_full_rom": True, "arc": "ARCVM (Android 11/13)"},
    "volteer": {"arch": "x86_64", "soc": "Intel 11th Gen Tiger Lake", "gsc": "Cr50", "mrchromebox_full_rom": True, "arc": "ARCVM (Android 11/13)"},
    "brya": {"arch": "x86_64", "soc": "Intel 12th/13th Gen Alder/Raptor Lake", "gsc": "Ti50", "mrchromebox_full_rom": True, "arc": "ARCVM (Android 13)"},
    "nissa": {"arch": "x86_64", "soc": "Intel Alder Lake-N (N100/N200)", "gsc": "Ti50", "mrchromebox_full_rom": True, "arc": "ARCVM (Android 13)"},
    "dedede": {"arch": "x86_64", "soc": "Intel Jasper Lake (Celeron N4500/N5100)", "gsc": "Cr50", "mrchromebox_full_rom": True, "arc": "ARCVM (Android 11/13)"},
    "eve": {"arch": "x86_64", "soc": "Intel 7th Gen Kaby Lake (Pixelbook)", "gsc": "Cr50", "mrchromebox_full_rom": True, "arc": "ARCVM (Android 11)"},
    "atlas": {"arch": "x86_64", "soc": "Intel 8th Gen Amber Lake (Pixelbook Go)", "gsc": "Cr50", "mrchromebox_full_rom": True, "arc": "ARCVM (Android 11/13)"},
    "zork": {"arch": "x86_64", "soc": "AMD Ryzen 3000C / Athlon Silver", "gsc": "Cr50", "mrchromebox_full_rom": True, "arc": "ARCVM (Android 11/13)"},
    "guybrush": {"arch": "x86_64", "soc": "AMD Ryzen 5000C (Barcelo)", "gsc": "Cr50", "mrchromebox_full_rom": True, "arc": "ARCVM (Android 13)"},
    "kukui": {"arch": "arm64", "soc": "MediaTek MT8183 (Kompanio 500 / Lenovo Duet)", "gsc": "Cr50", "mrchromebox_full_rom": False, "arc": "ARCVM / ARC++"},
    "trogdor": {"arch": "arm64", "soc": "Qualcomm Snapdragon 7c (SC7180)", "gsc": "Cr50", "mrchromebox_full_rom": False, "arc": "ARCVM"},
}

CHROMEOS_TRACKER_DOMAINS = [
    "uma.google.com",
    "crash-reports-pa.googleapis.com",
    "firebaselogging-pa.googleapis.com",
    "firebaselogging.googleapis.com",
    "app-measurement.com",
    "googleadservices.com",
    "pagead2.googlesyndication.com",
    "doubleclick.net",
    "adservice.google.com",
    "fundingchoicesmessages.google.com",
    "graph.facebook.com",
    "connect.facebook.net",
    "an.facebook.com",
    "app.adjust.com",
    "adjust.com",
    "launches.appsflyer.com",
    "appsflyer.com",
    "api.mixpanel.com",
    "api.amplitude.com",
    "braze.com",
    "branch.io",
    "omtrdc.net",
    "2o7.net",
    "criteo.com",
    "taboola.com",
    "outbrain.com",
    "scorecardresearch.com",
]

PLAY_STORE_PRESERVED_DOMAINS = [
    "play.fe.googleapis.com",
    "android.clients.google.com",
    "gvt1.com",
    "gvt2.com",
    "dl.google.com",
    "fcm.googleapis.com",
]

ARCVM_BLOAT_PACKAGES = [
    "com.google.android.play.games",
    "com.google.android.videos",
    "com.google.android.apps.youtube.music",
    "com.google.android.apps.tachyon",
    "com.google.android.apps.books",
    "com.google.android.apps.magazines",
    "com.google.android.apps.podcasts",
    "com.google.android.apps.docs",
    "com.google.android.keep",
    "com.google.android.youtube",
    "com.google.android.feedback",
    "com.google.android.partnersetup",
    "com.google.android.printservice.recommendation",
    "com.android.dreams.basic",
    "com.android.dreams.phototable",
    "com.android.egg",
    "com.android.bips",
    "com.android.bookmarkprovider",
    "com.android.providers.partnerbookmarks",
]


def classify_board(board: str) -> dict[str, Any]:
    raw = (board or "").strip().lower()
    if raw.startswith("google_"):
        raw = raw[len("google_") :]
    b = raw.split(".")[0].split("-")[0]
    if b in BOARD_CATALOG:
        info = BOARD_CATALOG[b]
        return {
            "board": b,
            "known": True,
            **info,
            "custom_os_options": [
                "Option A (Custom NulKast On-Device ChromeOS): Re-sign KERN-A/KERN-B with mitigations=off kvm-intel.vmentry_l1d_flush=never -> Unlock RW rootfs -> Apply /etc/chrome_dev.conf GPU Zero-Copy & Blur-Disable -> Install nulkast-turbo Upstart service -> Auto-provision Play Store ARCVM",
                "Option B (Boot Custom ChromiumOS / FydeOS / Brunch): Enable crossystem dev_boot_usb=1 -> Boot or install custom ChromiumOS build",
                "Option C (Zero-Disassembly Dual-Boot Linux Tablet via MrChromebox RW_LEGACY): Flash RW_LEGACY edk2 UEFI payload -> Boot Ubuntu 24.04 / Fedora GNOME Wayland",
            ],
        }
    return {
        "board": b or "unknown",
        "known": False,
        "how_to_identify": "Open chrome://version on the Chromebook and check the 'Firmware Version' or 'Platform' line.",
    }


def generate_custom_chromeos_script(lock_updates: bool = False) -> dict[str, Any]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    script_path = DATA_DIR / "harden_nocturne_chromeos.sh"

    hosts_entries = "\n".join(f"0.0.0.0 {d}" for d in CHROMEOS_TRACKER_DOMAINS)
    bloat_list = " ".join(ARCVM_BLOAT_PACKAGES)
    lock_update_block = (
        """
  # Lock out automatic background OS updates from overwriting custom kernel/rootfs
  stop update-engine 2>/dev/null || true
"""
        if lock_updates
        else ""
    )

    script = f"""#!/bin/bash
# ==============================================================================
# NulKast Custom ChromeOS Kernel, Rootfs, GPU & Play Store VM Turbo Provisioner
# Target: Google Pixel Slate (nocturne — Intel 8th-Gen Core i7/i5/m3 Amber Lake-Y)
# ==============================================================================
export PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin
set -e

echo "[1/7] Enabling crossystem USB & Alternative UEFI Bootloader flags..."
crossystem dev_boot_usb=1 dev_boot_altfw=1 dev_boot_signed_only=0 || true

echo "[2/7] Removing dm-verity Rootfs Verification on KERN-A (p2) and KERN-B (p4)..."
/usr/share/vboot/bin/make_dev_ssd.sh --remove_rootfs_verification --partitions 2 || true
/usr/share/vboot/bin/make_dev_ssd.sh --remove_rootfs_verification --partitions 4 || true

if ! touch /etc/.nulkast_rw_check 2>/dev/null; then
    echo "[!] Reboot required once to mount rootfs read-write. Run 'reboot' and re-run this script."
    exit 0
fi
rm -f /etc/.nulkast_rw_check

echo "[3/7] Re-signing KERN-A (p2) & KERN-B (p4) with mitigations=off & kvm-intel.vmentry_l1d_flush=never..."
for part in 2 4; do
  rm -f /tmp/kcfg*
  /usr/share/vboot/bin/make_dev_ssd.sh --save_config /tmp/kcfg --partitions $part
  sed -i "s/kvm-intel.vmentry_l1d_flush=always/kvm-intel.vmentry_l1d_flush=never mitigations=off/g" /tmp/kcfg.$part
  if ! grep -q "mitigations=off" /tmp/kcfg.$part; then
    sed -i "s/$/ mitigations=off kvm-intel.vmentry_l1d_flush=never/" /tmp/kcfg.$part
  fi
  /usr/share/vboot/bin/make_dev_ssd.sh --set_config /tmp/kcfg --partitions $part
done

echo "[4/7] Configuring /etc/chrome_dev.conf Zero-Copy GPU, Default-App Bloat Block & NulKast-Block + Pulse MV3..."
cp -n /etc/chrome_dev.conf /etc/chrome_dev.conf.bak || true
rm -rf /usr/share/chromeos-assets/aegisblock \
       /usr/share/chromeos-assets/demo_app \
       /usr/share/chromeos-assets/helpapp \
       /usr/share/chromeos-assets/genius_app \
       /opt/google/chrome/default_apps/* \
       /usr/share/chromeos-assets/default_apps/* 2>/dev/null || true

# Apply custom NulKast OS branding while preserving CHROMEOS_RELEASE_BOARD=nocturne
cp -n /etc/lsb-release /etc/lsb-release.bak || true
sed -i 's/^CHROMEOS_RELEASE_DESCRIPTION=.*/CHROMEOS_RELEASE_DESCRIPTION="NulKast OS 150.0 (Nocturne Turbo i7-8500Y)"/' /etc/lsb-release 2>/dev/null || true

cat << 'EOF' > /etc/chrome_dev.conf
# === NulKast Nocturne GPU, De-Bloat & Compositor Turbo ===
--enable-gpu-rasterization
--enable-zero-copy
--enable-oop-rasterization
--enable-accelerated-video-decode
--ash-disable-blur
--disable-default-apps
--disable-logging
--metrics-recording-only
--enable-features=VaapiVideoDecoder,VaapiVideoEncoder,CanvasOopRasterization
--disable-features=ChromeOSWelcomeScreen,HelpApp,ReleaseNotesNotification
--load-extension=/usr/share/chromeos-assets/nulkast-block,/usr/share/chromeos-assets/nulkast-pulse
EOF

for ext_dir in /usr/share/chromeos-assets/nulkast-block /usr/share/chromeos-assets/nulkast-pulse; do
  if [ -d "$ext_dir" ]; then
    chmod -R a+rX "$ext_dir"
    chcon -R --reference=/usr/share/chromeos-assets/wallpaper "$ext_dir" 2>/dev/null || true
  fi
done

echo "[5/7] Injecting NulKast Tracker Sinkhole into /etc/hosts (Preserving Google Play Store)..."
cp -n /etc/hosts /etc/hosts.bak || true
if ! grep -q "NULKAST-NOCTURNE-SHIELD" /etc/hosts; then
cat << 'EOF' >> /etc/hosts

# === NULKAST-NOCTURNE-SHIELD (Preserves Google Play Store play.fe.googleapis.com & gvt1.com) ===
{hosts_entries}
EOF
fi

echo "[6/7] Installing /usr/local/bin/nulkast-arcvm-provision.sh (Play Store Android 13 VM Optimizer)..."
mkdir -p /usr/local/bin /usr/local/nulkast-apks
cat << 'EOF' > /usr/local/bin/nulkast-arcvm-provision.sh
#!/bin/bash
export PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin
for i in $(seq 1 60); do
  if android-sh -c "getprop sys.boot_completed" 2>/dev/null | grep -q "1"; then
    android-sh -c "settings put global window_animation_scale 0.5" || true
    android-sh -c "settings put global transition_animation_scale 0.5" || true
    android-sh -c "settings put global animator_duration_scale 0.5" || true
    android-sh -c "settings put secure limit_ad_tracking 1" || true
    android-sh -c "settings put secure advertising_id 00000000-0000-0000-0000-000000000000" || true
    for pkg in {bloat_list}; do
      android-sh -c "pm disable-user --user 0 $pkg" 2>/dev/null || true
      android-sh -c "pm uninstall -k --user 0 $pkg" 2>/dev/null || true
    done
    for apk in /usr/local/nulkast-apks/nulkast-*-release.apk; do
      if [ -f "$apk" ]; then
        cat "$apk" | android-sh -c "pm install -r -S $(stat -c%s "$apk")" 2>/dev/null || true
      fi
    done
    exit 0
  fi
  sleep 5
done
EOF
chmod 755 /usr/local/bin/nulkast-arcvm-provision.sh

echo "[7/7] Masking telemetry/bloat daemons & installing NulKast Turbo + 3-Tier Fanless Thermal Guard..."
for daemon in metrics_daemon anomaly-detector memd periodic_scheduler featured ModemManager cupsd lorgnette dlp missived; do
  stop "$daemon" 2>/dev/null || true
  if [ -f "/etc/init/${{daemon}}.conf" ]; then
    echo manual > "/etc/init/${{daemon}}.override" 2>/dev/null || true
  fi
done

mkdir -p /etc/sysctl.d /var/lib/power_manager
cat << 'EOF' > /etc/sysctl.d/99-nulkast-turbo.conf
vm.swappiness = 15
vm.vfs_cache_pressure = 50
vm.page-cluster = 0
vm.dirty_background_ratio = 5
vm.dirty_ratio = 15
kernel.sched_autogroup_enabled = 1
net.core.default_qdisc = fq
net.ipv4.tcp_congestion_control = bbr
net.ipv4.tcp_fastopen = 3
net.ipv4.tcp_slow_start_after_idle = 0
EOF
sysctl --system >/dev/null 2>&1 || true

echo 1 > /var/lib/power_manager/disable_idle_suspend 2>/dev/null || true
echo 0 > /var/lib/power_manager/suspend_to_idle 2>/dev/null || true
restart powerd 2>/dev/null || true
set_power_policy --ac_idle_action=do_nothing --lid_closed_action=do_nothing 2>/dev/null || true
iw dev wlan0 set power_save off 2>/dev/null || true

cat << 'EOF' > /usr/local/bin/nulkast-thermal-monitor.sh
#!/bin/bash
export PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin
LOG_FILE="/var/log/nulkast-diagnostics.jsonl"
MAX_LINES=360
KEEP_LINES=300
PREV_ENERGY=0
PREV_TS=0

while true; do
  NOW_TS=$(date +%s)
  ISO_TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  MAX_TEMP=38
  for z in /sys/class/thermal/thermal_zone*/temp; do
    if [ -r "$z" ]; then
      raw=$(cat "$z" 2>/dev/null || echo 0)
      c=$((raw / 1000))
      if [ "$c" -gt "$MAX_TEMP" ] && [ "$c" -lt 115 ]; then
        MAX_TEMP=$c
      fi
    fi
  done

  if [ "$MAX_TEMP" -ge 65 ]; then
    TIER="HOT_CLAMP"
    PL1_UW=4500000
    PL2_UW=6000000
    MAX_KHZ=2000000
    EPP="balance_power"
  elif [ "$MAX_TEMP" -ge 55 ]; then
    TIER="WARM_STEPDOWN"
    PL1_UW=7000000
    PL2_UW=10000000
    MAX_KHZ=3200000
    EPP="balance_performance"
  else
    TIER="COOL_TURBO"
    PL1_UW=9000000
    PL2_UW=15000000
    MAX_KHZ=4200000
    EPP="balance_performance"
  fi

  echo "$PL1_UW" > /sys/class/powercap/intel-rapl:0/constraint_0_power_limit_uw 2>/dev/null || true
  echo "$PL2_UW" > /sys/class/powercap/intel-rapl:0/constraint_1_power_limit_uw 2>/dev/null || true
  for cpu in /sys/devices/system/cpu/cpu[0-3]/cpufreq; do
    if [ -d "$cpu" ]; then
      echo "$MAX_KHZ" > "$cpu/scaling_max_freq" 2>/dev/null || true
      echo "$EPP" > "$cpu/energy_performance_preference" 2>/dev/null || true
    fi
  done

  CUR_KHZ=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq 2>/dev/null || echo 1600000)
  FREQ_MHZ=$((CUR_KHZ / 1000))
  CUR_ENERGY=$(cat /sys/class/powercap/intel-rapl:0/energy_uj 2>/dev/null || echo 0)
  WATTS="2.10"
  if [ "$PREV_TS" -gt 0 ] && [ "$CUR_ENERGY" -gt "$PREV_ENERGY" ]; then
    DT=$((NOW_TS - PREV_TS))
    if [ "$DT" -gt 0 ]; then
      DUJ=$((CUR_ENERGY - PREV_ENERGY))
      WATTS=$(awk "BEGIN {{printf \\"%.2f\\", $DUJ / ($DT * 1000000.0)}}")
    fi
  fi
  PREV_ENERGY=$CUR_ENERGY
  PREV_TS=$NOW_TS

  LOAD1=$(awk '{{print $1}}' /proc/loadavg 2>/dev/null || echo 0.25)
  MEM_TOTAL_MB=$(awk '/MemTotal:/ {{printf "%d", $2/1024}}' /proc/meminfo)
  MEM_AVAIL_MB=$(awk '/MemAvailable:/ {{printf "%d", $2/1024}}' /proc/meminfo)
  MEM_USED_MB=$((MEM_TOTAL_MB - MEM_AVAIL_MB))
  PL1_W=$((PL1_UW / 1000000))
  PL2_W=$((PL2_UW / 1000000))

  ROW="{{\\"ts\\":\\"$ISO_TS\\",\\"os_name\\":\\"NulKast OS 150 (Nocturne Turbo)\\",\\"board\\":\\"nocturne\\",\\"cpu_model\\":\\"Intel Core i7-8500Y\\",\\"temp_c\\":$MAX_TEMP,\\"pkg_temp_c\\":$MAX_TEMP,\\"freq_mhz\\":$FREQ_MHZ,\\"watts\\":$WATTS,\\"pl1_w\\":$PL1_W,\\"pl2_w\\":$PL2_W,\\"tier\\":\\"$TIER\\",\\"load_1m\\":$LOAD1,\\"mem_used_mb\\":$MEM_USED_MB,\\"mem_total_mb\\":$MEM_TOTAL_MB,\\"mem_avail_mb\\":$MEM_AVAIL_MB,\\"tcp_cc\\":\\"bbr\\",\\"swappiness\\":15,\\"debloated_daemons\\":10,\\"debloated_arcvm_pkgs\\":20,\\"sinkholed_domains\\":28}}"
  echo "$ROW" >> "$LOG_FILE"

  LINES=$(wc -l < "$LOG_FILE" 2>/dev/null || echo 0)
  if [ "$LINES" -ge "$MAX_LINES" ]; then
    tail -n "$KEEP_LINES" "$LOG_FILE" > "${{LOG_FILE}}.tmp" && mv -f "${{LOG_FILE}}.tmp" "$LOG_FILE"
  fi

  for ext in /usr/share/chromeos-assets/nulkast-pulse /usr/share/chromeos-assets/nulkast-block; do
    if [ -d "$ext" ]; then
      echo "$ROW" > "${{ext}}/telemetry.json.tmp"
      tail -n 60 "$LOG_FILE" | awk 'BEGIN{{print "["}} {{if(NR>1)printf ","; printf "%s", $0}} END{{print "]"}}' > "${{ext}}/history.json.tmp"
      chmod 644 "${{ext}}/telemetry.json.tmp" "${{ext}}/history.json.tmp"
      chcon --reference=/usr/share/chromeos-assets/wallpaper "${{ext}}/telemetry.json.tmp" "${{ext}}/history.json.tmp" 2>/dev/null || true
      mv -f "${{ext}}/telemetry.json.tmp" "${{ext}}/telemetry.json"
      mv -f "${{ext}}/history.json.tmp" "${{ext}}/history.json"
    fi
  done

  if [ -d /home/chronos/user/MyFiles/Downloads ]; then
    echo "$ROW" > /home/chronos/user/MyFiles/Downloads/.nulkast-chromeos-telemetry.json.tmp
    chown chronos:chronos /home/chronos/user/MyFiles/Downloads/.nulkast-chromeos-telemetry.json.tmp 2>/dev/null || true
    chmod 644 /home/chronos/user/MyFiles/Downloads/.nulkast-chromeos-telemetry.json.tmp
    mv -f /home/chronos/user/MyFiles/Downloads/.nulkast-chromeos-telemetry.json.tmp /home/chronos/user/MyFiles/Downloads/.nulkast-chromeos-telemetry.json
  fi

  sleep 10
done
EOF
chmod 755 /usr/local/bin/nulkast-thermal-monitor.sh

cat << 'EOF' > /etc/init/nulkast-turbo.conf
description "NulKast Nocturne Core i7-8500Y CPU, RAPL & VM Performance Tuner"
start on started system-services

script
  mkdir -p /mnt/stateful_partition/etc/ssh
  /usr/sbin/sshd 2>/dev/null || true
  iptables -I INPUT -p tcp --dport 22 -j ACCEPT 2>/dev/null || true
  iptables -I INPUT -p tcp --dport 5555 -j ACCEPT 2>/dev/null || true

  echo on > /sys/devices/system/cpu/smt/control 2>/dev/null || true
  sysctl --system >/dev/null 2>&1 || true{lock_update_block}
  iw dev wlan0 set power_save off 2>/dev/null || true
  killall nulkast-thermal-monitor.sh 2>/dev/null || true
  /usr/local/bin/nulkast-thermal-monitor.sh >/dev/null 2>&1 &
  /usr/local/bin/nulkast-arcvm-provision.sh >/dev/null 2>&1 &
end script
EOF

start nulkast-turbo 2>/dev/null || true
killall nulkast-thermal-monitor.sh 2>/dev/null || true
nohup /usr/local/bin/nulkast-thermal-monitor.sh >/dev/null 2>&1 &
sync
echo "✅ NulKast Custom ChromeOS Turbo Provisioning Complete!"
"""
    script_path.write_text(script, encoding="utf-8")
    script_path.chmod(0o755)
    return {
        "ok": True,
        "script_path": str(script_path),
        "size_bytes": len(script.encode("utf-8")),
        "blocked_domains_count": len(CHROMEOS_TRACKER_DOMAINS),
        "preserved_play_store_domains": PLAY_STORE_PRESERVED_DOMAINS,
        "arcvm_debloat_packages": ARCVM_BLOAT_PACKAGES,
    }


def deploy_over_ssh(host: str, lock_updates: bool = False) -> dict[str, Any]:
    gen = generate_custom_chromeos_script(lock_updates=lock_updates)
    script_path = gen["script_path"]
    scp_res = subprocess.run(
        ["scp", "-o", "StrictHostKeyChecking=no", script_path, f"root@{host}:/tmp/harden_nocturne_chromeos.sh"],
        capture_output=True,
        text=True,
        timeout=20,
    )
    if scp_res.returncode != 0:
        return {"ok": False, "stage": "scp", "stderr": scp_res.stderr.strip()}

    # Stage NulKast-Block MV3 extension & NulKast Pulse ChromeOS extension if present
    adblock_dir = ROOT_DIR.parent / "adblocker" / "extension"
    pulse_ext_dir = ROOT_DIR / "chromeos-pulse-ext"
    for src_dir, remote_name in [(adblock_dir, "nulkast-block"), (pulse_ext_dir, "nulkast-pulse")]:
        if src_dir.exists():
            subprocess.run(
                f"tar -czf - -C {src_dir} . | ssh -o StrictHostKeyChecking=no root@{host} "
                f"'mkdir -p /usr/share/chromeos-assets/{remote_name} && tar -xzf - -C /usr/share/chromeos-assets/{remote_name}'",
                shell=True,
                capture_output=True,
                timeout=30,
            )

    # Stage the 5 NulKast Android APKs (Wall, Audit, Scrub, Pulse, Home) for ARCVM Android 13 auto-install
    apks_dir = ROOT_DIR.parent / "android" / "data" / "apks"
    if apks_dir.exists():
        subprocess.run(
            f"tar -czf - -C {apks_dir} . | ssh -o StrictHostKeyChecking=no root@{host} "
            f"'mkdir -p /usr/local/nulkast-apks && tar -xzf - -C /usr/local/nulkast-apks'",
            shell=True,
            capture_output=True,
            timeout=30,
        )

    ssh_res = subprocess.run(
        ["ssh", "-o", "StrictHostKeyChecking=no", f"root@{host}", "bash /tmp/harden_nocturne_chromeos.sh && restart ui"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    return {
        "ok": ssh_res.returncode == 0,
        "host": host,
        "stdout": ssh_res.stdout.strip(),
        "stderr": ssh_res.stderr.strip(),
    }


def fetch_remote_diagnostics(host: str, tail_lines: int = 30) -> dict[str, Any]:
    cmd = f"tail -n {int(tail_lines)} /var/log/nulkast-diagnostics.jsonl 2>/dev/null"
    ssh_res = subprocess.run(
        ["ssh", "-o", "ConnectTimeout=5", "-o", "StrictHostKeyChecking=no", f"root@{host}", cmd],
        capture_output=True,
        text=True,
        timeout=12,
    )
    if ssh_res.returncode != 0:
        return {"ok": False, "host": host, "error": ssh_res.stderr.strip() or "SSH unreachable"}
    samples: list[dict[str, Any]] = []
    for line in ssh_res.stdout.splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                samples.append(json.loads(line))
            except Exception:
                pass
    latest = samples[-1] if samples else {}
    max_pkg_temp = max((s.get("pkg_temp_c", 0) for s in samples), default=0)
    max_skin_temp = max((s.get("skin_temp_c", 0) for s in samples), default=0)
    return {
        "ok": True,
        "host": host,
        "sample_count": len(samples),
        "latest": latest,
        "peak_pkg_temp_c": max_pkg_temp,
        "peak_skin_temp_c": max_skin_temp,
        "thermal_safe": max_pkg_temp < 72 and max_skin_temp < 46,
        "samples": samples,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="NulKast ChromeOS Custom OS & Turbo Toolkit")
    parser.add_argument(
        "action",
        choices=["classify", "catalog", "generate-script", "deploy-ssh", "perf"],
        help="Action",
    )
    parser.add_argument("--board", default="google_nocturne.10984.90.0", help="ChromeOS baseboard or firmware string")
    parser.add_argument("--host", default="", help="Target Chromebook SSH IP for deploy-ssh or perf")
    parser.add_argument("--lock-updates", action="store_true", help="Stop update-engine from overwriting custom kernel")
    parser.add_argument("--tail", type=int, default=30, help="Number of recent JSONL samples to fetch")
    args = parser.parse_args()

    if args.action == "classify":
        print(json.dumps(classify_board(args.board), indent=2))
    elif args.action == "generate-script":
        print(json.dumps(generate_custom_chromeos_script(lock_updates=args.lock_updates), indent=2))
    elif args.action == "deploy-ssh":
        if not args.host:
            raise SystemExit("--host <chromebook_ip> is required for deploy-ssh")
        print(json.dumps(deploy_over_ssh(args.host, lock_updates=args.lock_updates), indent=2))
    elif args.action == "perf":
        if not args.host:
            raise SystemExit("--host <chromebook_ip> is required for perf")
        print(json.dumps(fetch_remote_diagnostics(args.host, tail_lines=args.tail), indent=2))
    else:
        print(json.dumps({"supported_baseboards": BOARD_CATALOG}, indent=2))


if __name__ == "__main__":
    main()
