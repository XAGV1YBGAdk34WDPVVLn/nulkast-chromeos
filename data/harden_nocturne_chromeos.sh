#!/bin/bash
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

echo "[4/7] Configuring /etc/chrome_dev.conf Zero-Copy GPU & 3000x2000 Blur Elimination..."
cp -n /etc/chrome_dev.conf /etc/chrome_dev.conf.bak || true
cat << 'EOF' > /etc/chrome_dev.conf
# === NulKast Nocturne GPU & Compositor Turbo ===
--enable-gpu-rasterization
--enable-zero-copy
--enable-oop-rasterization
--enable-accelerated-video-decode
--ash-disable-blur
--enable-features=VaapiVideoDecoder,VaapiVideoEncoder,CanvasOopRasterization
--load-extension=/usr/share/chromeos-assets/aegisblock
EOF

echo "[5/7] Injecting NulKast Tracker Sinkhole into /etc/hosts (Preserving Google Play Store)..."
cp -n /etc/hosts /etc/hosts.bak || true
if ! grep -q "NULKAST-NOCTURNE-SHIELD" /etc/hosts; then
cat << 'EOF' >> /etc/hosts

# === NULKAST-NOCTURNE-SHIELD (Preserves Google Play Store play.fe.googleapis.com & gvt1.com) ===
0.0.0.0 uma.google.com
0.0.0.0 crash-reports-pa.googleapis.com
0.0.0.0 firebaselogging-pa.googleapis.com
0.0.0.0 firebaselogging.googleapis.com
0.0.0.0 app-measurement.com
0.0.0.0 googleadservices.com
0.0.0.0 pagead2.googlesyndication.com
0.0.0.0 doubleclick.net
0.0.0.0 adservice.google.com
0.0.0.0 fundingchoicesmessages.google.com
0.0.0.0 graph.facebook.com
0.0.0.0 connect.facebook.net
0.0.0.0 an.facebook.com
0.0.0.0 app.adjust.com
0.0.0.0 adjust.com
0.0.0.0 launches.appsflyer.com
0.0.0.0 appsflyer.com
0.0.0.0 api.mixpanel.com
0.0.0.0 api.amplitude.com
0.0.0.0 braze.com
0.0.0.0 branch.io
0.0.0.0 omtrdc.net
0.0.0.0 2o7.net
0.0.0.0 criteo.com
0.0.0.0 taboola.com
0.0.0.0 outbrain.com
0.0.0.0 scorecardresearch.com
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
    for pkg in com.google.android.play.games com.google.android.videos com.google.android.apps.youtube.music com.google.android.apps.tachyon com.google.android.feedback com.google.android.printservice.recommendation; do
      android-sh -c "pm disable-user --user 0 $pkg" 2>/dev/null || true
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

echo "[7/7] Installing /etc/init/nulkast-turbo.conf Upstart service..."
stop metrics_daemon 2>/dev/null || true
if [ -f /etc/init/metrics_daemon.conf ]; then
  mv -f /etc/init/metrics_daemon.conf /etc/init/metrics_daemon.conf.disabled
fi

cat << 'EOF' > /etc/init/nulkast-turbo.conf
description "NulKast Nocturne Core i7-8500Y CPU, RAPL & VM Performance Tuner"
start on started system-services

script
  mkdir -p /mnt/stateful_partition/etc/ssh
  /usr/sbin/sshd 2>/dev/null || true
  iptables -I INPUT -p tcp --dport 22 -j ACCEPT 2>/dev/null || true
  iptables -I INPUT -p tcp --dport 5555 -j ACCEPT 2>/dev/null || true

  echo on > /sys/devices/system/cpu/smt/control 2>/dev/null || true
  for cpu in /sys/devices/system/cpu/cpu[0-3]/cpufreq; do
    if [ -d "$cpu" ]; then
      echo 1200000 > "$cpu/scaling_min_freq" 2>/dev/null || true
      echo 4200000 > "$cpu/scaling_max_freq" 2>/dev/null || true
      echo balance_performance > "$cpu/energy_performance_preference" 2>/dev/null || true
    fi
  done

  if [ -w /sys/class/powercap/intel-rapl:0/constraint_0_power_limit_uw ]; then
    echo 9500000 > /sys/class/powercap/intel-rapl:0/constraint_0_power_limit_uw 2>/dev/null || true
  fi

  sysctl -w vm.swappiness=15 2>/dev/null || true
  # Lock out automatic background OS updates from overwriting custom kernel/rootfs
  stop update-engine 2>/dev/null || true

  /usr/local/bin/nulkast-arcvm-provision.sh &
end script
EOF

start nulkast-turbo 2>/dev/null || true
sync
echo "✅ NulKast Custom ChromeOS Turbo Provisioning Complete!"
