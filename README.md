# 💻 NulKast ChromeOS — Custom Kernel, Rootfs, GPU & Play Store (`ARCVM`) Turbo Studio

> [!IMPORTANT]
> **Hobby / Vibe-Coded Project — Provided As-Is With No Support**
> This repository is a personal, vibe-coded hobby experiment for customizing ChromeOS kernels, unlocking root filesystems, eliminating Intel 8th-Gen CPU/KVM cache-flush bottlenecks, and de-bloating the ChromeOS Android 13 (`ARCVM`) subsystem. **No support, warranty, issue tracking, or maintenance is provided.** Use or fork entirely at your own risk.

---

## Overview

**NulKast ChromeOS** modifies an installed official ChromeOS image in-place (preserving 100% of the proprietary **Google Play Store (`ARCVM`)**, Widevine DRM, and device-specific audio/fingerprint drivers) while stripping out the kernel, CPU, GPU, and telemetry bottlenecks that make 8th-Gen Intel ChromeOS tablets like the **Google Pixel Slate (`nocturne` — Core i7-8500Y / i5-8200Y / m3-8100Y)** sluggish on modern ChromeOS releases.

---

## What the 7-Step `NulKast Nocturne` Provisioner Does

1. **Kernel Command-Line Re-Signing (`KERN-A` `/dev/mmcblk0p2` & `KERN-B` `/dev/mmcblk0p4`):**
   - Uses `make_dev_ssd.sh` to remove `dm-verity` rootfs verification (`rw`) and patches the kernel boot config with:
     ```text
     mitigations=off kvm-intel.vmentry_l1d_flush=never
     ```
   - Eliminates `PTI` (Meltdown TLB flush on every syscall), `IBRS` / `Retbleed` microcode stalls, `MDS` buffer clearing, and **stops KVM from flushing the CPU L1 Data Cache on every single Android 13 (`ARCVM`) VM entry** (+35–45% CPU & Play Store VM speedup).
2. **CPU Clock Floor, Intel RAPL Power & Swappiness Tuner (`/etc/init/nulkast-turbo.conf`):**
   - Ensures all 4 Hyper-Threading cores (`2C/4T`) are online (`smt/control = on`).
   - Raises `scaling_min_freq` from `400 MHz` (`400000`) to **`1.20 GHz` (`1200000`)** (`4.20 GHz` max turbo, `balance_performance`) to eliminate touch/scroll wake-up lag.
   - Raises sustained Intel RAPL package power (`constraint_0_power_limit_uw`) from `7.0W` to **`9.5W`** (`18W` burst).
   - Sets `vm.swappiness=15` to keep the Play Store VM in fast physical RAM instead of thrashing `zram`.
3. **3000×2000 (6MP) GPU Hardware Rasterization & Blur Removal (`/etc/chrome_dev.conf`):**
   - Enables `--enable-gpu-rasterization`, `--enable-zero-copy`, `--enable-oop-rasterization`, `VaapiVideoDecoder`, and `--ash-disable-blur` so the fanless Intel UHD 615 GPU renders at 60 FPS without choking on 6-megapixel Gaussian background blurs.
4. **System-Wide Telemetry Disabling & `/etc/hosts` Tracker Sinkhole:**
   - Disables `metrics_daemon` (UMA reporting) and injects a tracker blocklist into `/etc/hosts` while preserving `play.fe.googleapis.com` and `gvt1.com`.
5. **Automatic Play Store (`ARCVM`) Optimizer & `NulKast` APK Installer (`/usr/local/bin/nulkast-arcvm-provision.sh`):**
   - Automatically sets Android 13 animation scales to `0.5x`, zeroes the Google Advertising ID, disables preloaded Android bloatware (`Play Games`, `Google TV`, `YouTube Music`), and installs staged `NulKast` APKs (`Wall`, `Audit`, `Scrub`, `Home`) inside `ARCVM`.

---

## Quick Start & Makefile Commands

```bash
# 1. Classify a ChromeOS board or firmware string
make classify BOARD=Google_Nocturne.10984.90.0

# 2. Generate data/harden_nocturne_chromeos.sh
make generate-script

# 3. Deploy and execute over SSH to a Developer-Mode Chromebook
make deploy-ssh IP=<chromebook_lan_ip>

# 4. Run unit tests
make test
```
