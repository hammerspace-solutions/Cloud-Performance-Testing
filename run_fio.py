#!/usr/bin/env python3
# TODO: Review Michael's fio scripts to see if we can't integrate a defaults argument that would replicate specific
#  workloads I/E. -D mike1 which would automatically set XYZ properly
# TODO: Review Chris Worley's test notes and integrate any missing functionality
# TODO: Adapt to allow for array of nfs mounts and mount points and check all.  Plan would be to distribute number of
#  files equally between mounts ensuring they are evenly distributed.  This would allow for parallel testing
# TODO: Anytime sender is called the success part of the return should be checked.
# TODO: Instantiate logger for server as well
# TODO: Double check run_command_and_go return values

import argparse
import subprocess
import multiprocessing
import logging
import os
import csv
import re
import sys
import json
import shutil
import ipaddress
import socket
import tarfile
import time
import typing
from datetime import datetime
from functools import reduce
from concurrent.futures import ThreadPoolExecutor


# =====================================
# GLOBAL VARIABLES
# =====================================


# Create Logger
logger = logging.getLogger('fio_nfs')

# Create global for nfsio process
nfsio_proc: typing.Optional[subprocess.Popen] = None

TEMPLATES = {
    'mike1': {
        'globals': {
            'fallocate': 'none',
            'fsync_on_close': 1,
            'unlink': 1,
        },
        'loops': 200,
        'file_size': '10G',
        'num_testfiles': 7,
        'file_create_threads': 16,
        'block_size': '256K',
        'io_engine': 'libaio',
        'io_direction': 'rw',
        'files_per_job': 1,
        'rw_mixread': 95,
        'fio_numjobs': 1,
        'queue_depth': 1,
        'use_directory_mode': True
    },
    'JonIOPSMix': {
        'file_size': '4G',
        'num_testfiles': 72,
        'file_create_threads': 36,
        'block_size': '4K',
        'io_engine': 'libaio',
        'io_direction': 'randrw',
        'files_per_job': 1,
        'rw_mixread': 70,
        'fio_numjobs': 2,
        'queue_depth': 8
    },
    'JonIOPSRead': {
        'file_size': '4G',
        'num_testfiles': 72,
        'file_create_threads': 36,
        'block_size': '4K',
        'io_engine': 'libaio',
        'io_direction': 'randread',
        'files_per_job': 1,
        'fio_numjobs': 2,
        'queue_depth': 8
    },
    'JonIOPSWrite': {
        'file_size': '4G',
        'num_testfiles': 72,
        'file_create_threads': 36,
        'block_size': '4K',
        'io_engine': 'libaio',
        'io_direction': 'randwrite',
        'files_per_job': 1,
        'fio_numjobs': 2,
        'queue_depth': 8
    },
    'JonBWRead': {
        'file_size': '50G',
        'num_testfiles': 12,
        'file_create_threads': 12,
        'block_size': '1m',
        'io_engine': 'libaio',
        'io_direction': 'read',
        'files_per_job': 1,
        'fio_numjobs': 4,
        'queue_depth': 16
    },
    'JonBWWrite': {
        'file_size': '50G',
        'num_testfiles': 12,
        'file_create_threads': 12,
        'block_size': '1m',
        'io_engine': 'libaio',
        'io_direction': 'write',
        'files_per_job': 1,
        'fio_numjobs': 4,
        'queue_depth': 16
    },
    'JonBWMix': {
        'file_size': '50G',
        'num_testfiles': 12,
        'file_create_threads': 12,
        'block_size': '1m',
        'io_engine': 'libaio',
        'io_direction': 'rw',
        'files_per_job': 1,
        'rw_mixread': 50,
        'fio_numjobs': 4,
        'queue_depth': 16
    },
    'WekaBWRead': {
        'globals': {
            'disk_util': 0,
            'startdelay': 5
        },
        'file_size': '128G',
        'num_testfiles': 32,
        'file_create_threads': 32,
        'block_size': '1m',
        'io_engine': 'posixaio',
        'io_direction': 'read',
        'files_per_job': 32,
        'fio_numjobs': 32,
        'queue_depth': 1,
        'use_directory_mode': True
    },
    'WekaBWWrite': {
        'globals': {
            'disk_util': 0,
            'startdelay': 5
        },
        'file_size': '128G',
        'num_testfiles': 32,
        'file_create_threads': 32,
        'block_size': '1m',
        'io_engine': 'posixaio',
        'io_direction': 'write',
        'files_per_job': 32,
        'fio_numjobs': 32,
        'queue_depth': 1,
        'use_directory_mode': True
    },
    'WekaBWMix': {
        'globals': {
            'disk_util': 0,
            'startdelay': 5
        },
        'file_size': '128G',
        'num_testfiles': 32,
        'file_create_threads': 32,
        'block_size': '1m',
        'io_engine': 'posixaio',
        'io_direction': 'rw',
        'files_per_job': 32,
        'rw_mixread': 50,
        'fio_numjobs': 32,
        'queue_depth': 1,
        'use_directory_mode': True
    },
    'WekaIOPSWrite': {
        'globals': {
            'disk_util': 0,
            'startdelay': 5
        },
        'file_size': '4G',
        'num_testfiles': 192,
        'file_create_threads': 72,
        'block_size': '4k',
        'io_engine': 'posixaio',
        'io_direction': 'randwrite',
        'files_per_job': 192,
        'fio_numjobs': 192,
        'queue_depth': 1,
        'use_directory_mode': True
    },
    'WekaIOPSMix': {
        'globals': {
            'disk_util': 0,
            'startdelay': 5
        },
        'file_size': '4G',
        'num_testfiles': 192,
        'file_create_threads': 72,
        'block_size': '4k',
        'io_engine': 'posixaio',
        'io_direction': 'randrw',
        'rw_mixread': 70,
        'files_per_job': 192,
        'fio_numjobs': 192,
        'queue_depth': 1,
        'use_directory_mode': True
    },
    'JonLATRead': {
        'file_size': '50G',
        'num_testfiles': 1,
        'file_create_threads': 1,
        'block_size': '4k',
        'io_engine': 'libaio',
        'io_direction': 'randread',
        'files_per_job': 1,
        'fio_numjobs': 1,
        'queue_depth': 1
    },
    'JonLATWrite': {
        'file_size': '50G',
        'num_testfiles': 1,
        'file_create_threads': 1,
        'block_size': '4k',
        'io_engine': 'libaio',
        'io_direction': 'randwrite',
        'files_per_job': 1,
        'fio_numjobs': 1,
        'queue_depth': 1
    }
}

# =====================================
# Class Definitions
# =====================================


