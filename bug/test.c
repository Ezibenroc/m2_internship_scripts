#include <stdio.h>
#include <stdlib.h>
#include <mpi.h>
#include <stdint.h>

uint64_t fib(int n) {
    if(n < 2)
        return 1;
    else
        return fib(n-1) + fib(n-2);
}

void compute(int rank, int size) {
    double tmp_time, computation_time;
    tmp_time = MPI_Wtime();
    uint64_t result = fib(size);
    computation_time = MPI_Wtime() - tmp_time;
    printf("rank: %4d | computation_time: %.8lf | result: %lu\n", rank, computation_time, result);
}


int main(int argc, char *argv[]) {
    MPI_Init(&argc, &argv);
    int size = 0;

    if (argc < 2) {
        fprintf(stderr, "Missing <size> argument\n"); 
        exit(1);
    } else {
        size = atoi(argv[1]);
    }

    int rank;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    compute(rank, size);

    MPI_Finalize();
    return 0;
}
