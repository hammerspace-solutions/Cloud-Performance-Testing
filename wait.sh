source config 
echo waiting for all files to be deleted on ShareID $share 

ssh  serviceadmin@${anvil_ips}  "while [ \`pdfs-cli.py share-count-keys --column_family PDK_ORPHAN_INODE $share | grep -c \"PDK_ORPHAN_INODE: 0\"\` -eq 0 ]; do sleep 2; done; while [ \`pdfs-cli.py share-count-keys --column_family PDK_DELINST $share | grep -c \"PDK_DELINST: 0\"\` -eq 0 ]; do sleep 2;done;"  

echo wait done 
