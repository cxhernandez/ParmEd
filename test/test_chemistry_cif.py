# These unit tests were taken from PdbxReaderTest.py and PdbxWriterTest.py from
# the pdbx package on the wwPDB website.

##
# File:    PdbxReaderTests.py
# Author:  jdw
# Date:    9-Jan-2012
# Version: 0.001
#
# Update:
#  27-Sep-2012  jdw add test case for reading PDBx structure factor file 
#
##
"""
Test cases for reading PDBx/mmCIF data files PdbxReader class -

"""
import sys, unittest, traceback, os
from utils import get_fn, get_saved_fn, diff_files

from chemistry.formats.pdbx import PdbxReader, PdbxWriter
from chemistry.formats.pdbx.PdbxContainers import *

class PdbxReaderTests(unittest.TestCase):
    def setUp(self):
        self.verbose=False
        self.pathPdbxDataFile = get_fn("1kip.cif")
        self.pathBigPdbxDataFile = get_fn("1ffk.cif")
        self.pathSFDataFile = get_fn("1kip-sf.cif")

    def tearDown(self):
        pass

    def testReadSmallDataFile(self): 
        """ Test reading small CIF file """
        try:
            #
            myDataList=[]
            ifh = open(self.pathPdbxDataFile, "r")
            pRd=PdbxReader(ifh)
            pRd.read(myDataList)
            ifh.close()            
        except:
            traceback.print_exc(file=sys.stderr)
            self.fail()

    def testReadBigDataFile(self): 
        """ Test reading large CIF file """
        try:
            #
            myDataList=[]
            ifh = open(self.pathBigPdbxDataFile, "r")
            pRd=PdbxReader(ifh)
            pRd.read(myDataList)
            ifh.close()            
        except:
            traceback.print_exc(file=sys.stderr)
            self.fail()

    def testReadSFDataFile(self): 
        """read PDB structure factor data file and compute statistics on f/sig(f).
        """
        #
        myContainerList=[]
        ifh = open(self.pathSFDataFile, "r")
        pRd=PdbxReader(ifh)
        pRd.read(myContainerList)
        c0=myContainerList[0]
        #
        catObj=c0.getObj("refln")
        if catObj is None:
            return False
        
        nRows=catObj.getRowCount()
        #
        # Get column name index.
        #
        itDict={}
        itNameList=catObj.getItemNameList()
        for idxIt,itName in enumerate(itNameList):
            itDict[str(itName).lower()]=idxIt
            #
        idf=itDict['_refln.f_meas_au']
        idsigf=itDict['_refln.f_meas_sigma_au']
        minR=100
        maxR=-1
        sumR=0
        icount=0
        for row in  catObj.getRowList():
            try:
                f=float(row[idf])
                sigf=float(row[idsigf])
                ratio=sigf/f
                maxR=max(maxR,ratio)
                minR=min(minR,ratio)
                sumR+=ratio
                icount+=1
            except:
                continue
        
        ifh.close()
        self.assertAlmostEqual(minR, 0.00455182)
        self.assertAlmostEqual(maxR, 549.333333333)
        self.assertAlmostEqual(sumR/icount, 0.547058, delta=0.000002)
        self.assertEqual(icount, 18508)