class PerformanceResult:
    def __init__(self, data: dict):
        self.io_bytes = data['io_bytes']
        self.bw_bytes = data['bw_bytes']
        self.iops = data['iops']
        self.runtime = data['runtime']
        self.total_ios = data['total_ios']
        self.slat_ns = data['slat_ns']
        self.clat_ns = data['clat_ns']
        self.lat_ns = data['lat_ns']
        self.percentile = data['clat_ns']['percentile'] if 'percentile' in data['clat_ns'] else {}
        self.bw_min = data['bw_min']
        self.bw_max = data['bw_max']
        self.bw_agg = data['bw_agg']
        self.bw_mean = data['bw_mean']
        self.bw_dev = data['bw_dev']
        self.bw_samples = data['bw_samples']
        self.iops_min = data['iops_min']
        self.iops_max = data['iops_max']
        self.iops_mean = data['iops_mean']
        self.iops_stddev = data['iops_stddev']
        self.iops_samples = data['iops_samples']

    def __add__(self, other):
        if not isinstance(other, PerformanceResult):
            raise ValueError('Can only add two PerformanceResult instances')

        self.io_bytes += other.io_bytes
        self.bw_bytes += other.bw_bytes
        self.iops += other.iops
        self.runtime += (self.runtime + other.runtime) / 2
        self.total_ios += other.total_ios
        # TODO: straight addition here doesn't make sense... or does it
        self.bw_min += other.bw_min
        self.bw_max += other.bw_max
        self.bw_agg += other.bw_agg
        self.bw_mean += other.bw_mean
        self.bw_dev += other.bw_dev
        self.bw_samples += other.bw_samples
        self.iops_min += other.iops_min
        self.iops_max += other.iops_max
        self.iops_mean += other.iops_mean
        self.iops_stddev += other.iops_stddev
        self.iops_samples += other.iops_samples

        # Assuming mean values should be averaged
        for key in ['min', 'max', 'mean', 'stddev']:
            self.slat_ns[key] = (self.slat_ns[key] + other.slat_ns[key]) / 2
            self.clat_ns[key] = (self.clat_ns[key] + other.clat_ns[key]) / 2
            self.lat_ns[key] = (self.lat_ns[key] + other.lat_ns[key]) / 2

        # Summing up the percentiles (if there are percentiles in both instances)
        if self.percentile and other.percentile:
            for key in self.percentile.keys():
                self.percentile[key] += other.percentile.get(key, 0)

        return self


class FIOResult:
    def __init__(self, data: dict, index: int):
        self.fio_version = data['fio version']
        self.timestamp = data['timestamp']
        self.time = data['time']
        self.global_options = data['global options']
        self.hostname = None
        client_stat = data['client_stats'][index]

        self.read_result = PerformanceResult(client_stat['read'])
        self.write_result = PerformanceResult(client_stat['write'])
        self.trim_result = PerformanceResult(client_stat['trim']) if 'trim' in client_stat else None

        # Copy fields from client_stat to self, while excluding read, write, trim
        excluded_keys = {'read', 'write', 'trim'}
        for key, value in client_stat.items():
            if key not in excluded_keys:
                setattr(self, key, value)

    def __add__(self, other):
        if not isinstance(other, FIOResult):
            raise ValueError('Can only add two FIOResult instances')

        self.hostname += f', {other.hostname}'
        self.read_result += other.read_result
        self.write_result += other.write_result
        if self.trim_result and other.trim_result:
            self.trim_result += other.trim_result

        return self

    def __str__(self):
        lines = []
        lines.append(f"\n\n\n=== Test Details ===")
        lines.append(f"FIO Version: {self.fio_version}")
        lines.append(f"Timestamp: {self.time}")
        lines.append(f"Hostname(s): {getattr(self, 'hostname', 'N/A')}")
        lines.append(f"I/O Engine: {self.global_options['ioengine']}")
        lines.append(f"Read/Write Type: {self.global_options['rw']}")
        lines.append(f"Run Time: {self.global_options['runtime']}")
        lines.append(f"Block Size: {self.global_options['bs']}")
        lines.append(f"Number of Jobs: {self.global_options['numjobs']}")
        lines.append(f"I/O Depth: {self.global_options['iodepth']}")

        lines.append(f"\n=== Performance Results ===")
        lines.append(f"{'':^13} | {'BW GiB/s':^10} | {'BW GB/s':^10} | {'IOPS':^12} | {'Lat (us)':^12}")

        if self.read_result and self.read_result.bw_mean != 0:
            lines.append(f"{'Read result:':<13} "
                         f"| {format(round(self.read_result.bw_mean / (1024 ** 2), 2), '.2f'):>10} "
                         f"| {format(round(self.read_result.bw_mean / (1000 ** 2), 2), '.2f'):>10} "
                         f"| {format(round(self.read_result.iops_mean, 2), '.2f'):>12} "
                         f"| {format(round(self.read_result.lat_ns['mean'] / 1000, 2), '.2f'):>12}")
        if self.write_result and self.write_result.bw_mean != 0:
            lines.append(f"{'Write result:':<13} "
                         f"| {format(round(self.write_result.bw_mean / (1024 ** 2), 2), '.2f'):>10} "
                         f"| {format(round(self.write_result.bw_mean / (1000 ** 2), 2), '.2f'):>10} "
                         f"| {format(round(self.write_result.iops_mean, 2), '.2f'):>12} "
                         f"| {format(round(self.write_result.lat_ns['mean'] / 1000, 2), '.2f'):>12}")
        if self.trim_result and self.trim_result.bw_mean != 0:
            lines.append(f"{'Trim result:':<13} "
                         f"| {format(round(self.trim_result.bw_mean / (1024 ** 2), 2), '.2f'):>10} "
                         f"| {format(round(self.trim_result.bw_mean / (1000 ** 2), 2), '.2f'):>10} "
                         f"| {format(round(self.trim_result.iops_mean, 2), '.2f'):>12} "
                         f"| {format(round(self.trim_result.lat_ns['mean'] / 1000, 2), '.2f'):>12}")

        lines.append(f"\n")
        return "\n".join(lines)

    def __repr__(self):
        return self.__str__()


# =====================================
# FUNCTION DEFINITIONS
# =====================================


def print_templates_information():
    for template_name, settings in TEMPLATES.items():
        print(f"Template name: {template_name}")
        for setting, value in settings.items():
            if isinstance(value, dict):
                # If the setting value itself is a dictionary, print its contents too
                print(f"\t{setting.ljust(24)}:")
                for key, val in value.items():
                    print(f"\t\t{key.ljust(22)}: {val}")
            else:
                # Otherwise, print the setting and value as before
                print(f"\t{setting.ljust(24)}: {value}")


def print_arg_info(args, template_values):
    # Create a summary of the arguments
    arg_summary = {arg: getattr(args, arg) for arg in vars(args)}
    overridden_values, non_overridden_values = {}, {}

    # Separate overridden and non-overridden values
    for key, arg_val in arg_summary.items():
        if key in template_values and arg_val != template_values[key]:
            overridden_values[key] = arg_val
        elif key != 'template' and key in template_values:
            non_overridden_values[key] = arg_val

    # Format overridden and non-overridden values for printing
    overridden_values_str = '\n'.join(f"{k}: {v}" for k, v in overridden_values.items())
    non_overridden_values_str = '\n'.join(f"{k}: {v}" for k, v in non_overridden_values.items())

    # Printing the values
    logger.info(f"\nTemplate values: \n{non_overridden_values_str}")
    if overridden_values_str != "":
        logger.info(f"\nOverridden template values: \n{overridden_values_str}")


def cleanup(args: argparse.Namespace) -> None:
    """
    Cleans up the running processes on the specified IPs.

    Args:
        args (str): An object containing the list of IPs.

    Returns:
        None
    """
    for ip in args.ips:
        command = 'pkill fio'
        sender(ip, 5000, f'run_command_and_go, {command}', True, True)
        sender(ip, 5000, f'quit', True, True)


def create_tarfile(source_dir: str) -> None:
    """
    Creates a tarfile from the given source directory and places it in the source directory's parent directory.

    Args:
        source_dir (str): The path of the directory to be included in the tarfile.

    Returns:
        None
    """
    # Get the directory name and create the output filename
    dir_name = os.path.basename(source_dir)
    parent_dir = os.path.dirname(source_dir)
    output_filename = os.path.join(parent_dir, dir_name + '.tgz')

    # Create tarball
    with tarfile.open(output_filename, "w:gz") as tar:
        tar.add(source_dir, arcname=os.path.basename(source_dir))


