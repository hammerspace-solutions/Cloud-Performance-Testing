#!/bin/bash

# Check for required arguments
if [ $# -ne 2 ] || [ -z "$1" ] || ([ "$2" != "storage" ] && [ "$2" != "ecgroup" ]); then
    echo "Error: Incorrect or missing arguments."
    echo "Usage: $0 <test_name> <type>"
    echo "The first argument must be a non-empty string (test_name)."
    echo "The second argument must be either 'storage' or 'ecgroup'."
    exit 1
fi

./make-config.sh "$1" "$2" 

source config

sudo apt -y install openmpi-bin openmpi-common openmpi-doc libopenmpi-dev pdsh autoconf pkg-config miller
sudo apt -y install pdsh 
echo $client_ips
echo creating clients pdsh file

rm -rf clients servers
for i in `echo $client_ips`; do
	echo $i>>clients
done 

echo creating LSS pdsh file
for i in `echo $lss_ips`; do
        echo $i>>servers
done

echo Anvil IP is  $anvil_ips
c1=`head -n1  clients` 

echo installing packages
pdsh -w ^clients sudo apt -y install openmpi-bin openmpi-common openmpi-doc libopenmpi-dev pdsh

pdsh -w ^clients sudo mkdir -p /mnt/hs_test

pdsh -w ^clients sudo umount /mnt/hs_test
pdsh -w ^clients sudo mount -t nfs -o vers=4.2,nconnect=16,port=20492 ${anvil_ips}:/${share} /mnt/hs_test

ssh $c1 "sudo  apt  -y install autoconf pkg-config libopenmpi-dev make"
ssh $c1 "git clone https://github.com/IO500/io500.git; cd io500; bash ./prepare.sh" 
ssh $c1 "cp -rf io500 /mnt/hs_test/"
rm -rf hosts
mkdir -p hosts 

for i in `echo $client_ips`; do
        echo $i slots=1>>hosts/${client_num}
done
echo `head -n1 hosts/${client_num}`>hosts/1 

scp config-hammer-ec.ini ${c1}:/mnt/hs_test/io500 

echo ready to run IOR MDTEST or IO500 

sudo scp run_fio.py  ${c1}:/root 
sudo scp cloud_data_path_tests.sh ${c1}:/root
sudo scp config  ${c1}:/root

echo ready to run FIO from $c1 as root
