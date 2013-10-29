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
    if (LoadAndRegisterDbd())
        return Py_Main(argc, argv);
    else
        return 3;
}
