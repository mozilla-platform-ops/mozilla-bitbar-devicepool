import subprocess
import time
import sys

MAX_WAIT_TIME = 120


def get_connected_devices():
    try:
        # Run adb devices command and capture the output
        result = subprocess.run(
            ["/usr/bin/adb", "devices"], capture_output=True, text=True, check=True
        )
        # result = subprocess.run([os.environ['ADB_BINARY_PATH'], 'devices'], capture_output=True, text=True, check=True)

        print("got stdout from 'adb devices': %s" % result.stdout)

        # Split the output into lines and extract device IDs
        output_lines = result.stdout.strip().split("\n")[1:]
        devices = [line.split("\t")[0] for line in output_lines if line.strip() != ""]

        return devices

    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        return []


def run(command):
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    print(result.stderr)
    print(result.stdout)


# flush userPorts
import os

ports = [p.split("/")[-1] for p in os.environ.get("UserPorts", "").split(",")]
ports.extend(["2828", "8888", "8854", "4443", "4444"])
for port in ports:
    command = ["sudo", "ss", "--kill", "state", "listening", "src", f":{port}"]
    run(command)

# adb reboot
print("Sending reboot command...")
command = ["/usr/bin/adb", "-s", "RZCXA0H3T9P", "reboot"]
run(command)

# restart adb server
print("restarting adb server...")
command = ["/usr/bin/adb", "kill-server"]
run(command)
time.sleep(3)
command = ["/usr/bin/adb", "start-server"]
run(command)

# wait up to 2 minutes for device to show up in `adb devices`
elapsed = 0
wait_time = 10
while elapsed < MAX_WAIT_TIME:
    print(f"  sleeping {wait_time} seconds")
    time.sleep(wait_time)  # sleep X seconds
    elapsed += wait_time
    devices = get_connected_devices()
    if devices:
        break

if elapsed >= MAX_WAIT_TIME:
    print("TEST-UNEXPECTED-FAIL | lambda | device failed to reconnect after reboot")
    sys.exit(1)

sys.exit(0)
