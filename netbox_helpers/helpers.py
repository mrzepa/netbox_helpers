import logging
import pynetbox

logger = logging.getLogger(__name__)

class NetboxHelper:
    """
       A helper class for interacting with the NetBox API using pynetbox.
    """
    def __init__(self, api_url: str, token: str):
        """
        Initialize the NetBox API connection.

        :param api_url: The URL of the NetBox instance.
        :param token: The API token for authentication.
        """
        self.nb = pynetbox.api(url=api_url, token=token)
        self.nb.http_session.verify = False

    def find_next_free_number(self, integer_list, min_number, max_number):
        """
        Find the next available integer within a specified range that is not in the provided list.

        :param integer_list: A list of integers that are already used.
        :param min_number: The minimum number in the range (inclusive).
        :param max_number: The maximum number in the range (inclusive).
        :return: The smallest available integer or None if none are available.
        """
        all_numbers = set(range(min_number, max_number))

        # Convert the list of integers to a set for efficient operations
        used_numbers = set(integer_list)

        # Find the difference between all numbers and used numbers
        available_numbers = all_numbers - used_numbers

        if not available_numbers:
            return None  # There are no free numbers

        return min(available_numbers)  # Return the smallest free number

    def get_next_prefix(self, vrf_id: int, container: str, length: int) -> str:
        """
        Return the next available prefix of the specified length in the given container.

        :param vrf_id: The VRF ID.
        :param container: The container prefix (e.g., '10.0.0.0/8').
        :param length: The desired prefix length (e.g., 24).
        :return: The next available prefix or None if not found.
        """
        prefix = self.nb.ipam.prefixes.get(prefix=container, vrf_id=vrf_id)
        if prefix is None:
            logger.error(f"Prefix '{container}' not found.")
            return None

        try:
            available_prefixes = prefix.available_prefixes.list(prefix_length=length)
        except pynetbox.RequestError as e:
            logger.error(f"Error retrieving available prefixes: {e}")
            return None

        if not available_prefixes:
            logger.warning(f"No available prefixes of length {length} in '{container}'.")
            return None

        # Return the first available prefix
        return available_prefixes[0]['prefix']

    def add_interface_to_device(self, device_id: int, interface_name: str,
                                interface_type: str = 'virtual') -> pynetbox.models.dcim.Interfaces:
        """
        Add a new interface to a device.

        :param device_id: The ID of the device.
        :param interface_name: The name of the interface.
        :param interface_type: The type of the interface (default is 'virtual').
        :return: The created interface object.
        """
        try:
            new_interface = self.nb.dcim.interfaces.create(
                device=device_id,
                name=interface_name,
                type=interface_type,
                enabled=True,
            )
            logger.info(f"Added new interface '{interface_name}' to device ID {device_id}")
            return new_interface
        except pynetbox.RequestError as e:
            logger.error(f"Error adding interface: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return None

    def add_ip_address_to_interface(self, interface_id: int, tenant_id: int, vrf_id: int,
                                    ip_address: str) -> pynetbox.models.ipam.IpAddresses:
        """
        Assign an IP address to an interface.

        :param interface_id: The ID of the interface.
        :param tenant_id: The ID of the tenant.
        :param vrf_id: The ID of the VRF.
        :param ip_address: The IP address to assign (e.g., '192.168.1.10/24').
        :return: The created IP address object.
        """
        try:
            new_ip_address = self.nb.ipam.ip_addresses.create(
                assigned_object_id=interface_id,
                assigned_object_type='dcim.interface',
                address=ip_address,
                status='active',
                vrf=vrf_id,
                tenant=tenant_id,
            )
            logger.info(f"Assigned IP address '{ip_address}' to interface ID {interface_id}")
            return new_ip_address
        except pynetbox.RequestError as e:
            logger.error(f"Error assigning IP address: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return None

    def add_primary_ip_to_mgmt_interface(self, device_id: int, ip_address: str) -> bool:
        """
        Add a primary IP address to the management interface of a device.

        :param device_id: The ID of the device.
        :param ip_address: The IP address to assign.
        :return: True if successful, False otherwise.
        """
        base_mask_length = 24
        try:
            # Find the device and management interface
            device = self.nb.dcim.devices.get(device_id)
            if not device:
                logger.error(f"Device with ID {device_id} not found.")
                return False

            mgmt_interface = self.nb.dcim.interfaces.get(device_id=device_id, name='management')
            if not mgmt_interface:
                logger.error(f"Management interface not found for device '{device.name}'.")
                return False

            tenant_id = device.tenant.id if device.tenant else None

            # Find the prefix containing the IP address
            my_prefix = None
            for mask_length in range(base_mask_length, 31):
                prefixes = self.nb.ipam.prefixes.filter(
                    contains=ip_address,
                    mask_length=mask_length,
                    tenant_id=tenant_id
                )
                if prefixes:
                    my_prefix = prefixes[0]
                    mask = mask_length
                    break

            if not my_prefix:
                logger.error(
                    f"No prefix found for {ip_address} in tenant '{device.tenant.name if device.tenant else 'None'}'.")
                return False

            vrf_id = my_prefix.vrf.id if my_prefix.vrf else None

            # Create the new IP address
            ip = self.nb.ipam.ip_addresses.create(
                address=f'{ip_address}/{mask}',
                assigned_object_type='dcim.interface',
                assigned_object_id=mgmt_interface.id,
                status='active',
                description="Primary management IP address",
                tenant=tenant_id,
                vrf=vrf_id,
                tags=[],
            )

            # Set the device's primary IP
            device.primary_ip4 = ip.id
            device.save()
            logger.info(f"Primary IP address {ip_address} added to the management interface of device '{device.name}'.")
            return True

        except pynetbox.RequestError as e:
            logger.error(f"NetBox API error: {e.error}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return False

    def get_regions_list(self) -> list:
        """
        Retrieve a list of all region names.

        :return: A list of region names.
        """
        regions = self.nb.dcim.regions.all()
        return [region.name for region in regions]

    def get_device_model_list(self, manufacturer_name: str) -> list:
        """
        Retrieve a list of device models for a given manufacturer.

        :param manufacturer_name: The name of the manufacturer.
        :return: A list of device model names.
        """
        manufacturer = self.nb.dcim.manufacturers.get(name=manufacturer_name)
        if not manufacturer:
            logger.error(f"Manufacturer '{manufacturer_name}' not found.")
            return []

        device_models = self.nb.dcim.device_types.filter(manufacturer_id=manufacturer.id)
        return [model.model for model in device_models]

    def get_next_asns(self) -> int:
        """
        Find the next available private ASN (64512-65534).

        :return: The next available ASN or None if none are available.
        """
        netbox_asns = self.nb.ipam.asns.all()
        asns_list = [asn.asn for asn in netbox_asns]
        return self.find_next_free_number(asns_list, 64512, 65534)

    def create_next_prefix(self, tenant_id: int, site_id: int, vrf_id: int, supernet: str, description: str,
                           length: int, role_id: int):
        """
        Find an available prefix of a specified length from the supernet and add it to NetBox.

        :param tenant_id: Tenant ID from NetBox.
        :param site_id: Site ID from NetBox.
        :param vrf_id: VRF ID from NetBox.
        :param supernet: The parent prefix to get the next child prefix from.
        :param description: Description of the prefix.
        :param length: Length of the prefix (e.g., 24 for /24).
        :param role_id: The NetBox ID of the role for the prefix.
        :return: The newly created prefix or None if failed.
        """
        prefix = self.nb.ipam.prefixes.get(prefix=supernet, vrf_id=vrf_id)
        if prefix is None:
            logger.error(f"Supernet '{supernet}' not found in VRF ID {vrf_id}.")
            return None

        try:
            new_prefix_data = {
                'prefix_length': length,
                'tenant': tenant_id,
                'site': site_id,
                'vrf': vrf_id,
                'description': description,
                'role': role_id,
            }
            new_prefix = prefix.available_prefixes.create(new_prefix_data)
            logger.info(f"Created new prefix '{new_prefix.prefix}' in supernet '{supernet}'.")
            return new_prefix
        except pynetbox.RequestError as e:
            logger.error(f"Error creating new prefix: {e.error}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return None