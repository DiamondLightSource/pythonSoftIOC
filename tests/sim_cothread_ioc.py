from argparse import ArgumentParser

from softioc import softioc, builder, pvlog


if __name__ == "__main__":
    import cothread

    # Being run as an IOC, so parse args and set prefix
    parser = ArgumentParser()
    parser.add_argument('prefix', help="The PV prefix for the records")
    parsed_args = parser.parse_args()
    builder.SetDeviceName(parsed_args.prefix)

    import sim_records

    # Run the IOC
    builder.LoadDatabase()
    softioc.iocInit()
    cothread.WaitForQuit()
