# Setup script for G5K nodes.
# It installs Simgrid, copies HPL and the scripts, installs the dependencies and sets up the system.
# It has to be executed from the frontend (e.g. lyon).
# It assumes that an archive 'simgrid.zip' exists in the current directory, containing the Simgrid repository.
# It assumes that an archive 'exp.zip' exists in the current directory, containing hpl and scripts repositories.
# Example usage, to setup the four nodes: bash deploy.sh nova-10 nova-11 nova-12 nova-13

function run_command {
    if [ $# -ne 2 ]; then
        echo "Wrong args: $*"
    fi
    hostname=$1
    command=$2
    logfile="deploy_${hostname}.log"
    echo "### ${command}" >> ${logfile}
	ssh root@${hostname} "${command}" &>> ${logfile}
    if [ $? -ne 0 ]; then
        echo "Error on host ${hostname} with command ${command}"
        exit 1
    fi
}

for i in $*; do (
    rm -f deploy_*.log
	echo "Start copying on host $i"
    run_command $i 'rm -rf /root/{exp,simgrid}.zip /root/simgrid /root/hpl-2.2 /root/scripts'
	run_command $i 'cp /home/tocornebize/*.zip /root'
	run_command $i 'for j in *.zip; do unzip $j; done'
	echo "Stop copying on host $i"
	echo "Start compiling on host $i"
	run_command $i 'yes | apt install smemstat'
	run_command $i 'wget https://bootstrap.pypa.io/get-pip.py && python3 get-pip.py && yes | apt install python3-dev && pip3 install lxml psutil pandas statsmodels'
	run_command $i 'cd simgrid && mkdir build && cd build && cmake -Denable_documentation=OFF .. && make -j 32 && make install'
	run_command $i 'cd hpl* && sed -ri "s|TOPdir\s*=.+|TOPdir="`pwd`"|g" Make.SMPI && make startup arch=SMPI && make SMPI_OPTS="-DSMPI_OPTIMIZATION -DSMPI_DGEMM_COEFFICIENT=1.029e-11 -DSMPI_DGEMM_PHI_COEFFICIENT=1.981e-12 -DSMPI_DTRSM_COEFFICIENT=9.882e-12 -DSMPI_DTRSM_PHI_COEFFICIENT=1.954e-12" arch=SMPI'
	run_command $i 'sysctl -w vm.overcommit_memory=1 && sysctl -w vm.max_map_count=40000000'
	run_command $i 'mkdir -p /root/huge && mount none /root/huge -t hugetlbfs -o rw,mode=0777 && echo 1 >> /proc/sys/vm/nr_hugepages'
	echo "Stop compiling on host $i"
)&
done
wait
echo "Deployment terminated on all nodes."
