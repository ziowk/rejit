#include <string.h>
#include <stdlib.h>
#include <Windows.h>

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
	void *ptr = VirtualAlloc(NULL, source_size, MEM_COMMIT, PAGE_READWRITE);
	if (ptr == (void*)-1) {
		return NULL;
	}

	// copy the code
	memcpy(ptr, source, source_size);

	// set protection to executable
	if (VirtualProtect(ptr, source_size, PAGE_EXECUTE_READ, &oldProtect) == 0) {
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
freeFunction(FunObj* funobj) {
    JITFunc jitfunc = funobj->func;
    size_t source_size = funobj->length; // ignore, needed only on gnu/linux
	if (VirtualFree(jitfunc, 0, MEM_RELEASE) == 0) {
		return -1;
	}
	return 0;
}

