echo Drop Cache on Clients and Servers 

sudo pdsh -w ^clients,^servers "echo 3 > /proc/sys/vm/drop_caches"
