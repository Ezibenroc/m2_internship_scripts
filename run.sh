# Script to run one of the “scalability tests” on a Nova node in G5K and then transfer the result.
# It assumes the public key of this node has been added in my authorized keys in Lyon.
# It has to be executed from the target node (e.g. nova-10).
# Example usage, to run a test for N=5000 and nbproc=16: bash run.sh 5000 16
size=$1
nb_proc=$2
./run_measures.py --global_csv result.csv --nb_runs 1 --size ${size} --nb_proc ${nb_proc} --topo "2;16,32;1,16;1,1" --experiment HPL --running_power 5004882812.500 --nb_cpu 8 --hugepage /root/huge
scp result.csv tocornebize@lyon:/home/tocornebize/result_${size}_${nb_proc}.csv
