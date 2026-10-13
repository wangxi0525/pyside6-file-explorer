"""验证单实例保护：第二次启动应激活已有窗口并自行退出。"""
import os
import subprocess
import sys
import time

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, "run.py")
PY = sys.executable

print("启动第一个实例...")
env = dict(os.environ)
env["QT_QPA_PLATFORM"] = "offscreen"
p1 = subprocess.Popen([PY, SRC], env=env, cwd=BASE)
time.sleep(4)
print("  第一个实例 pid:", p1.pid, "存活:", p1.poll() is None)

print("启动第二个实例...")
p2 = subprocess.Popen([PY, SRC], env=env, cwd=BASE)
time.sleep(5)
alive2 = p2.poll() is None
print("  第二个实例存活:", alive2, "(应为 False —— 检测到已有实例后退出)")
if alive2:
    print("  !! 单实例保护未生效")
else:
    print("  第二个实例退出码:", p2.returncode)

p1.terminate()
try:
    p1.wait(timeout=10)
except subprocess.TimeoutExpired:
    p1.kill()

print()
if alive2:
    print("❌ 单实例保护失败")
    sys.exit(1)
print("✅ 单实例保护生效")