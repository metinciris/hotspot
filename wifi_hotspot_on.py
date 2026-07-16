# -*- coding: utf-8 -*-
# Windows 10 Mobil Etkin Nokta otomasyonu - sürüm 4
#
# Elle test:
#     py "C:\pyton\wifi_hotspot_on.py"
#
# Başlangıç görevini kur:
#     py "C:\pyton\wifi_hotspot_on.py" --install
#
# Görevi kaldır:
#     py "C:\pyton\wifi_hotspot_on.py" --remove

import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path


TASK_NAME = "WiFi_Mobil_Etkin_Nokta_Ac"
SCRIPT_PATH = Path(__file__).resolve()

LOG_DIR = Path(
    os.environ.get("LOCALAPPDATA", str(Path.home()))
) / "WiFiHotspotAuto"

# Her ay ayrı günlük oluşturulur. Yalnızca içinde bulunulan ay tutulur.
LOG_FILE = LOG_DIR / f"hotspot-{datetime.now():%Y-%m}.log"
MAX_LOG_BYTES = 1_000_000

STARTUP_WAIT_SECONDS = 10
MAX_PYTHON_ATTEMPTS = 3


POWERSHELL_SCRIPT = r'''
$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.Runtime.WindowsRuntime

[Windows.Networking.Connectivity.NetworkInformation,Windows.Networking.Connectivity,ContentType=WindowsRuntime] > $null
[Windows.Networking.NetworkOperators.NetworkOperatorTetheringManager,Windows.Networking.NetworkOperators,ContentType=WindowsRuntime] > $null


function Get-TetheringBundle {
    $profile = [Windows.Networking.Connectivity.NetworkInformation]::GetInternetConnectionProfile()

    if ($null -eq $profile) {
        throw "Aktif internet baglanti profili bulunamadi."
    }

    $capability = [Windows.Networking.NetworkOperators.NetworkOperatorTetheringManager]::GetTetheringCapabilityFromConnectionProfile($profile)

    Write-Host "Internet profili: $($profile.ProfileName)"
    Write-Host "Tethering yetenegi: $capability"

    if ($capability.ToString() -ne "Enabled") {
        throw "Bu internet profili icin tethering kullanilamiyor. Durum: $capability"
    }

    $manager = [Windows.Networking.NetworkOperators.NetworkOperatorTetheringManager]::CreateFromConnectionProfile($profile)

    if ($null -eq $manager) {
        throw "Tethering yoneticisi olusturulamadi."
    }

    return [PSCustomObject]@{
        Profile = $profile
        Manager = $manager
    }
}


function Get-HotspotState {
    param(
        [Parameter(Mandatory = $true)]
        $Manager
    )

    return $Manager.TetheringOperationalState.ToString()
}


function Disable-AutoTimeout {
    try {
        # Bu metot statiktir; manager nesnesi üzerinden çağrılmaz.
        [Windows.Networking.NetworkOperators.NetworkOperatorTetheringManager]::DisableNoConnectionsTimeout()
        Write-Host "Baglanti yokken otomatik kapanma devre disi birakildi."
    }
    catch {
        # Bazı eski Windows 10 derlemelerinde bu API bulunmayabilir.
        Write-Host "Otomatik kapanma API'si kullanilamadi: $($_.Exception.Message)"
    }
}


Write-Host "PowerShell betigi basladi."

foreach ($serviceName in @("icssvc", "SharedAccess")) {
    try {
        $service = Get-Service -Name $serviceName -ErrorAction Stop

        if ($service.Status -ne "Running") {
            Start-Service -Name $serviceName -ErrorAction Stop
            Start-Sleep -Seconds 1
        }

        $currentStatus = (Get-Service -Name $serviceName).Status
        Write-Host "Servis $serviceName durumu: $currentStatus"
    }
    catch {
        Write-Host "Servis $serviceName baslatilamadi: $($_.Exception.Message)"
    }
}


$bundle = Get-TetheringBundle
$manager = $bundle.Manager
$state = Get-HotspotState -Manager $manager

Write-Host "Baslangic durumu: $state"

if ($state -eq "On") {
    Disable-AutoTimeout
    Write-Host "DOGRULANDI: Mobil etkin nokta zaten acik."
    exit 0
}


# Olası yarım kalmış oturumu temizle.
# WinRT AsTask kullanılmaz; durum doğrudan yöneticiden izlenir.
try {
    $stopOperation = $manager.StopTetheringAsync()
    Write-Host "Durdurma istegi gonderildi."

    for ($second = 1; $second -le 5; $second++) {
        Start-Sleep -Milliseconds 500

        $bundle = Get-TetheringBundle
        $manager = $bundle.Manager
        $state = Get-HotspotState -Manager $manager

        if ($state -eq "Off") {
            Write-Host "On temizleme tamamlandi: Off"
            break
        }
    }
}
catch {
    Write-Host "On temizleme durdurmasi atlandi: $($_.Exception.Message)"
}


$bundle = Get-TetheringBundle
$manager = $bundle.Manager

Write-Host "Acma istegi gonderiliyor."
$startOperation = $manager.StartTetheringAsync()

# StartTetheringAsync çağrısı işlemi başlatır.
# PowerShell'in WinRT AsTask uyumsuzluğu yerine gerçek durum izlenir.
for ($tick = 1; $tick -le 40; $tick++) {
    Start-Sleep -Milliseconds 500

    $bundle = Get-TetheringBundle
    $manager = $bundle.Manager
    $state = Get-HotspotState -Manager $manager

    Write-Host "Dogrulama $($tick * 0.5) sn: $state"

    if ($state -eq "On") {
        Disable-AutoTimeout
        Write-Host "DOGRULANDI: Mobil etkin nokta acik."
        exit 0
    }
}


$operationStatus = "Bilinmiyor"

try {
    $operationStatus = $startOperation.Status
}
catch {
    $operationStatus = "Okunamadi"
}

throw (
    "Mobil etkin nokta 20 saniye icinde On durumuna gecmedi. " +
    "Son durum: $state. Async durum: $operationStatus"
)
'''


