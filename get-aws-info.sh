#!/bin/bash

# This script will take the first client IP from the inventory file and
# then use the aws cli to get the instance type, cpus, memory, network, and attached EBS volumes (including IOPS and throughput)

# Extract the first client IP and total client count from inventory.ini
FIRST_CLIENT_IP=$(awk '/\[clients\]/ {flag=1; next} /\[/{flag=0} flag && $0 ~ /^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+/ {print $1; exit}' ../inventory.ini)
TOTAL_CLIENTS=$(awk '/\[clients\]/ {flag=1; next} /\[/{flag=0} flag && $0 ~ /^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+/ {count++} END {print count+0}' ../inventory.ini)

if [ ${TOTAL_CLIENTS} -ne 0 ]; then
    # Get client instance ID (for EBS query) and type
    CLIENT_INSTANCE_ID=$(aws ec2 describe-instances --filters "Name=private-ip-address,Values=$FIRST_CLIENT_IP" --query "Reservations[0].Instances[0].InstanceId" --output text)
    CLIENT_INSTANCE_TYPE=$(aws ec2 describe-instances --filters "Name=private-ip-address,Values=$FIRST_CLIENT_IP" --query "Reservations[0].Instances[0].InstanceType" --output text)

    # Get client details as JSON
    CLIENT_JSON=$(aws ec2 describe-instance-types --instance-types $CLIENT_INSTANCE_TYPE --query "InstanceTypes[0].{InstanceType:InstanceType, vCPUs:VCpuInfo.DefaultVCpus, MemoryMiB:MemoryInfo.SizeInMiB, NetworkBandwidth:NetworkInfo.NetworkPerformance}" --output json)

    # Get attached EBS volumes for client as JSON array (includes IOPS and throughput)
    CLIENT_EBS_JSON=$(aws ec2 describe-volumes --filters "Name=attachment.instance-id,Values=$CLIENT_INSTANCE_ID" --query "Volumes[*].{VolumeId:VolumeId, Device:Attachments[0].Device, Size:Size, VolumeType:VolumeType, Iops:Iops, Throughput:Throughput}" --output json)
else
    CLIENT_JSON="{}"
fi

# Extract the first storage server IP and total storage server count from inventory.ini
FIRST_STORAGE_IP=$(awk '/\[storage_servers\]/ {flag=1; next} /\[/{flag=0} flag && $0 ~ /^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+/ {print $1; exit}' ../inventory.ini)
TOTAL_STORAGE_SERVERS=$(awk '/\[storage_servers\]/ {flag=1; next} /\[/{flag=0} flag && $0 ~ /^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+/ {count++} END {print count+0}' ../inventory.ini)

# Get storage server instance ID and type
if [ ${TOTAL_STORAGE_SERVERS} -ne 0 ]; then
    STORAGE_INSTANCE_ID=$(aws ec2 describe-instances --filters "Name=private-ip-address,Values=$FIRST_STORAGE_IP" --query "Reservations[0].Instances[0].InstanceId" --output text)
    STORAGE_INSTANCE_TYPE=$(aws ec2 describe-instances --filters "Name=private-ip-address,Values=$FIRST_STORAGE_IP" --query "Reservations[0].Instances[0].InstanceType" --output text)

    # Get storage server details as JSON
    STORAGE_JSON=$(aws ec2 describe-instance-types --instance-types $STORAGE_INSTANCE_TYPE --query "InstanceTypes[0].{InstanceType:InstanceType, vCPUs:VCpuInfo.DefaultVCpus, MemoryMiB:MemoryInfo.SizeInMiB, NetworkBandwidth:NetworkInfo.NetworkPerformance}" --output json)

    # Get attached EBS volumes for storage server as JSON array (includes IOPS and throughput)
    STORAGE_EBS_JSON=$(aws ec2 describe-volumes --filters "Name=attachment.instance-id,Values=$STORAGE_INSTANCE_ID" --query "Volumes[*].{VolumeId:VolumeId, Device:Attachments[0].Device, Size:Size, VolumeType:VolumeType, Iops:Iops, Throughput:Throughput}" --output json)
else
    STORAGE_JSON="{}"
    STORAGE_EBS_JSON="{}"
fi

# Extract the first ECGroup node IP and total ECGroup node count from inventory.ini
FIRST_ECGROUP_IP=$(awk '/\[ecgroup_nodes\]/ {flag=1; next} /\[/{flag=0} flag && $0 ~ /^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+/ {print $1; exit}' ../inventory.ini)
TOTAL_ECGROUP_SERVERS=$(awk '/\[ecgroup_nodes\]/ {flag=1; next} /\[/{flag=0} flag && $0 ~ /^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+/ {count++} END {print count+0}' ../inventory.ini)