def listener() -> None:
    """
    Listens for connections on a specified port and uses indirect function calls to execute commands received from
    clients.

    Returns:
        None
    """
    # host = socket.gethostname()
    host = '0.0.0.0'
    # TODO: host should probably be 0.0.0.0 so we listen on all ports.  I've found socket.gethostname to be unreliable.
    port = 5000
    close_server = False  # Initially set close_server to False

    server_socket = socket.socket()
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    max_attempts = 10  # Maximum number of attempts
    for attempt in range(max_attempts):
        try:
            server_socket.bind((host, port))
            break  # Break the loop if binding was successful
        except socket.error as e:
            if attempt < max_attempts - 1:  # No delay is needed after the last attempt
                wait_time = 2 ** attempt  # Exponential backoff
                print(f"Socket error occurred: {e}, retrying in {wait_time} seconds...")
                time.sleep(wait_time)  # Exponential backoff
            else:
                print(f"Socket error occurred: {e}. Giving up after {max_attempts} attempts.")
                server_socket.close()
                return

    server_socket.listen(2)
    while True:
        try:
            conn, address = server_socket.accept()
            print("Connection from: " + str(address))
        except socket.error as e:
            print(f"Socket error occurred while accepting connection: {e}")
            continue

        while True:
            try:
                data = conn.recv(1024)
                if not data:
                    break

                data = data.decode()
                print("from connected user: " + str(data))

                # Split the command and the parameters
                command, _, parameters = data.partition(', ')
                parameters = parameters.strip("'")  # Remove quotes if present
                param_list = parameters.split(', ')  # Split parameters into a list

                # Use the getattr function to dynamically call the function
                if command == 'quit':
                    response = "Quitting server"
                    close_server = True
                elif command in globals():
                    func = globals()[command]
                    response = str(func(*param_list))  # Unpack the parameter list into the function
                else:
                    response = "Unknown command"

                # Send response.
                try:
                    conn.send(response.encode())
                except socket.error as e:
                    print(f"Socket error occurred while sending response: {e}")

                if close_server:
                    break

            except Exception as e:
                print(f"An error occurred: {e}")

        # Allow response to sender time to get there before closing connection
        conn.close()
        if close_server:  # Break while loop after connection is closed
            break


def sender(host: str, port: int, cmd: str, logger_ready: bool, suppress_out: bool) -> tuple:
    """
    Sends a command to a server.

    Args:
        host (str): The host address of the server.
        port (int): The port number to connect to on the server.
        cmd (str): The command to send to the server. Command must be in the format of
            'FUNCTIONNAME, PARAMETERS, PARAMETERS'
        logger_ready (bool): Lets function know if it can use the logger instead of basic prints
        suppress_out (bool): Lets function know to suppress basic prints

    Returns:
        tuple: A tuple containing a boolean value indicating if the operation was successful, and the response received
        from the server.
    """
    response = ''
    client_socket = socket.socket()
    try:
        client_socket.connect((host, port))
    except socket.error as e:
        if logger_ready:
            logger.error(f"Could not connect to server: {e}")
        elif not suppress_out:
            print(f"Could not connect to server: {e}")
        return False, ''

    try:
        client_socket.send(cmd.encode())
        response = client_socket.recv(1024).decode()
        if logger_ready:
            logger.debug(f"Received from server: {response}")
        elif not suppress_out:
            print(f"Received from server: {response}")

    except socket.error as e:
        if logger_ready:
            logger.error(f"Socket error occurred: {e}")
        elif not suppress_out:
            print(f"Socket error occurred: {e}")

    finally:
        client_socket.close()

    return True, response


def valid_ip(s: str) -> str:
    """
    Validates if a string represents a valid IP address.

    Args:
        s (str): The string to be checked.

    Returns:
        str: The valid IP address as a string.

    Raises:
        ValueError: If the string does not represent a valid IP address.
    """
    try:
        ipaddress.ip_address(s)
        return s
    except ValueError:
        raise argparse.ArgumentTypeError("Invalid IP address")


def run_command_and_wait(command: str) -> bool:
    """
    Runs a command and waits for it to finish execution.

    Args:
        command (str): The command to be executed.

    Returns:
        bool: True if the command executed successfully, False otherwise.
    """
    try:
        result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            print(f"Command failed with return code {result.returncode}, stderr: {result.stderr}")
            return False
    except Exception as e:
        print(f"An exception occurred while running the command: {str(e)}")
        return False

    return True


def run_command_and_go(command: str) -> bool:
    """
    Runs the given command and returns immediately.

    Args:
        command (str): The command to be run.

    Returns:
        bool: True if the command is successfully executed, False otherwise.
    """
    try:
        subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    except Exception as e:
        print(f"An exception occurred while running the command: {str(e)}")
        return False

    return True


