#!/usr/bin/env python3
"""
Configuration Device Mover

A module for moving devices between device groups in configuration files.
Supports YAML configuration files with device_groups sections.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from ruamel.yaml import YAML


class ConfigurationDeviceMover:
    """A class to move devices between device groups in configuration files."""

    def __init__(self, config_file: str, backup: bool = True):
        """
        Initialize the device mover.

        Args:
            config_file: Path to the configuration file
            backup: Whether to create a backup before modifying
        """
        self.config_file = Path(config_file)
        self.backup = backup
        self.config_data = None
        self.yaml = YAML()

        # Set up logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        if not self.config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_file}")

    def load_config(self) -> Dict[str, Any]:
        """Load the configuration file."""
        try:
            with open(self.config_file, "r") as f:
                self.config_data = self.yaml.load(f)

            if "device_groups" not in self.config_data:
                raise ValueError(f"No 'device_groups' section found in {self.config_file}")

            self.logger.info(f"Loaded configuration from {self.config_file}")
            return self.config_data

        except Exception as e:
            raise ValueError(f"Error parsing YAML file {self.config_file}: {e}")

    def save_config(self) -> None:
        """Save the configuration file with optional backup."""
        if self.backup:
            backup_file = f"{self.config_file}.bak"
            self.logger.info(f"Creating backup: {backup_file}")
            with open(self.config_file, "r") as src, open(backup_file, "w") as dst:
                dst.write(src.read())

        try:
            with open(self.config_file, "w") as f:
                self.yaml.dump(self.config_data, f)
            self.logger.info(f"Saved configuration to {self.config_file}")

        except Exception as e:
            raise RuntimeError(f"Error saving configuration file: {e}")

    def list_device_groups(self) -> List[str]:
        """List all available device groups."""
        if not self.config_data:
            self.load_config()

        return list(self.config_data["device_groups"].keys())

    def list_devices_in_group(self, group_name: str) -> List[str]:
        """List all devices in a specific group."""
        if not self.config_data:
            self.load_config()

        device_groups = self.config_data["device_groups"]
        if group_name not in device_groups:
            raise ValueError(f"Device group '{group_name}' not found")

        # Devices are stored as keys in the group dictionary
        devices = list(device_groups[group_name].keys()) if device_groups[group_name] else []
        return devices

    def find_device_group(self, device_id: str) -> Optional[str]:
        """Find which group a device belongs to."""
        if not self.config_data:
            self.load_config()

        for group_name, devices in self.config_data["device_groups"].items():
            if devices and device_id in devices:
                return group_name

        return None

    def move_devices(
        self, source_group: str, target_group: str, device_ids: List[str], dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Move devices from source group to target group.

        Args:
            source_group: Name of the source device group
            target_group: Name of the target device group
            device_ids: List of device IDs to move
            dry_run: If True, show what would be moved without making changes

        Returns:
            Dictionary with move results and statistics
        """
        if not self.config_data:
            self.load_config()

        device_groups = self.config_data["device_groups"]

        # Validate groups exist
        if source_group not in device_groups:
            raise ValueError(f"Source group '{source_group}' not found")

        if target_group not in device_groups:
            raise ValueError(f"Target group '{target_group}' not found")

        # Initialize target group if it's None/empty
        if device_groups[target_group] is None:
            device_groups[target_group] = {}

        # Track results
        results = {"moved": [], "not_found": [], "already_in_target": [], "errors": []}

        for device_id in device_ids:
            try:
                # Check if device exists in source group
                if device_groups[source_group] is None or device_id not in device_groups[source_group]:
                    # Check if device is already in target group
                    if device_groups[target_group] and device_id in device_groups[target_group]:
                        results["already_in_target"].append(device_id)
                        self.logger.warning(f"Device {device_id} already in target group '{target_group}'")
                    else:
                        # Check if device exists in any other group
                        current_group = self.find_device_group(device_id)
                        if current_group:
                            results["errors"].append(
                                f"Device {device_id} found in '{current_group}', not '{source_group}'"
                            )
                        else:
                            results["not_found"].append(device_id)
                        self.logger.error(f"Device {device_id} not found in source group '{source_group}'")
                    continue

                if not dry_run:
                    # Get any existing value/comment for the device
                    device_value = device_groups[source_group][device_id]

                    # Remove from source group
                    del device_groups[source_group][device_id]

                    # Add to target group (preserving any value/comment)
                    device_groups[target_group][device_id] = device_value

                results["moved"].append(device_id)
                action = "Would move" if dry_run else "Moved"
                self.logger.info(f"{action} device {device_id} from '{source_group}' to '{target_group}'")

            except Exception as e:
                error_msg = f"Error moving device {device_id}: {e}"
                results["errors"].append(error_msg)
                self.logger.error(error_msg)

        # Save changes if not dry run and there were successful moves
        if not dry_run and results["moved"]:
            self.save_config()

        return results

    def validate_device_list(self, device_ids: List[str]) -> Dict[str, List[str]]:
        """
        Validate a list of device IDs and show where they are currently located.

        Returns:
            Dictionary with device locations and unknown devices
        """
        if not self.config_data:
            self.load_config()

        validation = {
            "found": {},  # device_id: group_name
            "not_found": [],
        }

        for device_id in device_ids:
            group = self.find_device_group(device_id)
            if group:
                validation["found"][device_id] = group
            else:
                validation["not_found"].append(device_id)

        return validation