class PdbxWriterTests(unittest.TestCase):
    def setUp(self):
        self.lfh=sys.stderr
        self.verbose=False
        self.pathPdbxDataFile = get_fn("1kip.cif")
        self.pathOutputFile = get_fn("testOutputDataFile.cif", written=True)
        if not os.path.exists(get_fn('writes')):
            os.makedirs(get_fn('writes'))

    def tearDown(self):
        if os.path.exists(get_fn('writes')):
            for f in os.listdir(get_fn('writes')):
                os.unlink(get_fn(f, written=True))

    def testWriteDataFile(self): 
        """ Test writing CIF file """
        myDataList=[]
        ofh = open(get_fn("test-output.cif", written=True), "w")
        curContainer=DataContainer("myblock")
        aCat=DataCategory("pdbx_seqtool_mapping_ref")
        aCat.appendAttribute("ordinal")
        aCat.appendAttribute("entity_id")
        aCat.appendAttribute("auth_mon_id")
        aCat.appendAttribute("auth_mon_num")
        aCat.appendAttribute("pdb_chain_id")
        aCat.appendAttribute("ref_mon_id")
        aCat.appendAttribute("ref_mon_num")                        
        aCat.append((1,2,3,4,5,6,7))
        aCat.append((1,2,3,4,5,6,7))
        aCat.append((1,2,3,4,5,6,7))
        aCat.append((1,2,3,4,5,6,7))
        curContainer.append(aCat)
        myDataList.append(curContainer)
        pdbxW=PdbxWriter(ofh)
        pdbxW.write(myDataList)
        ofh.close()
        self.assertTrue(diff_files(get_saved_fn('test-output.cif'),
                                   get_fn('test-output.cif', written=True)))

    def testUpdateDataFile(self): 
        """ Test writing another CIF file """
        # Create a initial data file --
        #
        myDataList=[]
        ofh = open(get_fn("test-output-1.cif", written=True), "w")
        curContainer=DataContainer("myblock")
        aCat=DataCategory("pdbx_seqtool_mapping_ref")
        aCat.appendAttribute("ordinal")
        aCat.appendAttribute("entity_id")
        aCat.appendAttribute("auth_mon_id")
        aCat.appendAttribute("auth_mon_num")
        aCat.appendAttribute("pdb_chain_id")
        aCat.appendAttribute("ref_mon_id")
        aCat.appendAttribute("ref_mon_num")                        
        aCat.append((1,2,3,4,5,6,7))
        aCat.append((1,2,3,4,5,6,7))
        aCat.append((1,2,3,4,5,6,7))
        aCat.append((1,2,3,4,5,6,7))
        curContainer.append(aCat)
        myDataList.append(curContainer)
        pdbxW=PdbxWriter(ofh)
        pdbxW.write(myDataList)
        ofh.close()
        self.assertTrue(diff_files(get_saved_fn('test-output-1.cif'),
                                   get_fn('test-output-1.cif', written=True)))
        #
        # Read and update the data -
        # 
        myDataList=[]
        ifh = open(get_fn("test-output-1.cif", written=True), "r")
        pRd=PdbxReader(ifh)
        pRd.read(myDataList)
        ifh.close()
        #
        myBlock=myDataList[0]
        dest = open(get_fn('test_write_1.txt', written=True), 'w')
        myBlock.printIt(dest)
        myCat=myBlock.getObj('pdbx_seqtool_mapping_ref')
        myCat.printIt(dest)
        dest.close()
        for iRow in range(0,myCat.getRowCount()):
            myCat.setValue('some value', 'ref_mon_id',iRow)
            myCat.setValue(100, 'ref_mon_num',iRow)
        ofh = open(get_fn("test-output-2.cif", written=True), "w")            
        pdbxW=PdbxWriter(ofh)
        pdbxW.write(myDataList)
        ofh.close()
        self.assertTrue(diff_files(get_saved_fn('test-output-2.cif'),
                                   get_fn('test-output-2.cif', written=True)))
        self.assertTrue(diff_files(get_saved_fn('test_write_1.txt'),
                                   get_fn('test_write_1.txt', written=True)))

    def testReadDataFile(self): 
        """ Test reading a CIF file (... again?) """
        #
        myDataList=[]
        ifh = open(self.pathPdbxDataFile, "r")
        pRd=PdbxReader(ifh)
        pRd.read(myDataList)
        ifh.close()            

    def testReadWriteDataFile(self):
        """Test case -  data file read write test
        """
        myDataList=[]
        ifh = open(self.pathPdbxDataFile, "r")            
        pRd=PdbxReader(ifh)
        pRd.read(myDataList)
        ifh.close()            

        ofh = open(self.pathOutputFile, "w")
        pWr=PdbxWriter(ofh)
        pWr.write(myDataList)        
        ofh.close()