# Get ECGroup node instance ID and type
if [ ${TOTAL_ECGROUP_SERVERS} -ne 0 ]; then
    ECGROUP_INSTANCE_ID=$(aws ec2 describe-instances --filters "Name=private-ip-address,Values=$FIRST_ECGROUP_IP" --query "Reservations[0].Instances[0].InstanceId" --output text)
    ECGROUP_INSTANCE_TYPE=$(aws ec2 describe-instances --filters "Name=private-ip-address,Values=$FIRST_ECGROUP_IP" --query "Reservations[0].Instances[0].InstanceType" --output text)

    # Get ECGroup node details as JSON
    ECGROUP_JSON=$(aws ec2 describe-instance-types --instance-types $ECGROUP_INSTANCE_TYPE --query "InstanceTypes[0].{InstanceType:InstanceType, vCPUs:VCpuInfo.DefaultVCpus, MemoryMiB:MemoryInfo.SizeInMiB, NetworkBandwidth:NetworkInfo.NetworkPerformance}" --output json)

    # Get attached EBS volumes for ECGroup node as JSON array (includes IOPS and throughput)

    ECGROUP_EBS_JSON=$(aws ec2 describe-volumes --filters "Name=attachment.instance-id,Values=$ECGROUP_INSTANCE_ID" --query "Volumes[*].{VolumeId:VolumeId, Device:Attachments[0].Device, Size:Size, VolumeType:VolumeType, Iops:Iops, Throughput:Throughput}" --output json)
else
    ECGROUP_JSON="{}"
    ECGROUP_EBS_JSON="{}"
fi

# Extract the first hammerspace IP and total hammerspace count from inventory.ini
FIRST_HAMMERSPACE_IP=$(awk '/\[hammerspace\]/ {flag=1; next} /\[/{flag=0} flag && $0 ~ /^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+/ {print $1; exit}' ../inventory.ini)
TOTAL_HAMMERSPACE=$(awk '/\[hammerspace\]/ {flag=1; next} /\[/{flag=0} flag && $0 ~ /^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+/ {count++} END {print count+0}' ../inventory.ini)

if [ ${TOTAL_HAMMERSPACE} -ne 0 ]; then
    # Get hammerspace instance ID and type
    HAMMERSPACE_INSTANCE_ID=$(aws ec2 describe-instances --filters "Name=private-ip-address,Values=$FIRST_HAMMERSPACE_IP" --query "Reservations[0].Instances[0].InstanceId" --output text)
    HAMMERSPACE_INSTANCE_TYPE=$(aws ec2 describe-instances --filters "Name=private-ip-address,Values=$FIRST_HAMMERSPACE_IP" --query "Reservations[0].Instances[0].InstanceType" --output text)

    # Get hammerspace details as JSON
    HAMMERSPACE_JSON=$(aws ec2 describe-instance-types --instance-types $HAMMERSPACE_INSTANCE_TYPE --query "InstanceTypes[0].{InstanceType:InstanceType, vCPUs:VCpuInfo.DefaultVCpus, MemoryMiB:MemoryInfo.SizeInMiB, NetworkBandwidth:NetworkInfo.NetworkPerformance}" --output json)

    # Get attached EBS volumes for hammerspace as JSON array (includes IOPS and throughput)
    HAMMERSPACE_EBS_JSON=$(aws ec2 describe-volumes --filters "Name=attachment.instance-id,Values=$HAMMERSPACE_INSTANCE_ID" --query "Volumes[*].{VolumeId:VolumeId, Device:Attachments[0].Device, Size:Size, VolumeType:VolumeType, Iops:Iops, Throughput:Throughput}" --output json)
else
    HAMMERSPACE_JSON="{}"
    HAMMERSPACE_EBS_JSON="{}"
fi
    
# Combine into a single JSON output using jq
echo "{\"client\": $CLIENT_JSON, \"client_ebs_volumes\": $CLIENT_EBS_JSON, \"total_clients\": $TOTAL_CLIENTS, \"storage_server\": $STORAGE_JSON, \"storage_ebs_volumes\": $STORAGE_EBS_JSON, \"total_storage_servers\": $TOTAL_STORAGE_SERVERS, \"ecgroup_server\": $ECGROUP_JSON, \"ecgroup_ebs_volumes\": $ECGROUP_EBS_JSON, \"total_ecgroup_nodes\": $TOTAL_ECGROUP_SERVERS, \"hammerspace\": $HAMMERSPACE_JSON, \"hammerspace_ebs_volumes\": $HAMMERSPACE_EBS_JSON, \"total_hammerspace\": $TOTAL_HAMMERSPACE}" | jq .
