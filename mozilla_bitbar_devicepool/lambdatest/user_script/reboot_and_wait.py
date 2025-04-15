import subprocess
import time
import sys
import os


# TODO: pull most of this code out into a library/class
# TODO: consider using mozdevice pip for many of these functions


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


def run_silent(command):
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    return result.stdout


# flush userPorts

ports = [p.split("/")[-1] for p in os.environ.get("UserPorts", "").split(",")]
ports.extend(["2828", "8888", "8854", "4443", "4444"])
for port in ports:
    command = ["sudo", "ss", "--kill", "state", "listening", "src", f":{port}"]
    run(command)


# + /usr/bin/adb devices -l
# List of devices attached
# R5CY128X71B            device usb:1-6.1 product:a55xnsxx model:SM_A556E device:a55x transport_id:1
# 10.146.5.140:5555      device product:a55xnsxx model:SM_A556E device:a55x transport_id:2


# cmd = "adb devices -l | grep -v 'List of devices attached' | sed '/^[[:space:]]*$/d' | cut -f 1 -d ' '"

# TODO: could be a mozdevice.get_connected_devices() call
cmd = ["/usr/bin/adb", "devices", "-l"]
#
run(cmd)
#
output = run_silent(cmd)
#
for output_line in output.split("\n"):
    if "device usb" in output_line:
        device_name = output_line.split()[0]
        break
    else:
        device_name = None

if not device_name:
    print("device_name is empty")
    sys.exit(1)
print(f"device_name: {device_name}")

# adb reboot
print("Sending reboot command...")
command = ["/usr/bin/adb", "-s", device_name, "reboot"]
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
