#! /usr/bin/env sh

./run_measures.py --csv_file /tmp/results.csv --nb_runs 1 --size 30000,40000 --nb_proc 12,16 --topo "2;4,4;1,1:2;1,1" --running_power 6217956542.969 &&\
./compare_csv.py test_results.csv /tmp/results.csv nb_proc topology size memory_size && echo "OK"
