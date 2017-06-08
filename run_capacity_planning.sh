# Script to run the “capacity planning tests” on a Nova node in G5K.
# It has to be executed from the target node (e.g. nova-10).
# Example usage, to run a test for N=5000 and nbproc=16: bash run_capacity_planning.sh 5000 16
size=$1
nb_proc=$2
for i in topologies/* ; do
    csvfile=$(basename $i .xml).csv
    echo $csvfile
    ./run_measures.py --global_csv ${csvfile} --nb_runs 1 --size ${size} --nb_proc ${nb_proc} --topo $i --experiment HPL --running_power 5004882812.500 --hugepage /root/huge
done
