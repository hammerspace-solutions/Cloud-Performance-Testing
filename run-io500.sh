#!/bin/bash

MPI=mpirun
IO500=/mnt/hs_test/io500/io500
source config 
LOGB=logs-io500

mkdir -p $LOGB 


C=$client_num
for N in 64; do 
	LOG=${LOGB}/${C}-clients-${N}_threads-${name}-300s
	./drop.sh  
	echo starting $i ppn with on $C clients  $N total threads $LOG
	${MPI} -n ${N} --hostfile hosts/${C} --allow-run-as-root --oversubscribe $IO500 /mnt/hs_test/io500/config-hammer-ec.ini  | tee -a $LOG 
done 

