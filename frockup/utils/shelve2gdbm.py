import shelve
import gdbm
import sys
import os
import json


def main():
    directory = sys.argv[1]
    assert os.path.exists(directory)
    assert os.path.isdir(directory)
    infile = os.path.join(directory, '.frockup.db')
    outfile = os.path.join(directory, '.frockup.gdbm')
    assert os.path.exists(infile)
    assert not os.path.exists(outfile)

    origdb = shelve.open(infile)
    newdb = gdbm.open(outfile, 'c')

    for key, value in origdb.iteritems():
        print " - Converting:", key
        newdb[key] = json.dumps(value)

    newdb.close()
    origdb.close()

if __name__ == '__main__':
    main()
