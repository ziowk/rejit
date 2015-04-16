#include <string.h>
#include <stdlib.h>
#include <sys/mman.h>

/*----- jit declarations -----*/

typedef int(*JITFunc)(const char* string, size_t length);

typedef struct {
    JITFunc func;
    size_t length;
} FunObj;

FunObj* createFunction(const void* source, size_t source_size);

int freeFunction(FunObj*);

/* ----- jit definitions -----*/

FunObj * 
createFunction(const void* source, size_t source_size) {
	int oldProtect;
    FunObj *funobj;

	// allocate executable and writeable memory
    void* ptr = mmap(0, source_size, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
	if (ptr == MAP_FAILED) {
		return NULL;
	}

	// copy the code
	memcpy(ptr, source, source_size);

	// set protection to executable
    if (mprotect(ptr, source_size, PROT_READ | PROT_EXEC) == -1) {
        return NULL;
    }

    // create FunObj object
    if ((funobj = (FunObj*)malloc(sizeof(FunObj))) == NULL) {
        return NULL;
    }
    funobj->func = ptr;
    funobj->length = source_size;
	return funobj;
}

int
freeFunction(FunObj *funobj) {
    JITFunc jitfunc = funobj->func;
    size_t source_size = funobj->length;
    if (munmap((void*)jitfunc, source_size) == -1) {
		return -1;
	}
    free(funobj);
	return 0;
}

