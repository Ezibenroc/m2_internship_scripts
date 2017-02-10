#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <mpi.h>
#include <assert.h>
#include <string.h>

// See for the (bad) default random number generator
#define RAND_SEED 842270

///////////////////////////////////////////////////////
//// program_abort() and print_usage() functions //////
///////////////////////////////////////////////////////

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
        fprintf(stderr,"              %s <matrix size>\n",exec_name);
        fprintf(stderr,"MPIRUN arguments:\n");
        fprintf(stderr,"\t<num processes>: number of MPI processes, it has to be a square\n");
        fprintf(stderr,"\t<XML platform file>: a Simgrid platform description file\n");
        fprintf(stderr,"\t<host file>: MPI host file with host names from the platform file\n");
        fprintf(stderr,"PROGRAM arguments:\n");
        fprintf(stderr,"\t<message size>: a positive integer\n");
        fprintf(stderr,"\n");
    }
    return;
}


///////////////////////////
////// Main function //////
///////////////////////////

int main(int argc, char *argv[])
{
    int i,j;

    // Parse command-line arguments (not using getopt because not thread-safe
    // and annoying anyway). The code below ignores extraneous command-line
    // arguments, which is lame, but we're not in the business of developing
    // a cool thread-safe command-line argument parser.

    MPI_Init(&argc, &argv);
    int msg_size = 0;

    // Bcast implementation name
    if (argc < 2) {
        program_abort(argv[0],"Missing <matrix size> argument\n");
    } else {
        msg_size = atoi(argv[1]);
    }

    // Determine rank and number of processes
    int num_procs;
    int rank;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &num_procs);
    
    float *buff = (float*)malloc(msg_size*sizeof(float));
    assert(buff);

    // Start the timer
    double start_time, total_time;
    MPI_Barrier(MPI_COMM_WORLD);
    if (rank == 0) {
        start_time = MPI_Wtime();
    }

    MPI_Bcast(buff, msg_size, MPI_FLOAT, 0, MPI_COMM_WORLD);

    MPI_Barrier(MPI_COMM_WORLD);
    total_time = MPI_Wtime() - start_time;
    // Print out bcast implementation name and wall-clock time, only if the bcast was successful
    if (0 == rank) {
        fprintf(stdout,"number_procs: %d | msg_size: %d |  time: %.8lf seconds\n",
                num_procs,
                msg_size,
                total_time);
    }
    free(buff);
    MPI_Finalize();

    return 0;
}
