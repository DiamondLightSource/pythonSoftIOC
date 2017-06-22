/* Soft IOC initialisation.
 *
 * This is really pretty well as simple as possible: all real work is
 * delegated to the invoked Python script. */

/* pyconfig.h (included from Python.h) redefines _POSIX_C_SOURCE and
 * _XOPEN_SOURCE, and in ways which conflict with the definitions provided by
 * EPICS.  To avoid messages, we let Python.h have its way here.
 *    Note also that Python recommends that Python.h be included first. */
#undef _POSIX_C_SOURCE
#undef _XOPEN_SOURCE
#include <Python.h>

#include <stdbool.h>

#include <stdio.h>
#include <unistd.h>
#include <stdlib.h>
#include <libgen.h>
#include <locale.h>

#include "dbAccess.h"
#include "iocInit.h"


/* The global IOC registration function is automatically constructed by the
 * EPICS IOC build process, and this call completes the registration
 * process.
 *     Note that although this is declared to return a value, in fact it
 * unconditionally returns 0, so it might as well be a void! */
extern int softIoc_registerRecordDeviceDriver(struct dbBase *pdbbase);



/* Loads the global IOC dbd definitions and registers them. */

static bool LoadAndRegisterDbd(void)
{
    const char *here = getenv("HERE");
    if (here == NULL)
    {
        fprintf(stderr, "Environment variable HERE must be defined\n");
        return false;
    }
    char softIoc_dbd[PATH_MAX];
    bool Ok = snprintf(
        softIoc_dbd, PATH_MAX, "%s/dbd/softIoc.dbd", here) < PATH_MAX;
    if (!Ok)
    {
        fprintf(stderr, "Path to dbd too long.\n");
        return false;
    }

    int status = dbLoadDatabase(softIoc_dbd, NULL, NULL);
    if (status != 0)
        fprintf(stderr,
            "Error (%d) loading dbd file \"%s\"\n", status, softIoc_dbd);
    if (status == 0)
        softIoc_registerRecordDeviceDriver(pdbbase);
    return status == 0;
}


int main(int argc, char *argv[])
{
#if PY_MAJOR_VERSION == 2
    char **python_argv = argv;

#else
    /* Alas, for Python3 we need convert argv from char** to wchar_t**. */
    wchar_t **python_argv = PyMem_Malloc(sizeof(wchar_t *) * (argc + 1));
    python_argv[argc] = NULL;

#if PY_MINOR_VERSION < 5
    /* This is a tricky space: we're supposed to use Py_DecodeLocale(), but
     * these versions of Python3 don't implement it yet.  Do the simplest
     * workaround we can.  This code is lifted from Python 3.4 Modules/python.c
     * and simplified as much as possible. */
    char *oldloc = strdup(setlocale(LC_ALL, NULL));
    setlocale(LC_ALL, "");
    for (int i = 0; i < argc; i ++)
        python_argv[i] = _Py_char2wchar(argv[i], NULL);
    setlocale(LC_ALL, oldloc);
    free(oldloc);

#else
    /* This seems to be the "correct" Python 3 way. */
    for (int i = 0; i < argc; i ++)
        python_argv[i] = Py_DecodeLocale(argv[i], NULL);
#endif
#endif

    if (LoadAndRegisterDbd())
        return Py_Main(argc, python_argv);
    else
        return 3;
}
