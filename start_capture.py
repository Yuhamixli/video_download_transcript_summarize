"""
一键启动: 设置 Windows 代理 → 安装 CA 证书 → 启动 mitmproxy 捕获
参考 res-downloader 的 system_windows.go 和 proxy.go
"""

import subprocess
import shutil
import sys
import os
import time
import signal
import ctypes
import winreg

PROXY_HOST = "127.0.0.1"
PROXY_PORT = 8899
MITMPROXY_CA_DIR = os.path.join(os.path.expanduser("~"), ".mitmproxy")
MITMPROXY_CA_CERT = os.path.join(MITMPROXY_CA_DIR, "mitmproxy-ca-cert.cer")
ADDON_SCRIPT = os.path.join(os.path.dirname(__file__), "capture_addon.py")


def _mitmdump_cmd():
    """Find the mitmdump executable: direct command or python -m fallback."""
    mitmdump = shutil.which("mitmdump")
    if mitmdump:
        return [mitmdump]
    venv_bin = os.path.join(os.path.dirname(sys.executable), "mitmdump")
    if os.path.exists(venv_bin) or os.path.exists(venv_bin + ".exe"):
        return [venv_bin]
    return [sys.executable, "-m", "mitmproxy.tools.dump"]


def is_admin():
    """检查是否以管理员权限运行"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def set_windows_proxy(enable: bool, host: str = PROXY_HOST, port: int = PROXY_PORT):
    """设置/取消 Windows 系统代理 (参考 res-downloader system_windows.go)"""
    internet_settings = winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
        0, winreg.KEY_ALL_ACCESS,
    )
    try:
        if enable:
            winreg.SetValueEx(internet_settings, "ProxyEnable", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(internet_settings, "ProxyServer", 0, winreg.REG_SZ, f"{host}:{port}")
            print(f"[OK] Windows 系统代理已设置: {host}:{port}")
        else:
            winreg.SetValueEx(internet_settings, "ProxyEnable", 0, winreg.REG_DWORD, 0)
            print("[OK] Windows 系统代理已关闭")
    finally:
        winreg.CloseKey(internet_settings)

    # 通知系统设置已更改
    import ctypes
    INTERNET_OPTION_SETTINGS_CHANGED = 39
    INTERNET_OPTION_REFRESH = 37
    internet_set_option = ctypes.windll.Wininet.InternetSetOptionW
    internet_set_option(0, INTERNET_OPTION_SETTINGS_CHANGED, 0, 0)
    internet_set_option(0, INTERNET_OPTION_REFRESH, 0, 0)


def generate_mitmproxy_ca():
    """首次运行生成 CA 证书"""
    if os.path.exists(MITMPROXY_CA_CERT):
        print(f"[OK] CA 证书已存在: {MITMPROXY_CA_CERT}")
        return True

    print("[...] 首次运行，生成 mitmproxy CA 证书...")
    cmd = _mitmdump_cmd() + ["--listen-port", "18888"]
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
    )
    time.sleep(5)
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()

    if os.path.exists(MITMPROXY_CA_CERT):
        print(f"[OK] CA 证书已生成: {MITMPROXY_CA_CERT}")
        return True
    else:
        print("[ERROR] CA 证书生成失败")
        return False


def install_ca_cert():
    """安装 CA 证书到 Windows 受信任根证书存储"""
    if not os.path.exists(MITMPROXY_CA_CERT):
        print("[ERROR] CA 证书不存在，请先生成")
        return False

    print("[...] 安装 CA 证书到系统...")
    try:
        result = subprocess.run(
            ["certutil", "-addstore", "-user", "Root", MITMPROXY_CA_CERT],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            print("[OK] CA 证书安装成功")
            return True
        else:
            print(f"[WARN] certutil 返回码: {result.returncode}")
            print(f"  stdout: {result.stdout}")
            print(f"  stderr: {result.stderr}")
            # 尝试用管理员权限安装到 LocalMachine
            if is_admin():
                result2 = subprocess.run(
                    ["certutil", "-addstore", "Root", MITMPROXY_CA_CERT],
                    capture_output=True, text=True,
                )
                if result2.returncode == 0:
                    print("[OK] CA 证书安装到 LocalMachine 成功")
                    return True
            return False
    except Exception as e:
        print(f"[ERROR] 安装 CA 证书失败: {e}")
        return False


def start_mitmdump():
    """启动 mitmdump 代理"""
    print(f"\n{'='*60}")
    print(f" mitmproxy 代理启动中... 端口: {PROXY_PORT}")
    print(f" 请在微信中打开课程视频播放")
    print(f" 按 Ctrl+C 停止捕获")
    print(f"{'='*60}\n")

    cmd = _mitmdump_cmd() + [
        "--listen-host", PROXY_HOST,
        "--listen-port", str(PROXY_PORT),
        "--set", "connection_strategy=lazy",
        "--set", f"confdir={MITMPROXY_CA_DIR}",
        "--set", "http2=false",
        "-s", ADDON_SCRIPT,
    ]

    try:
        proc = subprocess.Popen(cmd)
        proc.wait()
    except KeyboardInterrupt:
        print("\n[...] 正在停止代理...")
        proc.terminate()
        proc.wait(timeout=10)


def cleanup():
    """清理: 关闭系统代理"""
    print("\n[...] 清理: 关闭系统代理...")
    try:
        set_windows_proxy(False)
    except Exception as e:
        print(f"[WARN] 关闭代理失败: {e}")
        print("  请手动关闭: 设置 → 网络和 Internet → 代理 → 关闭")


def main():
    print("=" * 60)
    print(" 微信课程视频捕获工具")
    print(" 参考 res-downloader 3.1.3 核心逻辑")
    print("=" * 60)
    print()

    # Step 1: 生成 CA 证书
    print("[Step 1/4] 检查 CA 证书...")
    if not generate_mitmproxy_ca():
        print("[ERROR] 无法生成 CA 证书，退出")
        return

    # Step 2: 安装 CA 证书
    print("\n[Step 2/4] 安装 CA 证书...")
    install_ca_cert()

    # Step 3: 设置系统代理
    print("\n[Step 3/4] 设置系统代理...")
    set_windows_proxy(True)

    # Step 4: 启动代理
    print("\n[Step 4/4] 启动 mitmproxy...")
    try:
        start_mitmdump()
    finally:
        cleanup()

    print("\n[完成] 捕获结果保存在: captured/ 目录")
    print("  运行 python analyze_capture.py 查看结果")


if __name__ == "__main__":
    main()