def clean_old_logs() -> None:
    """Yalnızca içinde bulunulan aya ait günlük dosyasını tutar."""
    current_log_name = f"hotspot-{datetime.now():%Y-%m}.log"

    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)

        for old_log in LOG_DIR.glob("hotspot-*.log"):
            if old_log.name != current_log_name:
                old_log.unlink(missing_ok=True)

        # Eski tek dosya adını kullanan sürümlerin günlüğünü de kaldır.
        legacy_log = LOG_DIR / "hotspot.log"
        legacy_log.unlink(missing_ok=True)
    except OSError:
        pass


def limit_log_size(log_path: Path) -> None:
    """Aylık günlük 1 MB'ı aşarsa en yeni yaklaşık 500 KB'ı korur."""
    try:
        if not log_path.exists() or log_path.stat().st_size <= MAX_LOG_BYTES:
            return

        with log_path.open("rb") as log_file:
            log_file.seek(-500_000, os.SEEK_END)
            recent_data = log_file.read()

        # İlk yarım satırı atarak kaydın temiz bir satırdan başlamasını sağla.
        first_newline = recent_data.find(b"\n")
        if first_newline >= 0:
            recent_data = recent_data[first_newline + 1:]

        header = (
            f"[{datetime.now():%Y-%m-%d %H:%M:%S}] "
            "Günlük 1 MB sınırını aştığı için eski kayıtlar temizlendi.\n"
        ).encode("utf-8")

        with log_path.open("wb") as log_file:
            log_file.write(header)
            log_file.write(recent_data)
    except OSError:
        pass


def write_log(message: str) -> None:
    try:
        clean_old_logs()

        # Ay değişmişse çalışmakta olan süreçte dosya yolunu yeniden hesapla.
        log_path = LOG_DIR / f"hotspot-{datetime.now():%Y-%m}.log"
        limit_log_size(log_path)

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with log_path.open("a", encoding="utf-8") as log_file:
            for line in message.splitlines() or [""]:
                log_file.write(f"[{timestamp}] {line}\n")
    except OSError:
        pass


