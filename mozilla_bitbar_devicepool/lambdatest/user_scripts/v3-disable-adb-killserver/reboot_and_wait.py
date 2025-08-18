import os
import subprocess
import sys
import time

# TODO: pull most of this code out into a library/class
# TODO: consider using mozdevice pip for many of these functions
# TODO: rename this to just post_script.py or something?


MAX_WAIT_TIME = 120


def get_connected_devices():
    try:
        # Run adb devices command and capture the output
        result = subprocess.run(["/usr/bin/adb", "devices"], capture_output=True, text=True, check=True)
        # result = subprocess.run([os.environ['ADB_BINARY_PATH'], 'devices'], capture_output=True, text=True, check=True)

        print("got stdout from 'adb devices': %s" % result.stdout)

        # Split the output into lines and extract device IDs
        output_lines = result.stdout.strip().split("\n")[1:]
        devices = [line.split("\t")[0] for line in output_lines if line.strip() != ""]

        return devices

    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        return []


def run(command, show_output=True):
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    if show_output:
        if result.stdout:
            print(result.stdout)
        # TODO: should we show stderr? should stderr and stdout be merged?
        if result.stderr:
            print(result.stderr)
    return result.stdout


# if the tc metadata file exists, then display its contents
metadata_path = "./generic-worker-metadata.json"
metadata_filename = os.path.basename(metadata_path)
if os.path.exists(metadata_path):
    with open(metadata_path, "r") as f:
        metadata = f.read()
    print(f"{metadata_filename} contents:")
    print(metadata)
else:
    print(f"{metadata_filename} does not exist")

print("")

# flush userPorts
print("Flushing userPorts...")
ports = [p.split("/")[-1] for p in os.environ.get("UserPorts", "").split(",")]
ports.extend(["2828", "8888", "8854", "4443", "4444"])
for port in ports:
    command = ["sudo", "ss", "--kill", "state", "listening", "src", f":{port}"]
    run(command)

print("")

# TODO: could be mozdevice calls
#   (see https://firefox-source-docs.mozilla.org/mozbase/mozdevice.html)

print("Listing connected devices:")
cmd = ["/usr/bin/adb", "devices", "-l"]

device_name = None
retry_sleeps = [1, 2, 5, 10, 20, 30, 60]
for attempt, sleep_time in enumerate(retry_sleeps + [0]):  # final attempt, no sleep after
    output = run(cmd, show_output=True)
    for output_line in output.split("\n"):
        if "device usb" in output_line:
            device_name = output_line.split()[0]
            break
    if device_name:
        break
    if attempt < len(retry_sleeps):
        print(f"device_name not found, retrying after {sleep_time}s...")
        time.sleep(sleep_time)

if not device_name:
    print("device_name is empty")
    sys.exit(1)
print(f"device_name: {device_name}")

print("")

# adb reboot
print("Sending reboot command...")
command = ["/usr/bin/adb", "-s", device_name, "reboot"]
run(command)

print("")

# 8/18/25: disabled to see if needed
#
# restart adb server
# print("restarting adb server...")
# command = ["/usr/bin/adb", "kill-server"]
# run(command)
# time.sleep(3)
# command = ["/usr/bin/adb", "start-server"]
# run(command)

# wait for device to show up in `adb devices`
elapsed = 0
wait_time = 10
print(f"Waiting up to {MAX_WAIT_TIME} seconds for device to reconnect...")
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

print("Device reconnected successfully.")
sys.exit(0)
