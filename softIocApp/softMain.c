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




static void Usage()
{
    printf("Usage: softIoc [<ioc-script> [<script-args>]]\n");
}

static bool ProcessOptions(int *pargc, char ***pargv)
{
    int Ok = true;
    while (Ok)
    {
        switch (getopt(*pargc, *pargv, "+h"))
        {
            case 'h':
                Usage();
                return false;
            case -1:
                // End of flags
                *pargc -= optind;
                *pargv += optind;
                return true;
            default:
                /* Invalid flag or too few arguments. */
                fprintf(stderr, "Try `softIoc -h` for usage\n");
                return false;
        }
    }
    return false;
}


/* Loads the global IOC dbd definitions and registers them. */

static bool LoadAndRegisterDbd()
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
    char * argv0 = argv[0];
    bool Ok =
        /* The first thing we do is parse and consume the command line options
         * and check that we have a script to execute.  On return argc counts
         * the arguments and argv[0] is the first argument. */
        ProcessOptions(&argc, &argv)  &&
        /* Perform the basic IOC initialisation. */
        LoadAndRegisterDbd();

    if (Ok)
    {
        /* Need to fix up the arguments passed to Py_Main to compensate for
         * the adjustment made by ProcessOptions. */
        argc += 1;
        argv -= 1;
        argv[0] = argv0;
        return Py_Main(argc, argv);
    }
    else
        return 3;
}
