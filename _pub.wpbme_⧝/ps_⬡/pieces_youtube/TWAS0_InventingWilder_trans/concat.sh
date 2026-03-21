awk 'FNR==1{print "=== " FILENAME " ==="} {print} ENDFILE{print ""}' *.txt > output.txt
