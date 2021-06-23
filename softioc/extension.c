
#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <string.h>

#define db_accessHFORdb_accessC     // Needed to get correct DBF_ values
#include <dbAccess.h>
#include <dbFldTypes.h>
#include <dbStaticLib.h>
#include <asTrapWrite.h>
#include <epicsVersion.h>
#include <dbChannel.h>
#include <asTrapWrite.h>
#include <asDbLib.h>

/* In Python3 this function has been renamed. */
#if PY_MAJOR_VERSION >= 3
#define PyInt_FromLong(value)   PyLong_FromLong(value)
#endif

/* Reference stealing version of PyDict_SetItemString */
static void set_dict_item_steal(
    PyObject *dict, const char *name, PyObject *py_value)
{
    PyDict_SetItemString(dict, name, py_value);
    Py_DECREF(py_value);
}

/* Helper for function below. */
#define ADD_ENUM(dict, name) \
    set_dict_item_steal(dict, #name, PyInt_FromLong(name))

/* Alas, EPICS has changed the numerical assignments of the DBF_ enums between
 * versions, so to avoid unpleasant surprises, we compute thes values here in C
 * and pass them back to the Python layer. */
static PyObject *get_DBF_values(PyObject *self, PyObject *args)
{
    PyObject *dict = PyDict_New();
    ADD_ENUM(dict, DBF_STRING);
    ADD_ENUM(dict, DBF_CHAR);
    ADD_ENUM(dict, DBF_UCHAR);
    ADD_ENUM(dict, DBF_SHORT);
    ADD_ENUM(dict, DBF_USHORT);
    ADD_ENUM(dict, DBF_LONG);
    ADD_ENUM(dict, DBF_ULONG);
    ADD_ENUM(dict, DBF_FLOAT);
    ADD_ENUM(dict, DBF_DOUBLE);
    ADD_ENUM(dict, DBF_ENUM);
    ADD_ENUM(dict, DBF_MENU);
    ADD_ENUM(dict, DBF_DEVICE);
    ADD_ENUM(dict, DBF_INLINK);
    ADD_ENUM(dict, DBF_OUTLINK);
    ADD_ENUM(dict, DBF_FWDLINK);
    ADD_ENUM(dict, DBF_NOACCESS);
    return dict;
}


/* Given an array of field names, this routine looks up each field name in
 * the EPICS database and returns the corresponding field offset. */
static PyObject *get_field_offsets(PyObject *self, PyObject *args)
{
    const char *record_type;
    if (!PyArg_ParseTuple(args, "s", &record_type))
        return NULL;

    DBENTRY dbentry;
    dbInitEntry(pdbbase, &dbentry);

    int status = dbFindRecordType(&dbentry, record_type);
    if (status != 0)
        printf("Unable to find record type \"%s\" (error %d)\n",
            record_type, status);
    else
        status = dbFirstField(&dbentry, 0);

    PyObject *dict = PyDict_New();
    while (status == 0)
    {
        const char * field_name = dbGetFieldName(&dbentry);
        PyObject *ost = Py_BuildValue("iii",
            dbentry.pflddes->offset,
            dbentry.pflddes->size,
            dbentry.pflddes->field_type);
        set_dict_item_steal(dict, field_name, ost);
        status = dbNextField(&dbentry, 0);
    }

    dbFinishEntry(&dbentry);
    return dict;
}


/* Updates PV field with integrated db lookup.  Safer to do this in C as we need
 * an intermediate copy of the dbAddr structure, which changes size between
 * EPICS releases. */
static PyObject *db_put_field(PyObject *self, PyObject *args)
{
    const char *name;
    short dbrType;
    void *pbuffer;
    long length;
    if (!PyArg_ParseTuple(args, "shnl", &name, &dbrType, &pbuffer, &length))
        return NULL;

    struct dbAddr dbAddr;
    if (dbNameToAddr(name, &dbAddr))
        return PyErr_Format(
            PyExc_RuntimeError, "dbNameToAddr failed for %s", name);
    if (dbPutField(&dbAddr, dbrType, pbuffer, length))
        return PyErr_Format(
            PyExc_RuntimeError, "dbPutField failed for %s", name);
    Py_RETURN_NONE;
}


/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * */
/*                            IOC PV put logging                             */
/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * */

struct formatted
{
    long length;
    epicsOldString values[];
};

static struct formatted * FormatValue(struct dbAddr *dbaddr)
{
    struct formatted *formatted =
        malloc(sizeof(struct formatted) +
            dbaddr->no_elements * sizeof(epicsOldString));

    /* Start by using dbGetField() to format everything.  This will also update
     * the length. */
    formatted->length = dbaddr->no_elements;
    dbGetField(
        dbaddr, DBR_STRING, formatted->values, NULL, &formatted->length, NULL);

    /* Alas dbGetField is rather rubbish at formatting floating point numbers,
     * so if that's what we've got redo everything ourselves. */
#define FORMAT(type, format) \
    do { \
        type *raw = (type *) dbaddr->pfield; \
        for (int i = 0; i < formatted->length; i ++) \
            snprintf(formatted->values[i], sizeof(epicsOldString), \
                format, raw[i]); \
    } while (0)

    switch (dbaddr->field_type)
    {
        case DBF_FLOAT:
            FORMAT(epicsFloat32, "%.7g");
            break;
        case DBF_DOUBLE:
            FORMAT(epicsFloat64, "%.15lg");
            break;
    }
#undef FORMAT
    return formatted;
}

static void PrintValue(struct formatted *formatted)
{
    if (formatted->length == 1)
        printf("%s", formatted->values[0]);
    else
    {
        printf("[");
        for (int i = 0; i < formatted->length; i ++)
        {
            if (i > 0)  printf(", ");
            printf("%s", formatted->values[i]);
        }
        printf("]");
    }
}

void EpicsPvPutHook(struct asTrapWriteMessage *pmessage, int after)
{
    struct dbChannel *pchan = pmessage->serverSpecific;
    dbAddr *dbaddr = &pchan->addr;
    struct formatted *value = FormatValue(dbaddr);

    if (after)
    {
        /* Log the message after the event. */
        struct formatted *old_value = pmessage->userPvt;
        printf("%s@%s %s.%s ",
            pmessage->userid, pmessage->hostid,
            dbaddr->precord->name, dbaddr->pfldDes->name);
        PrintValue(old_value);
        printf(" -> ");
        PrintValue(value);
        printf("\n");

        free(old_value);
        free(value);
    }
    else
        /* Just save the old value for logging after. */
        pmessage->userPvt = value;
}


static PyObject *install_pv_logging(PyObject *self, PyObject *args)
{
    const char *acf_file;

    if (!PyArg_ParseTuple(args, "s", &acf_file))
        return NULL;

    asSetFilename(acf_file);
    asTrapWriteRegisterListener(EpicsPvPutHook);
    Py_RETURN_NONE;
}

static struct PyMethodDef softioc_methods[] = {
    {"get_DBF_values",  get_DBF_values, METH_VARARGS,
     "Get a map of DBF names to values"},
    {"get_field_offsets",  get_field_offsets, METH_VARARGS,
     "Get offset, size and type for each record field"},
    {"db_put_field",  db_put_field, METH_VARARGS,
     "Put a database field to a value"},
    {"install_pv_logging",  install_pv_logging, METH_VARARGS,
     "Install caput logging to stdout"},
    {NULL, NULL, 0, NULL}        /* Sentinel */
};

#if PY_MAJOR_VERSION >= 3
static struct PyModuleDef softioc_module = {
  PyModuleDef_HEAD_INIT,
    "softioc._extension",
    NULL,
    -1,
    softioc_methods,
};
#endif

#if PY_MAJOR_VERSION >= 3
#  define PyMOD(NAME) PyObject* PyInit_##NAME (void)
#else
#  define PyMOD(NAME) void init##NAME (void)
#endif

PyMOD(_extension)
{
#if PY_MAJOR_VERSION >= 3
    return PyModule_Create(&softioc_module);
#else
    Py_InitModule("softioc._extension", softioc_methods);
#endif
}
