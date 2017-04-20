#include <stdio.h>
#include <stdlib.h>
#include <sys/mman.h>
#include <unistd.h>
#include <assert.h>
#include <stdint.h>
#include <string.h>

#define blocksize 0x100000
#define filename "/tmp/test-XXXXXX"

void* shared_malloc(size_t size) {
    void *mem;
    /* First reserve memory area */
    mem = mmap(NULL, size, PROT_READ | PROT_WRITE, MAP_ANONYMOUS | MAP_PRIVATE, -1, 0);
    assert(mem != MAP_FAILED);
    int bogusfile;
    /* Create a fd to a new file on disk, make it blocksize big, and unlink it.
     * It still exists in memory but not in the file system (thus it cannot be leaked). */
    char name[30];
    strcpy(name, filename);
    bogusfile = mkstemp(name);
    unlink(name);
    char* dumb = (char*)calloc(1, blocksize);
    ssize_t err = write(bogusfile, dumb, blocksize);
    assert(err > 0);
    free(dumb);
    unsigned int i;
    /* Map the bogus file in place of the anonymous memory */
    for (i = 0; i < size / blocksize; i++) {
        void* pos = (void*)((unsigned long)mem + i * blocksize);
        void* res = mmap(pos, blocksize, PROT_READ | PROT_WRITE, MAP_FIXED | MAP_SHARED | MAP_POPULATE,
                         bogusfile, 0);
        assert(res == pos);
    }
    if (size % blocksize) {
        void* pos = (void*)((unsigned long)mem + i * blocksize);
        void* res = mmap(pos, size % blocksize, PROT_READ | PROT_WRITE,
                         MAP_FIXED | MAP_SHARED | MAP_POPULATE, bogusfile, 0);
        assert(res == pos);
    }
    return mem;
}

void *allocate(size_t size, int shared) {
    if(shared == 0)
        return malloc(size);
    else if(shared == 1)
        return shared_malloc(size);
    else if(shared == 2)
        return mmap(NULL, size, PROT_READ | PROT_WRITE, MAP_ANONYMOUS | MAP_PRIVATE, -1, 0);
    else
        assert(0);
}

void deallocate(void *ptr, size_t size, int shared) {
    if(shared == 0)
        free(ptr);
    else if(shared == 1 || shared ==2)
        munmap(ptr, size);
    else
        assert(0);
}

int main(int argc, char *argv[]) {
    if(argc != 4) {
        printf("Syntax: %s <shared_allocation> <allocation_size> <mem_access>", argv[0]);
        exit(1);
    }
    int shared      = atoi(argv[1]);
    size_t size     = atol(argv[2]);
    int mem_access  = atoi(argv[3]);
    uint8_t *buff   = allocate(size, shared);
    if(buff == NULL) {
        printf("Error with allocation.");
        exit(1);
    }
    if(mem_access)
        memset(buff, 0, size);
    deallocate(buff, size, shared);
    return 0;
}
