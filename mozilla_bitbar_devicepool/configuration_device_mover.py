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
from ruamel.yaml.comments import CommentedMap


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

            # Ensure device_groups is a CommentedMap for YAML comment handling
            if "device_groups" in self.config_data:
                self.config_data["device_groups"] = CommentedMap(self.config_data["device_groups"])

            self.logger.info(f"Loaded configuration from {self.config_file}")
            return self.config_data

        except Exception as e:
            raise ValueError(f"Error parsing YAML file {self.config_file}: {e}")

    def save_config(self) -> None:
        """Save the configuration file with optional backup, omitting empty device groups."""
        if self.backup:
            backup_file = f"{self.config_file}.bak"
            self.logger.info(f"Creating backup: {backup_file}")
            with open(self.config_file, "r") as src, open(backup_file, "w") as dst:
                dst.write(src.read())

        # Retain empty device groups before saving
        if self.config_data and "device_groups" in self.config_data:
            device_groups = self.config_data["device_groups"]
            # Ensure all groups, including empty ones, are retained
            self.config_data["device_groups"] = {k: v if v else {} for k, v in device_groups.items()}

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

    def find_device_groups(self, device_id: str) -> List[str]:
        """Find all groups a device belongs to."""
        if not self.config_data:
            self.load_config()

        groups = []
        for group_name, devices in self.config_data["device_groups"].items():
            if devices and device_id in devices:
                groups.append(group_name)

        return groups

    def move_devices_from_any_pool(
        self,
        target_group: str,
        device_ids: List[str],
        source_group: str = None,
        dry_run: bool = False,
        comment: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Move devices from any group (or a specific source group) to target group.

        Args:
            target_group: Name of the target device group
            device_ids: List of device IDs to move
            source_group: If provided, only remove devices from this group; otherwise, remove from all groups
            dry_run: If True, show what would be moved without making changes
            comment: Optional comment to append to each moved device

        Returns:
            Dictionary with move results and statistics
        """
        if not self.config_data:
            self.load_config()

        # Initialize result structure
        result = {"moved": [], "already_in_target": [], "not_found": [], "errors": []}

        # Sanitize device_ids by stripping colons
        device_ids = [device_id.replace(":", "") for device_id in device_ids]

        # Check if target group exists
        if target_group not in self.config_data["device_groups"]:
            result["errors"].append(f"Target group '{target_group}' does not exist")
            return result

        # Ensure target group has a dictionary structure
        if self.config_data["device_groups"][target_group] is None:
            self.config_data["device_groups"][target_group] = CommentedMap()

        for device_id in device_ids:
            try:
                # Find all groups where this device exists
                current_groups = self.find_device_groups(device_id)

                if not current_groups:
                    result["not_found"].append(device_id)
                    continue

                # If source_group is specified, only consider devices in that group
                if source_group:
                    if source_group not in current_groups:
                        result["not_found"].append(device_id)
                        continue
                    # Only remove from the specified source group
                    groups_to_remove_from = [source_group]
                else:
                    # Remove from all groups
                    groups_to_remove_from = current_groups

                # Check if device is already in target group
                if target_group in current_groups:
                    # If we're removing from all groups, or specifically from the target group,
                    # we still need to process to ensure it's only in the target group
                    if source_group and source_group == target_group:
                        result["already_in_target"].append(device_id)
                        continue
                    elif not source_group and len(current_groups) == 1:
                        # Already only in target group
                        result["already_in_target"].append(device_id)
                        continue

                if not dry_run:
                    # Remove device from source groups
                    for group_name in groups_to_remove_from:
                        if (
                            group_name in self.config_data["device_groups"]
                            and self.config_data["device_groups"][group_name]
                            and device_id in self.config_data["device_groups"][group_name]
                        ):
                            del self.config_data["device_groups"][group_name][device_id]

                    # Add device to target group with comment
                    device_comment = comment if comment else None
                    self.config_data["device_groups"][target_group][device_id] = device_comment

                result["moved"].append(device_id)

            except Exception as e:
                result["errors"].append(f"Error processing device {device_id}: {str(e)}")

        # Save configuration if not a dry run
        if not dry_run and (result["moved"] or any(result.values())):
            try:
                self.save_config()
            except Exception as e:
                result["errors"].append(f"Error saving configuration: {str(e)}")

        return result

    def validate_device_list(self, device_ids: List[str]) -> Dict[str, List[str]]:
        """
        Validate a list of device IDs and show where they are currently located.

        Returns:
            Dictionary with device locations and unknown devices
        """
        if not self.config_data:
            self.load_config()

        # Sanitize device_ids by stripping colons
        device_ids = [device_id.replace(":", "") for device_id in device_ids]

        validation = {
            "found": {},  # device_id: group_name
            "not_found": [],
        }

        for device_id in device_ids:
            groups = self.find_device_groups(device_id)
            if groups:
                validation["found"][device_id] = groups
            else:
                validation["not_found"].append(device_id)

        return validation
