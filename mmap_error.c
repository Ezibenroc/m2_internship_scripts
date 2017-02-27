#include <stdio.h>
#include <mpi.h>

#define N 65472

int main(int argc, char *argv[]) {

    MPI_Init(&argc, &argv);

    for(int i = 0; i < N; i++) {
        float *a = SMPI_SHARED_MALLOC(1);
    }

    MPI_Barrier(MPI_COMM_WORLD);
    printf("Success\n");
    MPI_Finalize();
    return 0;
}
