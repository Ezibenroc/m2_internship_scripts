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
        fprintf(stderr,"\t<matrix size>: an integer that should be a multiple of the square root of the number of processes\n");
        fprintf(stderr,"\n");
    }
    return;
}

inline double my_abs(double x) {
    return x > 0 ? x : -x ;
}

void local_to_global(int local_i, int local_j, int *global_i, int *global_j, int proc_i, int proc_j, int local_matrix_size) {
    *global_i = proc_i*local_matrix_size + local_i;
    *global_j = proc_j*local_matrix_size + local_j;
}

void global_to_local(int *local_i, int *local_j, int global_i, int global_j, int local_matrix_size) {
    *local_i = global_i%local_matrix_size;
    *local_j = global_j%local_matrix_size;
}

int my_sqrt(int n) {
    int x = n;
    int y = (x+1)/2;
    while(y < x) {
        x = y;
        y = (x + n/x)/2;
    }
    return x;
}

float *allocate_matrix(int size) {
    float *matrix = (float*) malloc(sizeof(float*)*size*size);
    assert(matrix);
    return matrix;
}

void free_matrix(float *matrix, int size) {
    free(matrix);
}

inline void matrix_copy(float *dest, const float *src, int size) {
    memcpy(dest, src, size*size*sizeof(float));
}

inline void matrix_set(float *matrix, int size, int i, int j, float value) {
    matrix[i*size+j] = value;
}

inline float matrix_get(float *matrix, int size, int i, int j) {
    return matrix[i*size+j];
}

// A[i][j] = i
float *init_matrix_A(int size, int proc_i, int proc_j) {
    int global_i, global_j;
    float *matrix = allocate_matrix(size);
    for(int i = 0 ; i < size ; i++) {
        for(int j = 0 ; j < size ; j++) {
            local_to_global(i, j, &global_i, &global_j, proc_i, proc_j, size);
            matrix_set(matrix, size, i, j, global_i);
        }
    }
    return matrix;
}

// B[i][j] = i+j
float *init_matrix_B(int size, int proc_i, int proc_j) {
    int global_i, global_j;
    float *matrix = allocate_matrix(size);
    for(int i = 0 ; i < size ; i++) {
        for(int j = 0 ; j < size ; j++) {
            local_to_global(i, j, &global_i, &global_j, proc_i, proc_j, size);
            matrix_set(matrix, size, i, j, global_i+global_j);
        }
    }
    return matrix;
}

float *init_matrix_C(int size) {
    float *matrix = allocate_matrix(size);
    memset(matrix, 0, size*size*sizeof(float));
    return matrix;
}

void print_matrix(float *matrix, int size) {
    for(int i = 0 ; i < size ; i++) {
        for(int j = 0 ; j < size-1 ; j++) {
            printf("%6.3f ", matrix_get(matrix, size, i, j));
        }
        printf("%6.3f\n", matrix_get(matrix, size, i, size-1));
    }
}

bool matrix_equal(float *matrix_A, float *matrix_B, int size, float epsilon) {
    for(int i = 0 ; i < size ; i++) {
        for(int j = 0 ; j < size ; j++) {
            float a = matrix_get(matrix_A, size, i, j);
            float b = matrix_get(matrix_B, size, i, j);
            if(my_abs(a-b) > epsilon) {
                return false;
            }
        }
    }
    return true;
}

void sequential_matrix_product(float *A, float *B, float *C, int size) {
    for(int i = 0 ; i < size ; i++) {
        for(int j = 0 ; j < size ; j++) {
            for(int k = 0 ; k < size ; k++) {
                float a = matrix_get(A, size, i, k);
                float b = matrix_get(B, size, k, j);
                float c = matrix_get(C, size, i, j);
                matrix_set(C, size, i, j, c + a*b);
            }
        }
    }
}

void matrix_product(float *A, float *B, float *C, int size, int global_size, int proc_i, int proc_j, int sqrt_num_procs) {
    double communication_time = 0, computation_time = 0, tmp_time;
    float *A_buff = allocate_matrix(size);
    float *B_buff = allocate_matrix(size);
    float *A_send, *B_send;
    MPI_Comm line_comm;
    MPI_Comm column_comm;
    MPI_Comm_split(MPI_COMM_WORLD, proc_i, proc_j, &line_comm);
    MPI_Comm_split(MPI_COMM_WORLD, proc_j, proc_i, &column_comm);
    for(int k = 0 ; k < sqrt_num_procs ; k++) {
        tmp_time = MPI_Wtime();
        if(k == proc_j) { // we send our block of A
            A_send = A;
        }
        else { // we receive a block of A
            A_send = A_buff;
        }
        if(k == proc_i) { // we send our block of B
            B_send = B;
        }
        else { // we receive a block of B
            B_send = B_buff;
        }
        MPI_Bcast(A_send, size*size, MPI_FLOAT, k, line_comm);
        MPI_Bcast(B_send, size*size, MPI_FLOAT, k, column_comm);
        communication_time += MPI_Wtime() - tmp_time;
        tmp_time = MPI_Wtime();
        sequential_matrix_product(A_send, B_send, C, size);
        computation_time += MPI_Wtime() - tmp_time;
    }
    printf("rank: %4d | communication_time: %.8lf | computation_time: %.8lf\n", proc_i*sqrt_num_procs+proc_j, communication_time, computation_time);
    free_matrix(A_buff, size);
    free_matrix(B_buff, size);
    MPI_Comm_free(&line_comm);
    MPI_Comm_free(&column_comm);
}

