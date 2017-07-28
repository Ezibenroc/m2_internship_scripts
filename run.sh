# Script to run one of the “scalability tests” on a Nova node in G5K and then transfer the result.
# It assumes the public key of this node has been added in my authorized keys in Lyon.
# It has to be executed from the target node (e.g. nova-10).
# Example usage, to run a test for N=5000 and nbproc=16: bash run.sh 5000 16
size=$1
./run_measures.py --csv_file result.csv --nb_runs 1 --size "10000,${size}" --P_Q "77,78" --topo "../hpl-2.2/bin/SMPI/stampede.xml" --hugepage /root/huge
scp result.csv tocornebize@lyon:/home/tocornebize/result_${size}.csv