def run_powershell_script() -> subprocess.CompletedProcess[str]:
    script_path: Path | None = None
    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".ps1",
            prefix="wifi_hotspot_",
            delete=False,
            encoding="utf-8-sig",
            newline="\r\n",
        ) as script_file:
            script_file.write(POWERSHELL_SCRIPT)
            script_path = Path(script_file.name)

        return subprocess.run(
            [
                "powershell.exe",
                "-NoLogo",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(script_path),
            ],
            text=True,
            capture_output=True,
            timeout=60,
            creationflags=creation_flags,
        )
    finally:
        if script_path is not None:
            try:
                script_path.unlink(missing_ok=True)
            except OSError:
                pass


def enable_hotspot() -> bool:
    try:
        result = run_powershell_script()
    except subprocess.TimeoutExpired:
        write_log("HATA: PowerShell işlemi 60 saniyede tamamlanamadı.")
        return False
    except OSError as error:
        write_log(f"HATA: PowerShell çalıştırılamadı: {error}")
        return False

    stdout = result.stdout.strip()
    stderr = result.stderr.strip()

    if stdout:
        write_log(stdout)

    if result.returncode == 0 and "DOGRULANDI:" in stdout:
        return True

    write_log(
        "HATA: " +
        (stderr or "PowerShell gerçek On durumunu doğrulayamadı.")
    )
    return False


def get_pythonw_path() -> Path:
    python_path = Path(sys.executable)
    pythonw_path = python_path.with_name("pythonw.exe")
    return pythonw_path if pythonw_path.exists() else python_path


def install_startup_task() -> bool:
    pythonw_path = get_pythonw_path()
    task_action = f'"{pythonw_path}" "{SCRIPT_PATH}" --startup'

    result = subprocess.run(
        [
            "schtasks.exe",
            "/Create",
            "/TN",
            TASK_NAME,
            "/TR",
            task_action,
            "/SC",
            "ONLOGON",
            "/DELAY",
            "0000:45",
            "/RL",
            "HIGHEST",
            "/IT",
            "/F",
        ],
        text=True,
        capture_output=True,
    )

    if result.returncode == 0:
        print("Otomatik görev oluşturuldu.")
        print("Oturum açıldıktan yaklaşık 45 saniye sonra çalışacak.")
        print(f"Betik: {SCRIPT_PATH}")
        print(f"Günlük: {LOG_FILE}")
        return True

    print("Görev oluşturulamadı.")
    print(result.stderr.strip() or result.stdout.strip())
    print("Komut İstemi'ni yönetici olarak açıp yeniden deneyin.")
    return False


def remove_startup_task() -> bool:
    result = subprocess.run(
        [
            "schtasks.exe",
            "/Delete",
            "/TN",
            TASK_NAME,
            "/F",
        ],
        text=True,
        capture_output=True,
    )

    if result.returncode == 0:
        print("Otomatik görev kaldırıldı.")
        return True

    print("Görev kaldırılamadı veya görev bulunamadı.")
    print(result.stderr.strip() or result.stdout.strip())
    return False


def main() -> int:
    arguments = {argument.lower() for argument in sys.argv[1:]}

    if "--install" in arguments:
        return 0 if install_startup_task() else 1

    if "--remove" in arguments:
        return 0 if remove_startup_task() else 1

    if "--startup" in arguments:
        time.sleep(STARTUP_WAIT_SECONDS)

    write_log("=== WiFi hotspot betigi surum 5 ===")

    for attempt in range(1, MAX_PYTHON_ATTEMPTS + 1):
        write_log(f"Python denemesi {attempt}/{MAX_PYTHON_ATTEMPTS} başladı.")

        if enable_hotspot():
            write_log("SONUC: Mobil etkin nokta gerçek On durumunda doğrulandı.")
            return 0

        if attempt < MAX_PYTHON_ATTEMPTS:
            write_log("Başarısız; 10 saniye sonra yeniden denenecek.")
            time.sleep(10)

    write_log("SONUC: Mobil etkin nokta açılamadı.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
