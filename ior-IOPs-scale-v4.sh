source config 
c1=`head -n1  clients`
IOR=/mnt/hs_test/io500/bin/ior
MPI=mpirun

./drop.sh 

STONE=120
LOGD=logs-IOR-IOPs-${name}-${STONE}
LOGJD=${LOGD}-json
mkdir -p $LOGD

mkdir -p $LOGJD

for C in $client_num ; do #number of clients 
for N in 1 4 8 16 32 64 128 256 ; do  #total number of threads 
for k in 4 ; do   #size of random kb io.   4k is standard. 


	LOGG=${LOGD}/scale-odirect-${C}-servers-${N}-threads-${k}k
	LOGJG=${LOGJD}/scale-odirect-${C}-servers-${N}-threads-${k}k
	let "i=$N/$C"
	let "B=20482/$N"
	LOG=${LOGG}-write
	LOGJ=${LOGJG}-write.json
	echo starting  $i ppn with on $C clients at ${k}k random size $N total threads $LOG
		
  	${MPI} -n ${N} --hostfile hosts/${C} --allow-run-as-root --oversubscribe  --mca btl_tcp_if_include ens5 ${IOR} -o /mnt/hs_test/file-ior -w  -F -z -C  -a Posix -O useO_DIRECT=1,keepFile=1 -e -t ${k}k -b ${B}m --dataPacketType=timestamp  -D ${STONE}  -O stoneWallingWearOut=1  -O stoneWallingStatusFile=/mnt/hs_test/ior.stonewall -O summaryFormat=JSON -O summaryFile=${LOGJ} | tee $LOG 

	./drop.sh 

sleep 10


	LOG=${LOGG}-read
	LOGJ=${LOGJG}-read.json
 
  	${MPI} -n ${N}  --hostfile hosts/${C} --allow-run-as-root --oversubscribe --mca btl_tcp_if_include ens5  ${IOR} -o /mnt/hs_test/file-ior -r  -F -z -C  -a Posix -O useO_DIRECT=1,keepFile=1 -e -t ${k}k  -O stoneWallingStatusFile=/mnt/hs_test/ior.stonewall -O summaryFormat=JSON -O summaryFile=${LOGJ}  | tee $LOG

	./drop.sh


   rm -rf /mnt/hs_test/file-ior*

#echo waiting for data to to be really deleted.  

#time bash  ./wait.sh

echo you can find the run log at $LOG

done 
done 
done  

echo you can find json logs at $LOGD
