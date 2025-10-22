source config 
c1=`head -n1  clients`

sudo scp cloud_data_path_tests.sh ${c1}:/root

sudo ssh ${c1} /root/cloud_data_path_tests.sh



