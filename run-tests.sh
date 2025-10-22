#!/bin/bash

# Check for required arguments
if [ $# -ne 2 ] || [ -z "$1" ] || ([ "$2" != "storage" ] && [ "$2" != "ecgroup" ]); then
    echo "Error: Incorrect or missing arguments."
    echo "Usage: $0 <test_name> <type>"
    echo "The first argument must be a non-empty string (test_name)."
    echo "The second argument must be either 'storage' or 'ecgroup'."
    exit 1
fi

# Output the arguments

echo "[performance-testing] --- Test Name - ${1}"
echo "[performance-testing] --- Storage Type - ${2}"

# Make sure we can run the setup.sh script. This is only possible
# if we have the inventory.ini file

if [ ! -f "../inventory.ini" ]; then
    echo "[performance-testing] --- Missing inventory.ini file"
    exit 1
fi

# Start by setting up the configuration files

echo "[performance-testing] --- Run the setup.sh script"

./setup.sh "$1" "$2" 

# Run the ior-Bandwith-scale-v4 script

echo "[performance-testing] --- Run the ior-Bandwidth-scale-v4 script"

./ior-Bandwidth-scale-v4.sh

# Now, run the ior-IOPs-scale-v4.sh script

echo "[performance-testing] --- Run the ior-IOPs-scale-v4 script"

./ior-IOPs-scale-v4.sh

# Run the cloud_data_path_tests script. These are FIO tests

echo "[performance-testing] --- Run the FIO (cloud_data_path_tests) script"

./cloud_data_path_tests.sh

# Output the number and types of instances

./get-aws-info.sh > ./aws-info 2>&1

# Capture all the logs

echo "[performance-testing] --- Capture all of the logs"

./capture-logs.sh

# Cleanup files - First get the info about the tests so we know what
# directories and files to delete

source config

# Start by unmounting

pdsh -w ^clients sudo umount /mnt/hs_test

# Now delete unwanted files

rm -rf results-$name
rm -rf fio_results
rm -rf logs-*
rm -rf hosts
rm servers clients config