def is_port_open(ip: str, port: int) -> bool:
    """
    Checks if a port is open on a given IP address.

    Args:
        ip (str): The IP address.
        port (int): The port number.

    Returns:
        bool: True if the port is open, False if it is closed.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((ip, port)) == 0


def test_ssh_access(remote_server_ip: str, user: str) -> bool:
    """
    Tests passwordless SSH access to a remote server.

    Args:
        remote_server_ip (str): The IP address or hostname of the remote server.
        user (str): The user for SSH.

    Returns:
        bool: True if the SSH access test passed, False otherwise.
    """
    try:
        command = f'ssh -o BatchMode=yes -o ConnectTimeout=5 -q {user}@{remote_server_ip} echo ok'
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, universal_newlines=True)

        # Wait for the process to finish and get the output
        stdout, stderr = process.communicate()

        # Check if the remote command was run successfully
        if process.returncode != 0 or stdout.strip() != 'ok':
            print(f'Non-interactive SSH access test failed. Error: {stderr.strip()}')
            return False

        print('Non-interactive SSH access test passed.')
        return True

    except Exception as e:
        print(f'Failed to test non-interactive SSH access: {str(e)}')
        return False


def test_nonroot_access(test_dir: str) -> bool:
    """
    Checks non-root access to a directory and its files.

    Args:
        test_dir (str): The directory to be tested for non-root access.

    Returns:
        bool: True if the directory and its files are accessible for non-root users, False otherwise.
    """
    # Check for readability
    if not os.access(test_dir, os.R_OK):
        print(f"ERROR: non-root: Cannot read the directory {test_dir}")

    # Get list of files in the directory
    try:
        file_list = os.listdir(test_dir)
    except PermissionError:
        print(f"ERROR: non-root: Cannot list files in the directory {test_dir}")
        return False

    # Check each file's accessibility
    for file in file_list:
        file_path = os.path.join(test_dir, file)
        if 'testfile' in file:
            if not os.access(file_path, os.W_OK):
                print(f"ERROR: non-root: Cannot write the file {file_path}")
                return False

    return True


def is_nfs_mount(dir_path: str) -> bool:
    """
    Checks if the specified directory path is mounted as an NFS share.

    Args:
        dir_path (str): The directory path to check.

    Returns:
        bool: True if the directory path is mounted as an NFS share, False otherwise.
    """
    # TODO: Evaluate if this should use run_command_and_wait
    try:
        output = subprocess.check_output("mount").decode("utf-8")
        lines = output.split("\n")
        for line in lines:
            parts = line.split(" ")
            if len(parts) > 2 and parts[2] == dir_path and ("nfs" in parts or 'nfs4' in parts):
                return True
    except subprocess.CalledProcessError:
        logger.error('Error calling mount command.')
    return False


def convert_size(size_str: str) -> int:
    """
    Converts a given size string into its equivalent value in bytes.

    Args:
        size_str (str): A string representing the size to be converted. It can be in the format of "t", "g", "m", "k"

    Returns:
        int: The converted size as an integer in bytes.
    """
    size_str = size_str.lower()
    if 't' in size_str:
        return int(size_str.replace('t', '')) * (1024 ** 4)
    elif 'g' in size_str:
        return int(size_str.replace('g', '')) * (1024 ** 3)
    elif 'm' in size_str:
        return int(size_str.replace('m', '')) * (1024 ** 2)
    elif 'k' in size_str:
        return int(size_str.replace('k', '')) * 1024
    else:  # if no letter specified, we assume that it's already in bytes
        return int(size_str)


def create_file_orig(test_dir: str, block_size: str, file_size: int, file_num: int, job_num: int, ip: str, dir_mode: bool,
                file_subnum: int) -> None:
    """
    Creates a file with specified parameters.

    Args:
        test_dir (str): The directory where the file will be created.
        block_size (str): The size of each block in the file.
        file_size (str): The total size of the file.
        file_num (int): An identifier for the file.
        job_num (int): An identifier for the job.
        ip (str): The IP address associated with the file.
        dir_mode (bool): Whether the use_directory_mode was selected
        file_subnum (int): File sub number.  (Technically file number for the fio jobnum)

    Returns:
        None
    """
    if dir_mode:
        filename = f"{test_dir}/{ip}/job{job_num}/testfile{file_num}.{file_subnum}"
    else:
        filename = f"{test_dir}/{ip}/testfile{file_num}"

    # Delete file if it already exists
    if os.path.isfile(filename):
        os.remove(filename)

    # Convert filesize and block size into bytes and calculate number of blocks required
    block_size_bytes = convert_size(block_size)
    num_blocks = file_size // block_size_bytes

    # Generate a single random block
    random_block = os.urandom(block_size_bytes)

    # Open the file with Direct I/O
    # Added O_SYNC to ensure synchronous IO
    fd = os.open(filename, os.O_CREAT | os.O_WRONLY | os.O_DIRECT | os.O_SYNC)
    f = os.fdopen(fd, 'wb')

    with f:
        for _ in range(num_blocks):
            f.write(random_block)
        remainder = file_size % block_size_bytes
        if remainder != 0:
            logger.warning('Remainder is %s, truncating', remainder)


def create_file(test_dir: str, block_size: str, file_size: int, file_num: int, job_num: int, ip: str, dir_mode: bool,
                file_subnum: int) -> None:
    """
    Creates a file with specified parameters.

    Args:
        test_dir (str): The directory where the file will be created.
        block_size (str): The size of each block in the file.
        file_size (str): The total size of the file.
        file_num (int): An identifier for the file.
        job_num (int): An identifier for the job.
        ip (str): The IP address associated with the file.
        dir_mode (bool): Whether the use_directory_mode was selected
        file_subnum (int): File sub number.  (Technically file number for the fio jobnum)

    Returns:
        None
    """
    if dir_mode:
        filename = f"{test_dir}/{ip}/job{job_num}/testfile{file_num}.{file_subnum}"
    else:
        filename = f"{test_dir}/{ip}/testfile{file_num}"

    # Delete file if it already exists
    if os.path.isfile(filename):
        os.remove(filename)

    # Convert filesize and block size into bytes and calculate number of blocks required
    block_size_bytes = convert_size(block_size)
    num_blocks = file_size // block_size_bytes

    # Generate a single random block
    random_block = os.urandom(block_size_bytes)

    # Open the file with Direct I/O
    try:
        fd = os.open(filename, os.O_CREAT | os.O_WRONLY | os.O_DIRECT | os.O_SYNC)
    except OSError as e:
        logger.error('Failed to open file %s: %s', filename, e.strerror)
        raise

    try:
        for _ in range(num_blocks):
            try:
                os.write(fd, random_block)
            except OSError as e:
                logger.error('Failed to write to file %s: %s', filename, e.strerror)
                raise
        remainder = file_size % block_size_bytes
        if remainder != 0:
            logger.warning('Remainder is %s, truncating', remainder)
    finally:
        os.fsync(fd)  # ensure all internal buffers associated with fd are written to disk
        os.close(fd)


# TODO: Create_test_files doesn't seem to be working properly for directory mode.
# ./run_fio.py -N deleteme -T JonBWRead --ips 10.0.1.201 10.0.1.202 10.0.1.203 -r 300 -s 10G  -b 1m -j 24 -q 4 -n 1 -i
# libaio -t /mnt/hsshare -D
def create_test_files(num_testfiles: int, files_per_job: int, file_create_threads: int, test_dir: str, block_size: str,
                      file_size: str, ip: str, dir_mode: typing.Union[bool, str], nrfiles: int) -> str:
    """
    Creates a specified number of test files. The file creation tasks are processed in chunks, and the number of
    simultaneous tasks is defined by the number of file creation threads.

    The function arranges the tasks in a list of tuples, each containing the directory for the test files, the block
    size for each file, the size of each file, a unique identifier, and an IP address.

    Args:
        num_testfiles (int): The number of test files to create.
        files_per_job (int): The number of files to create per job.
        file_create_threads (int): The number of threads to use for creating files.
        test_dir (str): The directory where the test files will be created.
        block_size (str): The size of each block in the test files.
        file_size (str): The size of each test file.
        ip (str): The IP address of the server where the test files will be created.
        dir_mode (bool): Whether the use_directory_mode was selected
        nrfiles (int): Number of files per fio job for directory mode.

    Returns:
        str: A message indicating the success of the file creation process.
    """
    num_testfiles = int(num_testfiles)
    file_create_threads = int(file_create_threads)
    files_per_job = int(files_per_job)
    dir_mode = eval(dir_mode)
    nrfiles = int(nrfiles)
    number_jobs = num_testfiles // files_per_job
    tasks = []  # Define tasks outside the loop

    for j in range(1, number_jobs + 1):
        if dir_mode:
            os.makedirs(f"{test_dir}/{ip}/job{j}", exist_ok=True)
        start = 0 if dir_mode else 1
        if dir_mode:
            for n in range(0, nrfiles):
                tasks.extend([(test_dir, block_size, round(convert_size(file_size)/nrfiles), i, j, ip, dir_mode, n)
                              for i in range(start, files_per_job)])
        else:
            tasks.extend([(test_dir, block_size, convert_size(file_size), i + files_per_job * (j - 1), j, ip, dir_mode,
                           1) for i in range(start, files_per_job + 1)])

    # Process the tasks in chunks
    for i in range(0, len(tasks), file_create_threads):
        with multiprocessing.Pool(processes=file_create_threads) as pool:
            end = min(i + file_create_threads, len(tasks))
            logger.info(f'Creating test files {i + 1}-{end}')
            pool.starmap(create_file, tasks[i:i + file_create_threads])

    # TODO: Add resilience
    return 'Successfully created files'


def start_nfsio_stats(run_timestamp: str, output_dir: str) -> str:
    """
    Initiates the nfsiostat tool to begin collecting NFS IO statistics. If the nfsiostat process is already running, the
    function will not start another process. The statistics will be written into an output file in the provided
    output directory. If the directory doesn't exist, it is created.

    Args:
        run_timestamp (str): A timestamp string which gets included in the output filename.
        output_dir (str): Directory where the output file will be saved.

    Returns:
        str: The full path of the output file.

    Raises:
        Exception: If the nfsiostat process is already running.
    """
    global nfsio_proc

    # TODO: make sure callee is properly handling this condition
    # Do not start if there's a running process already
    if nfsio_proc is not None:
        print('Error: NFS IO Stats is already running')
        return ''

    if not os.path.isdir(output_dir):
        print(f"The directory {output_dir} does not exist. Creating it now.")
        os.makedirs(output_dir, exist_ok=True)
    if not output_dir.endswith('/'):
        # Ensure the output directory path ends with a trailing slash
        output_dir += '/'

    filename = f'{output_dir}nfsio_stats_{run_timestamp}.txt'
    command = ['nfsiostat', '1']
    with open(filename, 'w') as f:
        nfsio_proc = subprocess.Popen(command, stdout=f)

    return filename


def stop_and_parse_nfsio_stats(filename: str) -> None:
    """
    Stops the nfsiostat process if it is currently running. If the process is not running, returns an error
    message "No NFS IO Stats process to stop" and exits the function.

    The function then reads the contents of the file provided by the filename parameter, parses the output
    into a CSV format and saves the result with the same filename but with a .csv extension.

    Args:
        filename (str): The name of the file that should be processed.
    """
    global nfsio_proc

    # Do not attempt to stop if no process is running
    if nfsio_proc is None:
        print('Error: No NFS IO Stats process to stop')
        return

    nfsio_proc.terminate()

    # Parse the output to CSV
    with open(filename, 'r') as f:
        output = f.read()

    csv_filename = filename.replace('.txt', '.csv')
    parse_nfsio_output(output, csv_filename)


# TODO: This function current assumes a single NFS mount and parses the output.  Investigation required for multiple.
def parse_nfsio_output(output: str, filename: str):
    """
    Parses the output from NFS IO stats by splitting it into lines. Each line is checked for the presence of
    'mounted on', which signifies the presence of NFS mount and mount point details.

    If 'mounted on' is found, the line is split into NFS mount and mount point. Otherwise, the numerical statistics
    from the line are extracted and appended to the data list.

    The parsed data is then written to a CSV file with the headers and data.

    Args:
        output (str): An output string containing the NFS IO statistics.
        filename (str): The name of the file where the parsed data will be written.

    Returns:
        None
    """
    lines = output.splitlines()
    headers = ['nfs_mount', 'mount_point', 'ops/s', 'rpc bklog',
               'read ops/s', 'read kB/s', 'read kB/op', 'read retrans',
               'read avg RTT (ms)', 'read avg exe (ms)', 'read avg queue (ms)', 'read errors',
               'write ops/s', 'write kB/s', 'write kB/op', 'write retrans',
               'write avg RTT (ms)', 'write avg exe (ms)', 'write avg queue (ms)', 'write errors']
    data = []

    # look for 'mounted on' in each line, identifies which line contains mount and mount point details
    pattern = r'mounted on'
    for line in lines:
        if pattern in line:
            # split the line based on 'mounted on' to separate the nfs_mount and mount_point
            nfs_mount, mount_point = line.split(' mounted on ')
            # strip ':' from the end of mount_point
            mount_point = mount_point.strip(':')
            data.extend([nfs_mount, mount_point])
        else:
            # append numerical statistics
            data.extend(re.findall(r'(\d+\.\d+|\d+ \(\d+\.\d+%\))', line))

    # After you've processed all the lines, write the data to the CSV file
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(headers)
        # write data in chunks of len(headers)
        for i in range(0, len(data), len(headers)):
            writer.writerow(data[i: i + len(headers)])


def remote_checks(test_dir: str, num_testfiles: int, file_create_threads: int, skip_creation: typing.Union[bool, str],
                  ip_address: str, files_per_job: int, dir_mode: typing.Union[bool, str], nrfiles: int) -> tuple:
    """
    This function is intended to be invoked on a remote server to ensure that the test environment is set up correctly.

    It performs checks such as verifying the existence of the test directory, checking that the number of file creation
    threads is not greater than the CPU count, and confirming if NFS is mounted.

    It also checks if private access rights are available in the absence of root privileges, and if the script is
    instructed to skip file creation, it confirms the presence of all necessary files.

    The function returns a tuple: the first element is a boolean indicating if any argument errors were encountered,
    and the second is a string describing the outcome of the checks.

    Args:
        test_dir (str): The directory path where the tests will be performed.
        num_testfiles (int): The number of test files to be created.
        file_create_threads (int): The number of threads to be used for creating files.
        skip_creation (bool): Boolean value indicating whether to skip file creation.
        ip_address (str): The IP address of the remote machine.
        files_per_job (int): The number of files to assign per job.
        dir_mode (bool): Boolean value indicating use of directory mode over filename mode.
        nrfiles (int): The number of file to share in a directory for directory mode.

    Returns:
        tuple: A tuple containing a boolean indicating whether any argument error occurred, and a string representing
        the result of the remote checks.
    """
    num_testfiles = int(num_testfiles)
    file_create_threads = int(file_create_threads)
    skip_creation = eval(skip_creation)
    files_per_job = int(files_per_job)
    dir_mode = eval(dir_mode)
    nrfiles = int(nrfiles)

    arg_error = False

    check_result_str = ''

    # Checks for root to later check permissions
    is_root_privilege = True
    if not os.getuid() == 0:
        check_result_str += f"WARN: {ip_address}: Script doesn't have root privileges cannot perform all checks\n"
        is_root_privilege = False

    # Check test_dir
    test_dir_present = True
    if not os.path.isdir(test_dir):
        check_result_str += f"ERROR: {ip_address}: test_dir: The directory {test_dir} does not exist.\n"
        arg_error = True
        test_dir_present = False

    server_dir = f'{test_dir}/{ip_address}'
    if test_dir_present and not os.path.isdir(server_dir):
        try:
            os.mkdir(server_dir)
        except Exception as e:
            print(f'Error: {ip_address}: An error occurred while creating directory: {str(e)}\n')
            arg_error = True

    # Check test_dir has an NFS filesystem mounted
    if not is_nfs_mount(test_dir):
        check_result_str += f"ERROR: {ip_address}: test_dir: {test_dir} does not have an NFS filesystem mounted\n"
        arg_error = True

    # If not root see that access to mount point and existing files exists
    if not is_root_privilege and test_dir_present:
        check_result_str += (f"WARN: {ip_address}: Script doesn't have root privileges, checking non-root access "
                             f"permissions\n")
        if not test_nonroot_access(test_dir):
            arg_error = True

    # Check that all files already exist if you are asking to bypass file creation
    if skip_creation:
        files_per_job = int(files_per_job)
        number_jobs = num_testfiles // files_per_job
        all_files_present = True
        if dir_mode:
            for j in range(1, number_jobs + 1):
                for i in range(0, files_per_job):
                    for f in range(0, nrfiles):
                        filename = f"{test_dir}/{ip_address}/job{j}/testfile{i}.{f}"
                        if not os.path.exists(filename):
                            all_files_present = False
                            arg_error = True
        else:
            for i in range(1, num_testfiles + 1):
                filename = f"{test_dir}/{ip_address}/testfile{i}"
                if not os.path.exists(filename):
                    all_files_present = False
                    arg_error = True
        if not all_files_present:
            check_result_str += f"ERROR: {ip_address}: not all testfiles are present\n"

    # Check file_create_threads is a positive integer and not greater than cpu_count
    max_cpu_count = multiprocessing.cpu_count()
    if not (0 < file_create_threads <= max_cpu_count):
        check_result_str += (f'ERROR: {ip_address}: file_create_threads: "{file_create_threads}" is invalid. File '
                             f'create threads should be a positive integer and not more than the number of CPU cores '
                             f'which is {max_cpu_count}.\n')
        arg_error = True

    if not arg_error:
        check_result_str = f'INFO: {ip_address}: All remote checks passed.'

    return arg_error, check_result_str


def generate_fio_jobfiles(args: argparse.Namespace, directory: str) -> typing.Optional[dict]:
    """
    Generates FIO (Flexible I/O Tester) job files based on the provided parameters.

    If the directory does not exist, an error message is logged and the function returns. A base jobfile is
    created using the attributes from args. If a mixed workload is chosen (either readwrite or randrw), the
    rw-mixread is used to set read and write percentages.

    The function supports the creation of multiple job Files per IP by dividing the number of test files by the
    number of files per job. If a job file already exists, it's overwritten.

    attributes used for jobfile creation: file_size, block_size, queue_depth, run_time, io_engine, fio_numjobs,
    io_direction, rw_mixread, test_dir, num_testfiles, files_per_job, ips, and test_name.

    Args:
        args (Any): An object containing the arguments for generating the job files. It should contain the
        directory (str): The directory where the job files will be created.

    Returns:
        dict: A dictionary with IP addresses as keys and corresponding job file paths as values.
    """
    # TODO: make sure to handle None return properly from callee
    if not os.path.exists(directory):
        logger.error(f"Directory {directory} for jobfile creation doesn't exist. Exiting...")
        return None
    script_param_to_fio_jobfile = {
        'block_size': 'bs',
        'queue_depth': 'iodepth',
        'io_engine': 'ioengine',
        'fio_numjobs': 'numjobs'
    }

    base_jobfile = f"""
