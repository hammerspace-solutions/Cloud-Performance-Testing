#!/bin/bash

# Check for required arguments
if [ $# -ne 2 ] || [ -z "$1" ] || ([ "$2" != "storage" ] && [ "$2" != "ecgroup" ]); then
    echo "Error: Incorrect or missing arguments."
    echo "Usage: $0 <test_name> <type>"
    echo "The first argument must be a non-empty string (test_name)."
    echo "The second argument must be either 'storage' or 'ecgroup'."
    exit 1
fi

f=config
lss_num=`ansible-inventory -i ../inventory.ini --list | jq  .storage_servers.hosts | jq  length`
client_num=`ansible-inventory -i ../inventory.ini --list | jq  .clients.hosts | jq  length`

client_ips=`ansible-inventory  -i ../inventory.ini --list | jq -c .clients.hosts | sed 's/[{|}]//g' | tr ',' '
' | sed 's/"//g' |  sed 's/\[//g' | sed 's/\]//g'` 
lss_ips=`ansible-inventory   -i ../inventory.ini --list | jq -c  .storage_servers.hosts | sed 's/[{|}]//g' | tr ',' '
' | sed 's/"//g' |  sed 's/\[//g' | sed 's/\]//g'`

anvil_ips=`ansible-inventory  -i ../inventory.ini --list | jq -c .hammerspace.hosts | sed 's/[{|}]//g' | tr ',' '
' | sed 's/"//g' |  sed 's/\[//g' | sed 's/\]//g'`
anvil_num=`ansible-inventory -i ../inventory.ini --list | jq  .hammerspace.hosts | jq  length`

share=`cat ../inventory.ini | grep "${2}"_share_name | cut -d' ' -f 3`

#echo $lss_num  $client_num 

#echo $client_num Client IPs:  $client_ips

# for i  in $client_ips; do 
#	echo $i 
# done 

#echo $lss_num LSS IPs: $lss_ips

#echo $anvil_num Anvil IPs: $anvil_ips


rm $f 

echo client_num=$client_num>>$f 
echo client_ips=\"$client_ips\">>$f 

echo lss_num=$lss_num>>$f 
echo lss_ips=\"$lss_ips\">>$f 

echo anvil_num=$anvil_num>>$f 
echo anvil_ips=\"$anvil_ips\">>$f 

echo share=$share>>$f 
echo name="$1">>$f 

cat $f
