    # ~ # Get the delay stage positions of this scan
    # ~ metaDataFile = [x for x in os.listdir(scan_dir) if x[:13] == 'scanMetaData_'][0]
    # ~ # Load the meta data
    # ~ metaDataDict = {}
    # ~ with open(scan_dir + '//' + metaDataFile,'r') as f:
        # ~ for line in f:
            # ~ if line[:line.find(":")] != '#':
                # ~ metaDataDict[line[:line.find(":")]] = line[line.find(":")+1:].replace('\n','')
    # ~ print(metaDataDict['dsPositions entry'])
    # ~ dsPositions
    # ~ return