[global]
group_reporting=1
create_serialize=0
direct=1"""

    if args.template:
        if 'globals' in TEMPLATES[args.template].keys():
            base_jobfile += '\n' + '\n'.join(f"{key}={value}" for key, value in
                                             TEMPLATES[args.template]['globals'].items())

    for fio_global in ['block_size', 'queue_depth', 'io_engine', 'fio_numjobs']:
        if hasattr(args, fio_global):
            base_jobfile += f"\n{script_param_to_fio_jobfile[fio_global]}={getattr(args, fio_global)}"

    # If directory mode the add filename_format and unique_filename
    if args.use_directory_mode:
        base_jobfile += f"""
size={convert_size(args.file_size)}
filename_format=$jobname/testfile$jobnum.$filenum
unique_filename=0"""
    else:
        base_jobfile += f"\nsize={convert_size(args.file_size) * args.files_per_job}"

    # If directory mode the add filename_format and unique_filename
    if args.run_time:
        base_jobfile += f"""
runtime={args.run_time}
time_based"""

    if args.loops:
        base_jobfile += f"\nloops={args.loops}"

    # Determine if mixed workload was selected and use rwmixread to set percentages
    if args.io_direction in ['rw', 'readwrite', 'randrw']:
        base_jobfile += f"""
rw={args.io_direction} 
rwmixread={args.rw_mixread}"""
    else:
        base_jobfile += f"""
