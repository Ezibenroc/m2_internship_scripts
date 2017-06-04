#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <mpi.h>
#include <assert.h>
#include <string.h>


static void program_abort(char *exec_name, char *message);
static void print_usage();

// Abort, printing the usage information only if the
// first argument is non-NULL (and hopefully set to argv[0]), and
// printing the second argument regardless.
static void program_abort(char *exec_name, char *message) {
    int my_rank;
    MPI_Comm_rank(MPI_COMM_WORLD,&my_rank);
    if (my_rank == 0) {
        if (message) {
            fprintf(stderr,"%s",message);
        }
        if (exec_name) {
            print_usage(exec_name);
        }
    }
    MPI_Abort(MPI_COMM_WORLD, 1);
    exit(1);
}

// Print the usage information
static void print_usage(char *exec_name) {
    int my_rank;
    MPI_Comm_rank(MPI_COMM_WORLD,&my_rank);

    if (my_rank == 0) {
        fprintf(stderr,"Usage: smpirun --cfg=smpi/bcast:mpich -np <num processes>\n");
        fprintf(stderr,"              -platform <XML platform file> -hostfile <host file>\n");
        fprintf(stderr,"              %s <size> <nb_iter>\n",exec_name);
        fprintf(stderr,"MPIRUN arguments:\n");
        fprintf(stderr,"\t<num processes>: number of MPI processes\n");
        fprintf(stderr,"\t<XML platform file>: a Simgrid platform description file\n");
        fprintf(stderr,"\t<host file>: MPI host file with host names from the platform file\n");
        fprintf(stderr,"PROGRAM arguments:\n");
        fprintf(stderr,"\t<size>: an integer, the size of the messages sent by each process\n");
        fprintf(stderr,"\t<nb_iter>: an integer, the number of messages sent by each process\n");
        fprintf(stderr,"\n");
    }
    return;
}


void test_network(int size, int nb_iter, int rank, int num_procs, int *in_buff, int *out_buff) {
    int next = (rank+1)%num_procs;
    int prev = (rank+num_procs-1)%num_procs;
    MPI_Request request;
    for(int i = 0; i < nb_iter; i++) {
        MPI_Isend(out_buff, size, MPI_INT, next, 1, MPI_COMM_WORLD, &request);
        MPI_Recv(in_buff, size, MPI_INT, prev, 1, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
        MPI_Wait(&request, MPI_STATUS_IGNORE);
    }
}


///////////////////////////
////// Main function //////
///////////////////////////

int main(int argc, char *argv[])
{
    int i,j;

    MPI_Init(&argc, &argv);
    int size = 0;
    int nb_iter = 0;

    if (argc != 3) {
        program_abort(argv[0],"Missing argument\n");
    } else {
        size = atoi(argv[1]);
        nb_iter = atoi(argv[2]);
    }


    // Determine rank and number of processes
    int num_procs;
    int rank;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &num_procs);

    int *in_buff  = (int*)SMPI_SHARED_MALLOC(sizeof(int)*size);
    int *out_buff = (int*)SMPI_SHARED_MALLOC(sizeof(int)*size);
    assert(in_buff);
    assert(out_buff);
    memset(out_buff, rank, size);

    // Start the timer
    double start_time, total_time;
    MPI_Barrier(MPI_COMM_WORLD);
    if (rank == 0) {
        start_time = MPI_Wtime();
    }

    test_network(size, nb_iter, rank, num_procs, in_buff, out_buff);

    MPI_Barrier(MPI_COMM_WORLD);
    total_time = MPI_Wtime() - start_time;

    if (rank == 0) {
        printf("%.8lf\n", total_time);
    }

    SMPI_SHARED_FREE(in_buff);
    SMPI_SHARED_FREE(out_buff);
    MPI_Finalize();

    return 0;
}
