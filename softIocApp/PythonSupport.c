#include <string.h>

#define db_accessHFORdb_accessC     // Needed to get correct DBF_ values
#include <dbAccess.h>
#include <dbFldTypes.h>
#include <dbStaticLib.h>
#include <asTrapWrite.h>



/* Returns the EPICS_BASE path used to build this IOC. */

char * get_EPICS_BASE(void)
{
    return EPICS_BASE;
}



/* Given an array of field names, this routine looks up each field name in
 * the EPICS database and returns the corresponding field offset. */

void get_field_offsets(
    const char * record_type, const char * field_names[], int field_count,
    short field_offset[], short field_size[], short field_type[])
{
    int status;
    DBENTRY dbentry;
    dbInitEntry(pdbbase, &dbentry);

    status = dbFindRecordType(&dbentry, record_type);
    if (status != 0)
        printf("Unable to find record type \"%s\" (error %d)\n",
            record_type, status);
    else
        status = dbFirstField(&dbentry, 0);
    while (status == 0)
    {
        const char * field_name = dbGetFieldName(&dbentry);
        int i;
        for (i = 0; i < field_count; i ++)
        {
            if (strcmp(field_names[i], field_name) == 0)
            {
                field_offset[i] = dbentry.pflddes->offset;
                field_size[i]   = dbentry.pflddes->size;
                field_type[i]   = dbentry.pflddes->field_type;
            }
        }
        status = dbNextField(&dbentry, 0);
    }

    dbFinishEntry(&dbentry);
}


/* Updates PV field with integrated db lookup.  Safer to do this in C as we need
 * an intermediate copy of the dbAddr structure, which changes size between
 * EPICS releases. */
int db_put_field(const char *name, short dbrType, void *pbuffer, long length)
{
    struct dbAddr dbAddr;
    int rc = dbNameToAddr(name, &dbAddr);
    if (rc == 0)
        rc = dbPutField(&dbAddr, dbrType, pbuffer, length);
    return rc;
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
    struct dbAddr *dbaddr = pmessage->serverSpecific;
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