rw={args.io_direction}
"""

    ip_file_dict = {}

    number_jobs = int(args.num_testfiles / args.files_per_job)
    for ip in args.ips:
        jobfile_text = base_jobfile  # Copy the base jobfile
        for i in range(1, number_jobs + 1):
            if args.use_directory_mode:
                jobfile_text += f"""
[job{i}]
directory={args.test_dir}/{ip}/"""
                if args.nrfiles > 1:
                    # TODO: Need to consider args.files_per_job comparison. Right now nrfiles can make more files.
                    jobfile_text += f"""
nrfiles={args.nrfiles}
"""
            else:
                if args.files_per_job == 1:
                    jobfile_text += f"""
[job{i}]
filename={args.test_dir}/{ip}/testfile{i}
"""
                else:
                    filenames = ":".join(f"{args.test_dir}/{ip}/testfile{j + ((i - 1) * args.files_per_job)}"
                                         for j in range(1, args.files_per_job + 1))
                    jobfile_text += f"""
[job{i}]
filename={filenames}
"""

        jobfile_path = os.path.join(directory, f'{args.test_name}_{ip}.fio')

        if os.path.exists(jobfile_path):
            logger.warning(f"File {jobfile_path} already exists. Overwriting...")

        # Write the jobfile_text for this IP to its own file
        with open(jobfile_path, 'w') as f:
            f.write(jobfile_text)

        ip_file_dict[ip] = jobfile_path  # Add the filename to the dictionary.

    return ip_file_dict


def run_fio_command(command: str) -> tuple:
    """
    Executes the given command using Python's subprocess module.

    The function captures stdout and stderr from the executed command. It then splits the stdout lines and seeks
    for the start of JSON data. If the JSON data is correctly formed, it is parsed and returned. If there's any
    error during JSON parsing, it returns the error as a string.

    Args:
        command (str): An executable command provided as a string.

    Returns:
        tuple: A Python tuple containing two elements
            - The parsed JSON data as Python data structures if possible, otherwise None.
            - The stderr output from executing the command as a string.
    """
    # TODO: Determine whether or not this should use the run_command_and_wait function.
    try:
        result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except Exception as e:
        logger.error(f"Exception occurred while running the command: {str(e)}")
        return None, str(e)

    try:
        # Split the stdout lines and look for the start of json data
        stdout_lines = result.stdout.decode('utf-8').splitlines()
        json_start = next(i for i, line in enumerate(stdout_lines) if line.startswith('{'))

        # Join lines starting from json_start and parse as JSON
        json_string = '\n'.join(stdout_lines[json_start:])
        stdout_output = json.loads(json_string)
    except json.JSONDecodeError as e:
        logger.error(f"Error while parsing the command output to JSON: {str(e)}")
        return None, str(e)

    return stdout_output, result.stderr.decode('utf-8')


def flatten_json(json_in) -> dict:
    """
    Recursively flattens a JSON object (that can be nested dictionaries and lists) into a dictionary.

    The function generates a flattened dictionary from an input JSON object. The keys in this dictionary are based on
    the paths to the values in the original JSON object.

    For example, a JSON object like {"a": {"b": 1, "c": 2}} would be flattened to {"a_b": 1, "a_c": 2}.

    If the function encounters a list, it iterates over the list elements appending the index to the name path.

    Args:
        json_in (Union[dict, list]): A JSON object that needs to be flattened. The JSON object can be a dictionary or a
        list, and can contain nested dictionaries and lists.

    Returns:
        dict: A dictionary representation of the input JSON object that is flattened.
    """
    out = {}

    def flatten(x, name: str = '') -> None:
        """
        A helper function that is used in the "flatten_json" function for recursive flattening of the JSON object.

        The function takes an element of the JSON object and a name which is used as a key in the resulting flattened
        dictionary.

        If the element is of type dictionary, it recursively calls flatten for each of its keys.
        If the element is of type list, it recursively calls flatten on each of its elements and appends the index to
        the name. Otherwise, it treats the element as a terminal value and updates the flattened dictionary 'out' with
        the corresponding path and value.

        Note: This function does not return. It modifies the dictionary 'out' in place.

        Args:
            x (Union[dict, list, any]): The element of the JSON object that's currently processed and to be flattened.
            name (str): The path used for creating keys in the resulting flattened dictionary.

        Returns:
            None
        """
        if type(x) is dict:
            for a in x:
                flatten(x[a], name + a + '_')
        elif type(x) is list:
            i = 0
            for a in x:
                flatten(a, name + str(i) + '_')
                i += 1
        else:
            out[name[:-1]] = x

    flatten(json_in)
    return out


def json_to_csv(json_out: dict, out_csv: str) -> None:
    """
    Converts a JSON object to a CSV file.

    The JSON object is first flattened into a dictionary using the function 'flatten_json'. This resulting dictionary
    is then written into a CSV file where the keys form the header and values form the rows.

    Args:
        json_out (dict): A JSON object that needs to be converted to a CSV file.
        out_csv (str): The filename of the CSV file which will be written.

    Returns:
        None
    """
    # Flatten JSON
    json_out_flat = flatten_json(json_out)
    # Open (or create) CSV file
    with open(out_csv, 'w', newline='') as file:

        # Create CSV writer
        writer = csv.writer(file)

        # Write header
        header = json_out_flat.keys()
        writer.writerow(header)

        # Write values
        values = json_out_flat.values()
        writer.writerow(values)


# =====================================
# MAIN
# =====================================


def main():
    args = None
    try:
        # Generate a formatted timestamp at the beginning of your script
        run_timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

        parser = argparse.ArgumentParser(description='Generate and run fio command',
                                         formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        parser.add_argument('-P', '--print_templates', action='store_true', default=False,
                            help='Print templates and their settings')

        # Server Mode
        parser.add_argument('--server', action='store_true', default=False,
                            help='Start script in server mode')

        # Paths and directories
        # TODO: Known issue with failure if test_dir is given with trailing slash.  need to add check and parse better.
        parser.add_argument('-t', '--test_dir', default='/mnt/hs_rdma',
                            help='Directory in which test files are stored, usually an NFS mount point')
        parser.add_argument('-o', '--output_dir', default='./fio_results/',
                            help='The directory to store output files. Defaults to "./fio_results/".')

        # Test configuration
        parser.add_argument('-T', '--template', help='Preset configurations to use',
                            choices=list(TEMPLATES.keys()))
        parser.add_argument('-D', '--use_directory_mode', action='store_true',
                            help="Use --directory instead of --filename.")
        parser.add_argument('--nrfiles', type=int,
                            help='When using directory mode nrfiles is used to specify how many files to generate per'
                                 'fio job/thread. (Requires -D)')
        parser.add_argument('-N', '--test_name', default='',
                            help='Test name used for test directory names.')
        parser.add_argument('-s', '--file_size', default='4G',
                            help='Test file size in "m, g, or t", total capacity used will be file_size * '
                                 'num_testfiles')
        parser.add_argument('-l', '--loops', type=int, help='Number of times to run jobs')
        parser.add_argument('-r', '--run_time', type=int, help='Run time in seconds')
        parser.add_argument('-n', '--num_testfiles', default=2, type=int,
                            help='Number of test files to generate and test against. '
                                 'Total number of threads is num_testfiles * fio_numjobs')
        parser.add_argument('-S', '--skip_creation', action='store_true', default=False,
                            help="Skip the file creation step")
        parser.add_argument('-F', '--file_create_threads', type=int, default=multiprocessing.cpu_count(),
                            help='Maximum number of parallel threads to use for file creation')
        parser.add_argument('--ips', nargs='+', type=valid_ip, required=False,
                            help='Space separated list of IP addresses of systems to test. This script assumes '
                                 'localhost if no IPs given.')

        # Fio configurations
        parser.add_argument('-b', '--block_size', default='1m',
                            help='Block size to be used with fio command in "k or m"')
        parser.add_argument('-i', '--io_engine', default='libaio', choices=['libaio', 'posixaio'],
                            help='IO engine used for fio commands')
        parser.add_argument('-d', '--io_direction', default='readwrite',
                            choices=['rw', 'readwrite', 'read', 'write', 'randrw', 'randread', 'randwrite'],
                            help='IO direction and type used for fio commands')

        parser.add_argument('-f', '--files_per_job', default='1', type=int,
                            help='If greater than 1 a colon delimited list of files will be used per job. files_per_job'
                                 ' should divide evenly into num_testfiles')
        parser.add_argument('-m', '--rw_mixread', default='50', type=int,
                            help='Ratio of reads to writes in mixed workloads')
        parser.add_argument('-j', '--fio_numjobs', default='2', type=int,
                            help='Number of threads to run per fio job')
        parser.add_argument('-q', '--queue_depth', default='16', type=int,
                            help='Queue depth to be used for each job/thread')

        # Store the command line arguments (don't parse yet, so the defaults are not filled in.)
        args = argparse.Namespace()
        parser.parse_args(namespace=args)

        # Apply the template values if the template arg is used
        if args.template:
            template_values = TEMPLATES[args.template]
            for arg, value in template_values.items():
                setattr(args, arg, value)  # We strip the '-' from the arg name to match the attribute name

        parser.parse_args(namespace=args)

        if args.use_directory_mode is None:
            args.use_directory_mode = False

        if args.nrfiles and not args.use_directory_mode:
            parser.error("--nrfiles requires --use_directory_mode to be set")
        if not args.nrfiles:
            args.nrfiles = 1

        if args.print_templates:
            print_templates_information()
            sys.exit(0)

        if args.server:
            listener()
            sys.exit(0)

        # Argument checking
        arg_error = False

        # Local Argument checks
        # Check ssh access to remote servers
        for ip in args.ips:
            if not test_ssh_access(ip, 'root'):
                # Handle the error appropriately, you could either exit the program or remove the IP from the list
                print(f"Non-interactive SSH session failed for IP: {ip}")
                arg_error = True

        # Check output_dir
        if not os.path.isdir(args.output_dir):
            print(f"ERROR: output_dir: The directory {args.output_dir} does not exist.")
            arg_error = True
        elif not args.output_dir.endswith('/'):
            # Ensure the output directory path ends with a trailing slash
            args.output_dir += '/'

        # Check block_size and file_size
        try:
            convert_size(args.block_size)
            convert_size(args.file_size)
        except ValueError:
            print("ERROR: block_size or file_size: Block size and file size should be valid size strings "
                  "(like '10m', '1g', etc.)")
            arg_error = True

        # Check rw_mixread is a percentage
        if args.rw_mixread < 0 or args.rw_mixread > 100:
            print('ERROR: rw_mixread: "%s" is an invalid percentage value. It should be within 0-100.', args.rw_mixread)
            arg_error = True

        # Checks that runtime is greater than 0. Argument to be had here is a minimum runtime as 1 second is silly
        if args.run_time and args.run_time <= 0:
            print('ERROR: run_time: "%s" is an invalid value. It should be greater than 0.', args.run_time)
            arg_error = True

        # Check num_testfiles is a positive integer
        if args.num_testfiles <= 0:
            print("ERROR: num_testfiles: Number of test files should be a positive integer.")
            arg_error = True

        if args.files_per_job <= 0:
            print("ERROR: files_per_job: Files per job should be a positive integer.")
            arg_error = True
        elif args.files_per_job != 1:
            if args.num_testfiles % args.files_per_job != 0:
                print("ERROR: files_per_job: Files per job should divide evenly into num_testfiles.")
                arg_error = True

        # Check num_job is a positive integer
        if args.fio_numjobs <= 0:
            print("ERROR: fio_numjobs: fio number of jobs should be a positive integer.")
            arg_error = True

        # Setup remote server
        for ip in args.ips:
            max_attempts = 3
            user = 'root'
            source_file = os.path.realpath(__file__)
            destination_path = f'/tmp/{os.path.basename(__file__)}'
            command = f'scp {source_file} {user}@{ip}:{destination_path}'
            for attempt in range(max_attempts):
                if run_command_and_wait(command):
                    break
                else:
                    time.sleep(2 ** attempt)

            server_log = f"/tmp/{os.path.splitext(os.path.basename(__file__))[0]}_output_{run_timestamp}.log"
            command = f'ssh {user}@{ip} "nohup python3 {destination_path} --server &> {server_log} &"'
            attempt = 0
            for attempt in range(30):  # Try for 30 times
                if run_command_and_go(command):
                    port_check_attempt = 0
                    for port_check_attempt in range(30):  # Try to check the port for 30 times
                        if is_port_open(ip, 5000):
                            print(f'INFO: "run_fio.py --server" successfully launched on "{ip}"')
                            break  # Exit inner loop if port is open
                        else:
                            time.sleep(1)  # Wait for a second before checking again
                    else:
                        print(f'WARNING: Port {5000} did not become available after {port_check_attempt + 1} seconds '
                              f'on "{ip}". Retrying to launch the server.')
                        continue  # Continue the outer loop if port did not open within 30 seconds
                else:
                    print(f'ERROR: Command "{command}" failed')
                    time.sleep(1)  # Wait for a second before trying to re-run the command
                break  # Exit outer loop if command succeeded and port is open
            else:
                print(f"ERROR: `{command}` did not succeed after {attempt + 1} attempts")

        # Check test environment on each machine
        max_attempts = 3
        time.sleep(5)
        for ip in args.ips:
            print(f'INFO: Initiating remote environment checks on "{ip}"')
            for attempt in range(max_attempts):
                time.sleep(2 ** attempt)
                success, response = sender(ip, 5000, f'remote_checks, {args.test_dir}, {args.num_testfiles}, '
                                                     f'{args.file_create_threads}, {args.skip_creation}, {ip}, '
                                                     f'{args.files_per_job}, {args.use_directory_mode}, {args.nrfiles}',
                                           False, False)
                if success:
                    remote_arg_error, remote_errors = eval(response)
                    if remote_arg_error:
                        arg_error = True
                        print(remote_errors)
                    break

        # Exits after all parameters are checked
        if arg_error:
            print('ERROR: Too many invalid arguments -- aborting')
            for ip in args.ips:
                sender(ip, 5000, f'quit', False, False)
            parser.print_help()
            sys.exit(1)

        # Generate a formatted timestamp at the beginning of your script
        run_timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

        # Create a directory for this run's output
        output_dir = os.path.expanduser(f'{args.output_dir}{run_timestamp}'
                                        f'{"_" + args.test_name if args.test_name != "" else ""}/')
        os.makedirs(output_dir, exist_ok=True)

        # Create a logfile for this run
        logfile = os.path.join(output_dir, f'output_log_{run_timestamp}.log')

        # Configure logging
        logger.setLevel(logging.DEBUG)

        # Setup handlers for console and log file output
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        file_handler = logging.FileHandler(filename=logfile, mode='w')
        file_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s: %(name)s: [%(levelname)s] %(message)s',
                                      datefmt='%Y-%m-%d %H:%M:%S')
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)

        # Add Handlers
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

        # Document how the script was run.
        logger.debug('This script was run with: %s', ' '.join(sys.argv))

        logger.debug('Copying running script "%s" to "%s"', __file__, output_dir)
        shutil.copy2(__file__, output_dir)

        if args.fio_numjobs > args.files_per_job:
            logger.info(f'Current configuration will result in "{args.files_per_job}" files per job and '
                        f'"{args.fio_numjobs}" threads per job. This means the threads will share files with '
                        f'concurrent access')

        if args.template:
            logger.info(f'Loading template "{args.template}"')
            print_arg_info(args, TEMPLATES[args.template])

        # Generate test files
        # Skip creation if args.skip_creation is True
        if args.skip_creation:
            logger.info('Skipping file creation as per the arguments')
        else:
            logger.info('Starting file creation')
            # Parallelize calls to sender function with ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=len(args.ips)) as executor:
                executor.map(lambda ip_inner:
                             sender(ip_inner, 5000,
                                    f'create_test_files, {args.num_testfiles}, {args.files_per_job}, '
                                    f'{args.file_create_threads}, {args.test_dir}, {args.block_size}, {args.file_size},'
                                    f' {ip_inner}, {args.use_directory_mode}, {args.nrfiles}', True, True),
                             args.ips)

        # Launch fio servers
        for ip in args.ips:
            logger.debug(f'Starting fio server on {ip}')
            command = 'fio --server &'
            sender(ip, 5000, f'run_command_and_go, {command}', True, True)

        fio_server_timeout = 30
        for ip in args.ips:
            for _ in range(fio_server_timeout):
                if is_port_open(ip, 8765):
                    logger.debug(f'Fio server came online on "{ip}"')
                    break
                else:
                    time.sleep(5)
            else:
                logger.error(f"Fio server did not start at {ip} within timeout period")
                sys.exit(1)

        logger.info('Generating fio jobfiles for each server')
        jobfiles = generate_fio_jobfiles(args, '/tmp/')

        # Start collecting nfsiostat stats
        nfsio_procs = {}
        for ip in args.ips:
            logger.debug('Starting collection of nfsiostat on "%s"', ip)
            nfsio_procs[ip] = sender(ip, 5000,
                                     f'start_nfsio_stats, {run_timestamp}, /tmp/{ip}_{run_timestamp}',
                                     True, True)

        fio_command = "fio --output-format=json"
        for ip, jobfile in jobfiles.items():
            fio_command += f" --client={ip} {jobfile}"

        logger.info(f'Running command: {fio_command}')
        stdout, stderr = run_fio_command(fio_command)

        # Stop collecting nfsiostat stats and parse the output
        for ip in args.ips:
            logger.debug('Stopping collection of nfsiostat and parsing on "%s"', ip)
            nfsio_procs[ip] = sender(ip, 5000, f'stop_and_parse_nfsio_stats, {nfsio_procs[ip][1]}',
                                     True, True)

        fio_csv = os.path.join(output_dir, f'fio_output_{run_timestamp}.csv')
        logger.debug('Writing out fio results to "%s"', fio_csv)

        fio_results = [FIOResult(stdout, i) for i in range(len(stdout['client_stats']))]
        total_fio = reduce(lambda a, b: a + b, fio_results)
        logger.info(total_fio)
        json_to_csv(stdout, fio_csv)

        clients_dir = os.path.join(output_dir, 'clients')
        # Create a subdirectory 'jobfiles' under output_dir if it doesn't exist
        os.makedirs(clients_dir, exist_ok=True)
        # Collect remote files
        for ip in args.ips:
            user = 'root'
            sender(ip, 5000, f'create_tarfile, /tmp/{ip}_{run_timestamp}', True, True)
            # name of the tar file
            tar_file = f"/tmp/{ip}_{run_timestamp}.tgz"
            command = f'scp {user}@{ip}:{tar_file} {clients_dir}'
            run_command_and_wait(command)

        jobfiles_dir = os.path.join(output_dir, 'jobfiles')
        # Create a subdirectory 'jobfiles' under output_dir if it doesn't exist
        os.makedirs(jobfiles_dir, exist_ok=True)
        # Copy jobfiles to output/jobfiles dir
        for _, jobfile in jobfiles.items():
            shutil.move(jobfile, jobfiles_dir)

        if stdout:
            logger.debug(f'Output:\n{json.dumps(stdout, indent=4)}')

        if stderr:
            logger.error(f'Errors:\n{stderr}')

        logger.info('Testing complete, please refer to "%s" for more details', output_dir)
    except KeyboardInterrupt:
        print("Ctrl-C received, exiting...")
    except SystemExit as e:
        pass
    except BaseException as e:
        print(f"Unhandled exception: {str(e)}")
        logger.error(e, exc_info=True)
    finally:
        if not args.print_templates:
            cleanup(args)


if __name__ == "__main__":
    main()
