#!/bin/bash

source config

c1=`head -n1  clients` 

cp /mnt/hs_test/results-io500 . 

bash ./fio-json.sh
bash ./io500-json.sh 

mkdir results
cp -rf results-io500 results/ 
cp -rf logs* results/
cp -rf fio_results results/
cp -rf config results/
cp -rf ~/inventory.ini results/
mv ./aws-info results/

mv results results-$name

tar -cvf results-${name}.tar results-$name


echo results-${name}.tar contains all the found results.


