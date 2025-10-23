#!/bin/bash 
source config 
c1=`head -n1  clients`

IOR=/mnt/hs_test/io500/bin/ior
MPI=mpirun  
STONE=120

./drop.sh 

LOGD=logs-IOR-Bandwidth-${name}-${STONE}
LOGJD=${LOGD}-json
mkdir -p $LOGD
mkdir -p $LOGJD


C=$client_num
for s in  40964000  ; do 
for N in 1 32 64 128 ; do #total threads 


	let "i=$N/$C"
	let "B=${s}/$N"
	
	LOGG=${LOGD}/scale-odirect-${C}-servers-${N}-threads-${s}m
        LOGJG=${LOGJD}/scale-odirect-${C}-servers-${N}-threads-${s}m
        LOG=${LOGG}-write
        LOGJ=${LOGJG}-write.json
	
	echo starting $s $i ppn with $B filesize on $C clients  $N total threads $LOG
		
  	${MPI} -n ${N} --hostfile hosts/${C} --allow-run-as-root --oversubscribe --mca btl_tcp_if_include ens5 ${IOR} -o /mnt/hs_test/file-ior -w  -F -C  -a Posix -O useO_DIRECT=1,keepFile=1 -e -t 1m -b ${B}m   --dataPacketType=timestamp -D ${STONE}  -O stoneWallingWearOut=1  -O stoneWallingStatusFile=/mnt/hs_test/ior.stonewall -O summaryFormat=JSON -O summaryFile=${LOGJ}  | tee $LOG 


	./drop.sh 
sleep 5 


        LOG=${LOGG}-read
        LOGJ=${LOGJG}-read.json
	
 
  	${MPI} -n ${N}  --hostfile hosts/${C} --allow-run-as-root --oversubscribe --mca btl_tcp_if_include ens5 ${IOR} -o /mnt/hs_test/file-ior -r  -F -C  -a Posix -O useO_DIRECT=1,keepFile=1 -e -t 1m -b ${B}m   -O stoneWallingStatusFile=/mnt/hs_test/ior.stonewall -O summaryFormat=JSON -O summaryFile=${LOGJ} | tee $LOG

	./drop.sh


	rm -rf /mnt/hs_test/file-ior*

	echo waiting for data to to be really deleted.  

	#time sh  ./wait.sh

	echo you can find the read logs at $LOG

done 
done  

echo you can find json logs at $LOGD

