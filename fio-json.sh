

#mlr --icsv  --ojson cat fio_output_2025-08-13_21-34-18.csv > fio_output_2025-08-13_21-34-18.json

for d in `ls fio_results/*/*.csv`; do 
	jf=`echo $d| cut -d'.' -f 1`.json
	echo creating  $jf 
	mlr --icsv  --ojson cat $d > ${jf}
done
