// Compilation:
// gcc -std=gnu11 -ggdb3 -O3 -o page_faults page_faults.c -Wall
// Verbose mode  : add flag -DVERBOSE
// Huge page mode: add flag -DHUGEPAGE

#include <stdio.h>
#include <stdlib.h>
#include <sys/mman.h>
#include <unistd.h>
#include <assert.h>
#include <stdint.h>
#include <string.h>
#include <sys/time.h>


#ifdef VERBOSE
#pragma message "VERBOSE: ON"
#define print(...) printf(__VA_ARGS__);
#else
#pragma message "VERBOSE: OFF"
#define print(...) {}
#endif


#ifdef HUGEPAGE
#pragma message "HUGEPAGE: ON"
#define filename "/home/huge/test-XXXXXX"
#else
#pragma message "HUGEPAGE: OFF"
#define filename "/tmp/test-XXXXXX"
#endif

static const size_t blocksize = 1<<21;

static int bogusfile=-1;
static void *allocated_ptr = NULL;
static size_t allocated_size = -1;

void* shared_malloc(size_t size) {
    void *mem;
    /* First reserve memory area */
    allocated_size = size+2*blocksize;
    allocated_ptr = mmap(NULL, allocated_size, PROT_READ | PROT_WRITE, MAP_ANONYMOUS | MAP_PRIVATE, -1, 0);
    print("allocation: %p - %p\n", allocated_ptr, allocated_ptr+size+2*blocksize);
    if(allocated_ptr == MAP_FAILED) {
        perror("mmap");
        return NULL;
    }
    mem = (void*)(((intptr_t)allocated_ptr+blocksize-1)&~(blocksize-1));
    print("returned  : %p - %p\n", mem, mem+size);
    /* Create a fd to a new file on disk, and unlink it.
     * It still exists in memory but not in the file system (thus it cannot be leaked). */
    if(bogusfile == -1) {
        char name[30];
        strcpy(name, filename);
        bogusfile = mkstemp(name);
#ifndef HUGEPAGE
        char* dumb = (char*)calloc(1, blocksize);
        ssize_t err = write(bogusfile, dumb, blocksize);
        assert(err > 0);
        free(dumb);
#endif
        unlink(name);
    }
    int flag;
#ifdef HUGEPAGE
    flag = MAP_FIXED | MAP_SHARED | MAP_POPULATE | MAP_HUGETLB;
#else
    flag = MAP_FIXED | MAP_SHARED | MAP_POPULATE;
#endif
    unsigned int i;
    /* Map the bogus file in place of the anonymous memory */
    for (i = 0; i < size / blocksize; i++) {
        void* pos = (void*)((unsigned long)mem + i * blocksize);
        void* res = mmap(pos, blocksize, PROT_READ | PROT_WRITE, flag,
                         bogusfile, 0);
        print("mmap      : %p - %p\n", pos, pos+blocksize);
        if(res == MAP_FAILED) {
            perror("mmap2");
            return NULL;
        }
        assert(res == pos);
        assert(res < allocated_ptr+size);
    }
    if (size % blocksize) {
        void* pos = (void*)((unsigned long)mem + i * blocksize);
        void* res = mmap(pos, (size % blocksize), PROT_READ | PROT_WRITE,
                         MAP_FIXED | MAP_SHARED | MAP_POPULATE, bogusfile, 0);
        assert(res == pos);
        print("mmap*     : %p - %p\n", pos, pos+blocksize+size%blocksize);
    }
    return mem;
}

void *allocate(size_t size, int shared) {
    if(shared)
        return shared_malloc(size);
    else
        return malloc(size);
}

void deallocate(void *ptr, size_t size, int shared) {
    if(shared) {
        if(munmap(allocated_ptr, allocated_size) < 0) {
            perror("munmap_final");
        }
        allocated_size = -1;
        allocated_ptr = NULL;
    }
    else
        free(ptr);
}

int main(int argc, char *argv[]) {
    if(argc != 4) {
        printf("Syntax: %s <shared_allocation> <allocation_size> <mem_access>", argv[0]);
        exit(1);
    }
    int shared      = atoi(argv[1]);
    size_t size     = atol(argv[2]);
    int mem_access  = atoi(argv[3]);
    struct timeval before = {};
    struct timeval after = {};
    gettimeofday(&before, NULL);\
    uint8_t *buff   = allocate(size, shared);
    if(buff == NULL) {
        printf("Error with allocation.\n");
        exit(1);
    }
    for(int i = 0; i < mem_access; i++)
        memset(buff, i, size);
    deallocate(buff, size, shared);
    gettimeofday(&after, NULL);
    double real_time = (after.tv_sec-before.tv_sec) + 1e-6*(after.tv_usec-before.tv_usec);\
    printf("%g\n", real_time);
    return 0;
}
