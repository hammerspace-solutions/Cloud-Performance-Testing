#set -x 

benchj=""
for f in `ls logs-io500`; do 
	clients=`echo $f | cut -d'-' -f 1`
        threads=`echo $f | cut -d'-' -f 3 | cut -d'_' -f 1`	
	seconds=`echo $f | cut -d'-' -f 5 | cut -d's' -f 1`
	version=`cat logs-io500/$f | grep "IO500 version"| awk '{print $3}'`

	cat logs-io500/$f | grep RESULT>temp 
	while read line; do
		#echo $line 
		bname=$(echo $line | awk '{print $2}')
		bscore=$(echo $line | awk '{print $3}')
		uscore=$(echo $line | awk '{print $4}')
		sscore=$(echo $line | awk '{print $7}')
	
		bjson=$(jq -n --arg Name "$bname" --arg Score "$bscore" --arg Units "$uscore"  --arg Seconds  "$sscore" '$ARGS.named') 
		slinejson=$(jq -n --argjson Benchmark-$bname "$bjson" '$ARGS.named')
		benchj=$(echo "$benchj $slinejson" | jq -s 'add')
	
	done < temp
	rm -rf temp 

#	echo $benchj

	scoreline=`cat logs-io500/$f| grep SCORE`
	scoreb=$(echo $scoreline | awk '{print $4}').
	scorei=$(echo $scoreline | awk '{print $8}').
	scoret=$(echo $scoreline | awk '{print $12}').
	
#	echo $sjson


fjson=$(jq -n --arg IO500_Version "$version" \
       	--arg Client_Count "$clients" \
       	--arg Total_Threads "$threads" \
	--arg Stonewall_Seconds "$seconds" \
	--argjson Benchmarks "$benchj" \
	--arg IO500_Score "$scoret" \
	--arg Score_Bandwith "$scoreb" \
	--arg Score_IOPs "$scorei" \
	'$ARGS.named')

jq <<< $fjson > logs-io500/$f.json

done 

exit


