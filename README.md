# NetboxHelper

## Overview

**NetboxHelper** is a Python library designed to simplify interactions with the NetBox API using the `pynetbox` library. It provides a collection of helper functions for common NetBox operations, such as managing IP addresses, device interfaces, prefixes, and more.

## Features

- Retrieve and manage prefixes and IP addresses.
- Add interfaces and assign IP addresses to devices.
- Retrieve device and region information.
- Easily find the next available ASN within a specified range.

## Installation

To get started with **NetboxHelper**, you need to have Python installed. The library uses `pynetbox` for API interaction and `python-slugify` for slug generation.

### Using Poetry (Recommended)

1. Install dependencies:
   
   ```bash
   poetry install

2. Add the **NetboxHelper** package to your project:
    ```bash
    poetry add netbox-helper

### Using pip
If you're not using Poetry, you can install dependencies directly:

    pip install pynetbox

## Usage
Below is an example of how to use NetboxHelper to interact with a NetBox instance.
### Example Script
```python
    from netbox_helpers import NetboxHelper
    
    # Configure the NetBox API
    API_URL = 'http://netbox.example.com'
    API_TOKEN = 'your_netbox_api_token'
    
    # Initialize the helper
    netbox_helper = NetboxHelper(api_url=API_URL, token=API_TOKEN)
    
    # Example: Retrieve the next available /24 prefix in a given supernet
    vrf_id = 1
    container = '10.0.0.0/8'
    length = 24
    next_prefix = netbox_helper.get_next_prefix(vrf_id, container, length)
    if next_prefix:
        print(f"Next available prefix: {next_prefix}")
    else:
        print("No available prefix found.")
```

## Configuration
**NetboxHelper** requires access to a NetBox instance using an API URL and a valid token. Ensure you provide these parameters when initializing the helper:
```python
    netbox_helper = NetboxHelper(api_url='http://netbox.example.com', token='your_netbox_api_token')
