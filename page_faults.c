#include <stdio.h>
#include <stdlib.h>
#include <sys/mman.h>
#include <unistd.h>
#include <assert.h>
#include <stdint.h>
#include <string.h>

#define filename "/tmp/test-XXXXXX"
static const size_t blocksize = 0x100000;

void* shared_malloc(size_t size) {
    void *mem;
    /* First reserve memory area */
    mem = mmap(NULL, size, PROT_READ | PROT_WRITE, MAP_ANONYMOUS | MAP_PRIVATE, -1, 0);
    if(mem == MAP_FAILED) {
        perror("mmap");
        return NULL;
    }
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
    if(shared)
        return shared_malloc(size);
    else
        return malloc(size);
}

void deallocate(void *ptr, size_t size, int shared) {
    if(shared)
        munmap(ptr, size);
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
    uint8_t *buff   = allocate(size, shared);
    if(buff == NULL) {
        printf("Error with allocation.\n");
        exit(1);
    }
    for(int i = 0; i < mem_access; i++)
        memset(buff, i, size);
    deallocate(buff, size, shared);
    return 0;
}
