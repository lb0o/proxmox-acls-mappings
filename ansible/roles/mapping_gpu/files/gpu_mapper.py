#!/usr/bin/env python3
# Author: lb0o Nocilo

import os
import json
import requests
import urllib3
from typing import Dict, List, Optional, Union
from dataclasses import dataclass
from datetime import datetime

# Suppress SSL warnings if using self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

@dataclass
class GPUDevice:
    node: str
    pci_path: str
    vendor_id: str
    device_id: str
    subsystem_vendor_id: str
    subsystem_device_id: str
    iommu_group: str
    description: str
    last_seen: str
    index: int

class ProxmoxGPUMapper:
    def __init__(self, api_url: str, token_id: str, token_value: str, verify_ssl: bool = False):
        self.api_url = api_url.rstrip('/')
        self.token_id = token_id
        self.token_value = token_value
        self.verify_ssl = verify_ssl

    def api_request(
        self, 
        method: str, 
        path: str, 
        data: Optional[Dict] = None, 
        form_data: Optional[List[tuple]] = None
    ) -> Dict:
        """Make an API request to Proxmox using API token."""
        headers = {
            'Authorization': f'PVEAPIToken={self.token_id}={self.token_value}'
        }
        
        if method in ['POST', 'PUT', 'DELETE']:
            # For API tokens, we don't need a CSRF token
            pass

        try:
            print(f"Making {method} request to {path}")
            if form_data:
                headers['Content-Type'] = 'application/x-www-form-urlencoded'
                response = requests.request(
                    method,
                    f"{self.api_url}/{path.lstrip('/')}",
                    headers=headers,
                    data=form_data,
                    verify=self.verify_ssl
                )
            else:
                headers['Content-Type'] = 'application/json'
                response = requests.request(
                    method,
                    f"{self.api_url}/{path.lstrip('/')}",
                    headers=headers,
                    json=data,
                    verify=self.verify_ssl
                )
            
            print(f"Response status code: {response.status_code}")
            if response.status_code >= 400:
                print(f"Error response: {response.text}")
            
            response.raise_for_status()
            return response.json().get("data", {})
        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            if hasattr(e, 'response') and e.response is not None:
                error_msg = f"{error_msg} - {e.response.text}"
            raise Exception(f"API request failed: {error_msg}")

    def fetch_pci_devices(self, node: str) -> List[Dict]:
        """Fetch PCI devices for a given node using the API endpoint"""
        try:
            print(f"\nFetching PCI devices for node {node}")
            path = f"nodes/{node}/hardware/pci"
            response = self.api_request('GET', path)
            if not response:
                print(f"No PCI data found for node {node}")
                return []
            print(f"Found {len(response)} PCI devices")
            return response
        except Exception as e:
            print(f"Error fetching PCI devices for node {node}: {e}")
            return []

    def parse_pci_data(self, node: str, pci_data: List[Dict]) -> List[GPUDevice]:
        """Parse PCI data and extract GPU devices"""
        gpu_devices = []
        gpu_index = 0
        print(f"\nParsing PCI data for node {node}")
        for device in pci_data:
            if device.get('vendor') not in ["0x10de", "0x8086"]:
                continue

            if not device.get('class', '').startswith('0x03'):
                continue

            print(f"Found GPU device: {device.get('device_name', 'Unknown Device')}")
            gpu = GPUDevice(
                node=node,
                pci_path=device.get('id', ''),
                vendor_id=device.get('vendor', ''),
                device_id=device.get('device', ''),
                subsystem_vendor_id=device.get('subsystem_vendor', ''),
                subsystem_device_id=device.get('subsystem_device', ''),
                iommu_group=str(device.get('iommugroup', '')),
                description=device.get('device_name', 'Unknown Device'),
                last_seen=datetime.now().isoformat(),
                index=gpu_index
            )
            gpu_devices.append(gpu)
            gpu_index += 1
        return gpu_devices

    def create_gpu_mapping(self, mapping_id: str, devices: List[GPUDevice]) -> None:
        """Create a GPU mapping based on the devices list."""
        try:
            print(f"\nCreating GPU mapping '{mapping_id}'")
            try:
                self.api_request('DELETE', f"cluster/mapping/pci/{mapping_id}")
                print(f"Deleted existing mapping '{mapping_id}'")
            except Exception:
                print(f"No existing mapping '{mapping_id}' found. Proceeding to create a new one.")

            map_entries = []
            for device in devices:
                vendor_id = device.vendor_id.replace("0x", "")
                device_id = device.device_id.replace("0x", "")

                subsystem_id = ""
                if device.subsystem_vendor_id and device.subsystem_device_id:
                    subsystem_id = f"{device.subsystem_vendor_id}:{device.subsystem_device_id}"
                    subsystem_id = subsystem_id.replace("0x", "")

                entry_components = [
                    f"id={vendor_id}:{device_id}",
                    f"iommugroup={device.iommu_group}",
                    f"node={device.node}",
                    f"path={device.pci_path}"
                ]
                if subsystem_id:
                    entry_components.append(f"subsystem-id={subsystem_id}")
                
                entry_str = ",".join(entry_components)
                map_entries.append(entry_str)
                print(f"Adding mapping: {entry_str}")

            form_data: List[tuple] = [('id', mapping_id)]
            for entry in map_entries:
                form_data.append(('map', entry))

            self.api_request('POST', 'cluster/mapping/pci', form_data=form_data)
            print(f"Created mapping '{mapping_id}' for {len(devices)} device(s)")

        except Exception as e:
            print(f"Error creating mapping '{mapping_id}': {e}")
            if 'map_entries' in locals():
                print(f"Mapping entries: {map_entries}")

    def scan_and_map_gpus(self) -> None:
        """Scan all nodes and create GPU mappings based on PCI data from API"""
        try:
            print("\nStarting GPU scanning and mapping process")
            nodes_response = self.api_request('GET', 'nodes')
            nodes = nodes_response if isinstance(nodes_response, list) else nodes_response.get('nodes', [])

            if not nodes:
                print("No nodes found in the cluster.")
                return

            gpus_per_node: Dict[str, List[GPUDevice]] = {}
            for node in nodes:
                node_name = node.get('node') or node.get('name')
                if not node_name:
                    continue

                print(f"\nProcessing node {node_name}...")
                pci_data = self.fetch_pci_devices(node_name)
                gpu_devices = self.parse_pci_data(node_name, pci_data)
                if gpu_devices:
                    print(f"Found {len(gpu_devices)} GPU(s) on node {node_name}")
                    gpus_per_node[node_name] = gpu_devices
                else:
                    print(f"No GPUs found on node {node_name}")

            if not gpus_per_node:
                print("No GPUs found in the cluster.")
                return

            for node, gpus in gpus_per_node.items():
                for gpu in gpus:
                    cardname = f"{gpu.description}"
                    cardname = (
                        cardname.replace("[", "")
                        .replace("]", "")
                        .replace(" ", "_")
                        .replace(":", "_")
                        .replace("-", "_")
                        .lower()
                    )
                    mapping_id = f"gpu-{gpu.vendor_id[2:]}{gpu.device_id[2:]}-{cardname}-{gpu.index + 1}"
                    print(f"Creating mapping for GPU: {mapping_id}")
                    self.create_gpu_mapping(mapping_id, [gpu])

        except Exception as e:
            print(f"Error during GPU scanning and mapping: {e}")

def main():
    api_url = os.getenv('PROXMOX_API_URL')
    token_id = os.getenv('PROXMOX_TOKEN_ID')
    token_value = os.getenv('PROXMOX_TOKEN_VALUE')
    verify_ssl = os.getenv('PROXMOX_VERIFY_SSL', 'false').lower() == 'true'

    if not all([api_url, token_id, token_value]):
        print("Error: Required environment variables are not set")
        print("Please set: PROXMOX_API_URL, PROXMOX_TOKEN_ID, PROXMOX_TOKEN_VALUE")
        exit(1)

    print(f"\nInitializing GPU mapper with:")
    print(f"API URL: {api_url}")
    print(f"Token ID: {token_id}")
    print(f"Verify SSL: {verify_ssl}")

    mapper = ProxmoxGPUMapper(api_url, token_id, token_value, verify_ssl)
    mapper.scan_and_map_gpus()

if __name__ == "__main__":
    main() 