double matrix_sum(float *matrix, int size) {
    double sum = 0;
    double result = 0;
    for(int i = 0 ; i < size ; i++) {
        for(int j = 0 ; j < size ; j++) {
            sum += matrix_get(matrix, size, i, j);
        }
    }
    MPI_Reduce(&sum, &result, 1, MPI_DOUBLE, MPI_SUM, 0, MPI_COMM_WORLD);
    return result;
}

// Gather the matrix on process 0
// We do not use MPI_gather, since it is not very convenient with the way se store matrices here
float *gather_matrix(float *matrix, int size, int rank, int sqrt_num_procs) {
    if(rank == 0) {
        int global_size = size*sqrt_num_procs;
        float *global_matrix = allocate_matrix(global_size);
        float *buff = allocate_matrix(size);
        // Copy of our own matrix
        for(int i = 0 ; i < size ; i++) {
            for(int j = 0 ; j < size ; j++) {
                float elt = matrix_get(matrix, size, i, j);
                matrix_set(global_matrix, global_size, i, j, elt);
            }
        }
        // Reception and copy of the matrices from other processes
        for(int i_proc = 0 ; i_proc < sqrt_num_procs ; i_proc ++) {
            for(int j_proc = 0 ; j_proc < sqrt_num_procs ; j_proc ++) {
                if(i_proc == 0 && j_proc == 0) continue; // we are process (0, 0)
                MPI_Recv(buff, size*size, MPI_FLOAT, i_proc*sqrt_num_procs+j_proc, 1, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
                for(int i = 0 ; i < size ; i++) {
                    for(int j = 0 ; j < size ; j++) {
                        float elt = matrix_get(buff, size, i, j);
                        matrix_set(global_matrix, global_size, i_proc*size+i, j_proc*size+j, elt);
                    }
                }
            }
        }
        return global_matrix;
    }
    else {
        MPI_Send(matrix, size*size, MPI_FLOAT, 0, 1, MPI_COMM_WORLD);
        return NULL;
    }
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
    int matrix_size = 0;

    // Bcast implementation name
    if (argc < 2) {
        program_abort(argv[0],"Missing <matrix size> argument\n");
    } else {
        matrix_size = atoi(argv[1]);
    }

    // Determine rank and number of processes
    int num_procs;
    int rank;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &num_procs);
    int sqrt_num_procs = my_sqrt(num_procs);
    if(sqrt_num_procs*sqrt_num_procs != num_procs) {
        program_abort(argv[0], "Number of processes is not a square.\n");
    }
    if(matrix_size%sqrt_num_procs != 0) {
        program_abort(argv[0], "Matrix size is not a multiple of the square root of the number of processes.\n");
    }
    int local_size = matrix_size/sqrt_num_procs;
    int proc_i = rank/sqrt_num_procs;
    int proc_j = rank%sqrt_num_procs;
    float *matrix_A = init_matrix_A(local_size, proc_i, proc_j);
    float *matrix_B = init_matrix_B(local_size, proc_i, proc_j);
    float *matrix_C = init_matrix_C(local_size);

    // Start the timer
    double start_time, total_time;
    MPI_Barrier(MPI_COMM_WORLD);
    if (rank == 0) {
        start_time = MPI_Wtime();
    }

    matrix_product(matrix_A, matrix_B, matrix_C, local_size, matrix_size, proc_i, proc_j, sqrt_num_procs);

    MPI_Barrier(MPI_COMM_WORLD);
    total_time = MPI_Wtime() - start_time;

/*
///// Verification
    float *global_matrix_A = gather_matrix(matrix_A, local_size, rank, sqrt_num_procs);
    float *global_matrix_B = gather_matrix(matrix_B, local_size, rank, sqrt_num_procs);
    float *global_matrix_C = gather_matrix(matrix_C, local_size, rank, sqrt_num_procs);
    if(rank == 0) {
        float *expected_global_matrix_C = init_matrix_C(matrix_size);
        sequential_matrix_product(global_matrix_A, global_matrix_B, expected_global_matrix_C, matrix_size);
        if(!matrix_equal(global_matrix_C, expected_global_matrix_C, matrix_size, 1e-6)) {
            printf("ERROR, sequential product and parallel product are not equal.\n");
            exit(1);
        }
        free_matrix(global_matrix_A, matrix_size);
        free_matrix(global_matrix_B, matrix_size);
        free_matrix(global_matrix_C, matrix_size);
        free_matrix(expected_global_matrix_C, matrix_size);
    }

////// Other verification, much less precise since the sum is huge (545469235200 for a matrix of size 256).
////// But it is independent of the sequential product implementation, which is nice.
    double sum = matrix_sum(matrix_C, local_size);
    if(rank == 0) { // check that the sum is N^3 * (N-1)^2 / 2
        double N = matrix_size;
        double expected = N*N*N*(N-1)*(N-1)/2;
        if(my_abs((sum-expected)/expected) > 1e-6) {
            printf("Error with the matrix sum.\n");
            printf("Expected: %f\n", expected);
            printf("Observed: %f\n", sum);
            exit(1);
        }
    }
*/

    // Print out bcast implementation name and wall-clock time, only if the bcast was successful
    if (0 == rank) {
        fprintf(stdout,"number_procs: %d | matrix_size: %d |  time: %.8lf seconds\n",
                num_procs,
                matrix_size,
                total_time);
    }

    free_matrix(matrix_A, local_size);
    free_matrix(matrix_B, local_size);
    MPI_Finalize();

    return 0;
}
