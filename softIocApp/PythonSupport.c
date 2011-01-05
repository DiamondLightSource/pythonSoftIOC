#include <string.h>
#include <dbAccess.h>
#include <dbStaticLib.h>



/* Returns the EPICS_BASE path used to build this IOC. */

char * get_EPICS_BASE()
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
