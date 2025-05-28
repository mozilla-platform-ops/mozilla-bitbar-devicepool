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


def run(command):
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    print(result.stderr)
    print(result.stdout)


def run_silent(command):
    result = subprocess.run(command, capture_output=True, text=True, check=True)
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

print("Listing connected devices:")
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

print("")

# adb reboot
print("Sending reboot command...")
command = ["/usr/bin/adb", "-s", device_name, "reboot"]
run(command)

print("")

# restart adb server
print("restarting adb server...")
command = ["/usr/bin/adb", "kill-server"]
run(command)
time.sleep(3)
command = ["/usr/bin/adb", "start-server"]
run(command)

# wait up to 2 minutes for device to show up in `adb devices`
print("Waiting for device to reconnect...")
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

print("Device reconnected successfully.")
sys.exit(0)
