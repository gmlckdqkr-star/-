import sys, zipfile, re
# structure only: prints non-data lines and the first data row of each block (all blocks start in 1926/1927); never prints rows after 2014
for zp in sys.argv[1:]:
    z = zipfile.ZipFile(zp); name = z.namelist()[0]
    txt = z.read(name).decode('latin1').splitlines()
    print('==', name, 'lines', len(txt))
    prev_data = False; nblock = 0
    for i, l in enumerate(txt):
        p0 = l.split(',')[0].strip()
        is_data = p0.isdigit()
        if not is_data:
            print('%6d | %s' % (i, l[:200])); prev_data = False
        else:
            if not prev_data:
                assert int(p0[:4]) <= 2014
                print('%6d | first data row of block: %s' % (i, l[:200])); nblock += 1
            prev_data = True
    print('blocks', nblock)
