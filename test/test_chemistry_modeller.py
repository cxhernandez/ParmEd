"""
Tests the functionality in chemistry.modeller
"""
from chemistry import Atom, read_PDB
from chemistry.exceptions import AmberOFFWarning
from chemistry.modeller import (ResidueTemplate, ResidueTemplateContainer,
                                PROTEIN, SOLVENT, AmberOFFLibrary)
from chemistry.amber import AmberParm
from chemistry.exceptions import BondError
import os
from ParmedTools import changeRadii
import random
import sys
import unittest
import utils
import warnings
get_fn = utils.get_fn
skipIf = utils.skipIf

try:
    import cStringIO as StringIO
except ImportError:
    # Must be Python 3
    import io as StringIO
try:
    from itertools import izip as zip
except ImportError:
    pass # Must by py3

class TestResidueTemplate(unittest.TestCase):
    """ Tests the ResidueTemplate class """

    def setUp(self):
        self.templ = templ = ResidueTemplate('ACE')
        templ.add_atom(Atom(name='HH31', type='HC'))
        templ.add_atom(Atom(name='CH3', type='CT'))
        templ.add_atom(Atom(name='HH32', type='HC'))
        templ.add_atom(Atom(name='HH33', type='HC'))
        templ.add_atom(Atom(name='C', type='C'))
        templ.add_atom(Atom(name='O', type='O'))
        templ.tail = templ.atoms[4]

    def testAddAtom(self):
        """ Tests the ResidueTemplate.add_atom function """
        templ = self.templ
        self.assertEqual(len(templ), 6)
        for i in range(6):
            self.assertIs(templ[i], templ.atoms[i])
        for x, y in zip(templ, templ.atoms):
            self.assertIs(x, y)
        for i, atom in enumerate(templ):
            self.assertIs(atom, templ.atoms[i])
        self.assertIs(templ.head, None)
        self.assertIs(templ.tail, templ[-2])
        self.assertRaises(ValueError, lambda: templ.add_atom(Atom(name='C')))

    def testAddBondsAtoms(self):
        """ Tests the ResidueTemplate.add_bond function w/ indices """
        templ = self.templ
        a1, a2, a3, a4, a5, a6 = templ.atoms
        a7 = Atom(name='Unimportant', type='black hole')
        templ.add_bond(a1, a2)
        templ.add_bond(a2, a3)
        templ.add_bond(a3, a4)
        templ.add_bond(a2, a5)
        templ.add_bond(a5, a6)
        self.assertRaises(RuntimeError, lambda: templ.add_bond(a1, a7))
        self.assertRaises(BondError, lambda: templ.add_bond(a1, a1))
        self.assertIn(a1, a2.bond_partners)
        self.assertIn(a2, a1.bond_partners)
        self.assertIn(a3, a2.bond_partners)
        self.assertIn(a2, a3.bond_partners)
        self.assertIn(a5, a2.bond_partners)
        self.assertIn(a2, a5.bond_partners)
        self.assertIn(a5, a6.bond_partners)
        self.assertIn(a6, a5.bond_partners)
        self.assertEqual(len(templ.bonds), 5)

    def testAddBondsIdx(self):
        """ Tests the ResidueTemplate.add_bond function w/ atoms """
        templ = self.templ
        a1, a2, a3, a4, a5, a6 = range(6)
        a7 = Atom(name='Unimportant', type='black hole')
        templ.add_bond(a1, a2)
        templ.add_bond(a2, a3)
        templ.add_bond(a3, a4)
        templ.add_bond(a2, a5)
        templ.add_bond(a5, a6)
        self.assertRaises(RuntimeError, lambda: templ.add_bond(a1, a7))
        self.assertRaises(BondError, lambda: templ.add_bond(a1, a1))
        a1, a2, a3, a4, a5, a6 = templ.atoms
        self.assertIn(a1, a2.bond_partners)
        self.assertIn(a2, a1.bond_partners)
        self.assertIn(a3, a2.bond_partners)
        self.assertIn(a2, a3.bond_partners)
        self.assertIn(a5, a2.bond_partners)
        self.assertIn(a2, a5.bond_partners)
        self.assertIn(a5, a6.bond_partners)
        self.assertIn(a6, a5.bond_partners)
        self.assertEqual(len(templ.bonds), 5)

    def testFromResidue(self):
        """ Tests the ResidueTemplate.from_residue function """
        # Grab this residue from an amber prmtop file
        struct = AmberParm(get_fn('trx.prmtop'), get_fn('trx.inpcrd'))
        for res in struct.residues:
            self._check_arbitrary_res(struct, res)

    def _check_arbitrary_res(self, struct, res):
        orig_indices = [a.idx for a in res]
        templ = ResidueTemplate.from_residue(res)
        # Make sure we didn't clobber any of the atoms in res
        for i, atom in zip(orig_indices, res.atoms):
            self.assertIs(atom.list, struct.atoms)
            self.assertEqual(atom.idx, i)
        # Make sure that we have the same number of atoms in the residue as the
        # source
        self.assertEqual(len(res), len(templ))
        for a1, a2 in zip(res, templ):
            self.assertIsInstance(a1, Atom)
            self.assertIsInstance(a2, Atom)
            self.assertEqual(a1.name, a2.name)
            self.assertEqual(a1.type, a2.type)
            self.assertEqual(a1.atomic_number, a2.atomic_number)
            self.assertEqual(a1.xx, a2.xx)
            self.assertEqual(a1.xy, a2.xy)
            self.assertEqual(a1.xz, a2.xz)
        # Make sure we have the correct number of bonds in the residue
        bondset = set()
        for atom in res:
            for bond in atom.bonds:
                if bond.atom1 in res and bond.atom2 in res:
                    bondset.add(bond)
        self.assertGreater(len(bondset), 0)
        self.assertEqual(len(bondset), len(templ.bonds))
        # Make sure that each atom has the correct number of bonds
        for i, atom in enumerate(res):
            for bond in atom.bonds:
                try:
                    id1 = res.atoms.index(bond.atom1)
                    id2 = res.atoms.index(bond.atom2)
                except ValueError:
                    if bond.atom1 in res:
                        oatom = bond.atom2
                        idx = res.atoms.index(bond.atom1)
                    else:
                        oatom = bond.atom1
                        idx = res.atoms.index(bond.atom2)
                    if oatom.residue.idx == res.idx - 1:
                        self.assertIs(templ.head, templ[idx])
                    elif oatom.residue.idx == res.idx + 1:
                        self.assertIs(templ.tail, templ[idx])
                    elif oatom.residue.idx == res.idx:
                        self.assertTrue(False) # Should never hit
                    else:
                        # Should only happen with CYX for amber prmtop...
                        self.assertEqual(res.name, 'CYX')
                        self.assertEqual(atom.name, 'SG')
                        if bond.atom1 in res:
                            self.assertIn(templ[idx], templ.connections)
                else:
                    self.assertIn(templ[id1], templ[id2].bond_partners)
                    self.assertIn(templ[id2], templ[id1].bond_partners)
        # Make sure that our coordinates come as a numpy array
        if utils.has_numpy():
            self.assertIsInstance(templ.coordinates, utils.numpy.ndarray)
            self.assertEqual(templ.coordinates.shape, (len(templ)*3,))

class TestResidueTemplateContainer(unittest.TestCase):
    """ Tests the ResidueTemplateContainer class """

    def testFromStructure(self):
        """ Tests building ResidueTemplateContainer from a Structure """
        struct = AmberParm(get_fn('trx.prmtop'), get_fn('trx.inpcrd'))
        cont = ResidueTemplateContainer.from_structure(struct)
        for res, sres in zip(cont, struct.residues):
            self.assertIsInstance(res, ResidueTemplate)
            self.assertEqual(len(res), len(sres))
            for a1, a2 in zip(res, sres):
                self.assertEqual(a1.name, a2.name)
                self.assertEqual(a1.type, a2.type)
                self.assertEqual(a1.charge, a2.charge)
                self.assertEqual(a1.xx, a2.xx)
                self.assertEqual(a1.xy, a2.xy)
                self.assertEqual(a1.xz, a2.xz)

    def testToLibrary(self):
        """ Tests converting a ResidueTemplateContainer to a library/dict """
        lib = ResidueTemplateContainer.from_structure(
                AmberParm(get_fn('trx.prmtop'), get_fn('trx.inpcrd'))
        ).to_library()
        self.assertIsInstance(lib, dict)
        self.assertEqual(len(lib.keys()), 23)
        refset = set(["NSER", "ASP", "LYS", "ILE", "HID", "LEU", "THR", "SER",
                      "PHE", "VAL", "ALA", "GLY", "ASH", "TRP", "GLU", "CYX",
                      "PRO", "MET", "TYR", "GLN", "ASN", "ARG", "CALA"])
        self.assertEqual(set(lib.keys()), refset)

class TestAmberOFFLibrary(unittest.TestCase):
    """ Tests the AmberOFFLibrary class """

    def testReadInternal(self):
        """ Tests reading Amber amino12 OFF library (internal residues) """
        offlib = AmberOFFLibrary.parse(get_fn('amino12.lib'))
        self.assertEqual(len(offlib), 28)
        for name, res in offlib.items():
            self.assertIsInstance(res, ResidueTemplate)
            self.assertEqual(name, res.name)
            self.assertEqual(res.head.name, 'N')
            self.assertEqual(res.tail.name, 'C')
            self.assertIs(res.type, PROTEIN)
        # Check two residues in particular: ALA and CYX
        ala = offlib['ALA']
        self.assertEqual(len(ala), 10)
        self.assertEqual(len(ala.bonds), 9)
        self.assertIn(ala[0], ala[1].bond_partners)
        self.assertIn(ala[0], ala[2].bond_partners)
        self.assertIn(ala[2], ala[3].bond_partners)
        self.assertIn(ala[2], ala[4].bond_partners)
        self.assertIn(ala[2], ala[8].bond_partners)
        self.assertIn(ala[4], ala[5].bond_partners)
        self.assertIn(ala[4], ala[6].bond_partners)
        self.assertIn(ala[4], ala[7].bond_partners)
        self.assertIn(ala[8], ala[9].bond_partners)
        self.assertAlmostEqual(ala[0].xx, 3.325770)
        self.assertAlmostEqual(ala[0].xy, 1.547909)
        self.assertAlmostEqual(ala[0].xz, -1.607204E-06)
        self.assertAlmostEqual(ala[1].xx, 3.909407)
        self.assertAlmostEqual(ala[1].xy, 0.723611)
        self.assertAlmostEqual(ala[1].xz, -2.739882E-06)
        self.assertAlmostEqual(ala[2].xx, 3.970048)
        self.assertAlmostEqual(ala[2].xy, 2.845795)
        self.assertAlmostEqual(ala[2].xz, -1.311163E-07)
        self.assertAlmostEqual(ala[3].xx, 3.671663)
        self.assertAlmostEqual(ala[3].xy, 3.400129)
        self.assertAlmostEqual(ala[3].xz, -0.889820)
        self.assertAlmostEqual(ala[4].xx, 3.576965)
        self.assertAlmostEqual(ala[4].xy, 3.653838)
        self.assertAlmostEqual(ala[4].xz, 1.232143)
        self.assertAlmostEqual(ala[5].xx, 3.877484)
        self.assertAlmostEqual(ala[5].xy, 3.115795)
        self.assertAlmostEqual(ala[5].xz, 2.131197)
        self.assertAlmostEqual(ala[6].xx, 4.075059)
        self.assertAlmostEqual(ala[6].xy, 4.623017)
        self.assertAlmostEqual(ala[6].xz, 1.205786)
        self.assertAlmostEqual(ala[7].xx, 2.496995)
        self.assertAlmostEqual(ala[7].xy, 3.801075)
        self.assertAlmostEqual(ala[7].xz, 1.241379)
        self.assertAlmostEqual(ala[8].xx, 5.485541)
        self.assertAlmostEqual(ala[8].xy, 2.705207)
        self.assertAlmostEqual(ala[8].xz, -4.398755E-06)
        self.assertAlmostEqual(ala[9].xx, 6.008824)
        self.assertAlmostEqual(ala[9].xy, 1.593175)
        self.assertAlmostEqual(ala[9].xz, -8.449768E-06)
        # now cyx
        cyx = offlib['CYX']
        self.assertEqual(len(cyx), 10)
        self.assertEqual(len(cyx.bonds), 9)
        self.assertIn(cyx[0], cyx[1].bond_partners)
        self.assertIn(cyx[0], cyx[2].bond_partners)
        self.assertIn(cyx[2], cyx[3].bond_partners)
        self.assertIn(cyx[2], cyx[4].bond_partners)
        self.assertIn(cyx[2], cyx[8].bond_partners)
        self.assertIn(cyx[4], cyx[5].bond_partners)
        self.assertIn(cyx[4], cyx[6].bond_partners)
        self.assertIn(cyx[4], cyx[7].bond_partners)
        self.assertIn(cyx[8], cyx[9].bond_partners)
        self.assertAlmostEqual(cyx[0].xx, 3.325770)
        self.assertAlmostEqual(cyx[0].xy, 1.547909)
        self.assertAlmostEqual(cyx[0].xz, -1.607204E-06)
        self.assertAlmostEqual(cyx[1].xx, 3.909407)
        self.assertAlmostEqual(cyx[1].xy, 0.723611)
        self.assertAlmostEqual(cyx[1].xz, -2.739882E-06)
        self.assertAlmostEqual(cyx[2].xx, 3.970048)
        self.assertAlmostEqual(cyx[2].xy, 2.845795)
        self.assertAlmostEqual(cyx[2].xz, -1.311163E-07)
        self.assertAlmostEqual(cyx[3].xx, 3.671663)
        self.assertAlmostEqual(cyx[3].xy, 3.400129)
        self.assertAlmostEqual(cyx[3].xz, -0.889820)
        self.assertAlmostEqual(cyx[4].xx, 3.576965)
        self.assertAlmostEqual(cyx[4].xy, 3.653838)
        self.assertAlmostEqual(cyx[4].xz, 1.232143)
        self.assertAlmostEqual(cyx[5].xx, 2.496995)
        self.assertAlmostEqual(cyx[5].xy, 3.801075)
        self.assertAlmostEqual(cyx[5].xz, 1.241379)
        self.assertAlmostEqual(cyx[6].xx, 3.877484)
        self.assertAlmostEqual(cyx[6].xy, 3.115795)
        self.assertAlmostEqual(cyx[6].xz, 2.131197)
        self.assertAlmostEqual(cyx[7].xx, 4.309573)
        self.assertAlmostEqual(cyx[7].xy, 5.303523)
        self.assertAlmostEqual(cyx[7].xz, 1.366036)
        self.assertAlmostEqual(cyx[8].xx, 5.485541)
        self.assertAlmostEqual(cyx[8].xy, 2.705207)
        self.assertAlmostEqual(cyx[8].xz, -4.398755E-06)
        self.assertAlmostEqual(cyx[9].xx, 6.008824)
        self.assertAlmostEqual(cyx[9].xy, 1.593175)
        self.assertAlmostEqual(cyx[9].xz, -8.449768E-06)
        # Check connections
        self.assertEqual(len(cyx.connections), 1)
        self.assertEqual(cyx.connections[0].name, 'SG')

    def testReadNTerm(self):
        """ Test reading N-terminal amino acid Amber OFF library """
        offlib = AmberOFFLibrary.parse(get_fn('aminont12.lib'))
        self.assertEqual(len(offlib), 24)
        for name, res in offlib.items():
            self.assertIsInstance(res, ResidueTemplate)
            self.assertEqual(name, res.name)
            self.assertIs(res.head, None)
            self.assertEqual(res.tail.name, 'C')
            self.assertIs(res.type, PROTEIN)

    def testReadCTerm(self):
        """ Test reading C-terminal amino acid Amber OFF library """
        offlib = AmberOFFLibrary.parse(get_fn('aminoct12.lib'))
        self.assertEqual(len(offlib), 26)
        for name, res in offlib.items():
            self.assertIsInstance(res, ResidueTemplate)
            self.assertEqual(name, res.name)
            self.assertIs(res.head.name, 'N')
            self.assertIs(res.type, PROTEIN)

    def testReadSolvents(self):
        """ Test reading solvent Amber OFF lib (multi-res units) """
        # Turn off warnings... the solvents.lib file is SO broken.
        warnings.filterwarnings('ignore', module='.', category=AmberOFFWarning)
        offlib = AmberOFFLibrary.parse(get_fn('solvents.lib'))
        self.assertEqual(len(offlib), 24)
        for name, res in offlib.items():
            self.assertEqual(res.name, name)
            if 'BOX' in name:
                self.assertIsInstance(res, ResidueTemplateContainer)
                # Make sure all residues have the same features as the first
                for r in res:
                    self.assertIs(r.type, SOLVENT)
                    for a1, a2 in zip(r, res[0]):
                        self.assertEqual(a1.name, a2.name)
                        self.assertEqual(a1.type, a2.type)
                        self.assertEqual(a1.charge, a2.charge)
                        self.assertEqual(a1.atomic_number, a2.atomic_number)
                        self.assertEqual(len(a1.bond_partners),
                                         len(a2.bond_partners))
                        set1 = set([x.name for x in a1.bond_partners])
                        set2 = set([x.name for x in a2.bond_partners])
                        self.assertEqual(set1, set2)
                        if a1 is not a2:
                            self.assertNotEqual(a1.xx, a2.xx)
                            self.assertNotEqual(a1.xy, a2.xy)
                            self.assertNotEqual(a1.xz, a2.xz)
            else:
                self.assertIs(res.type, SOLVENT)
                self.assertIsInstance(res, ResidueTemplate)
        # Check a few solvent boxes in particular
        chcl3 = offlib['CHCL3BOX']
        self.assertEqual(chcl3.name, 'CHCL3BOX')
        self.assertEqual(len(chcl3), 1375)
        self.assertEqual(chcl3.box[0], 56.496)
        self.assertEqual(chcl3.box[1], 56.496)
        self.assertEqual(chcl3.box[2], 56.496)
        for res in chcl3:
            self.assertEqual(res.name, 'CL3')
        self.assertAlmostEqual(chcl3.box[3], 90, places=4)
        self.assertAlmostEqual(chcl3.box[4], 90, places=4)
        self.assertAlmostEqual(chcl3.box[5], 90, places=4)
        # Check some positions (but obviously not all)
        self.assertAlmostEqual(chcl3[0][0].xx, -22.675111)
        self.assertAlmostEqual(chcl3[0][0].xy, -13.977137)
        self.assertAlmostEqual(chcl3[0][0].xz, -21.470579)
        self.assertAlmostEqual(chcl3[1][0].xx, -9.668111)
        self.assertAlmostEqual(chcl3[1][0].xy, -15.097137)
        self.assertAlmostEqual(chcl3[1][0].xz, -18.569579)

    def testReadWriteInternal(self):
        """ Tests reading/writing of Amber OFF internal AA libs """
        offlib = AmberOFFLibrary.parse(get_fn('amino12.lib'))
        outfile = StringIO.StringIO()
        AmberOFFLibrary.write(offlib, outfile)
        outfile.seek(0)
        offlib2 = AmberOFFLibrary.parse(outfile)
        self._check_read_written_libs(offlib, offlib2)

    def testReadWriteCTerm(self):
        """ Tests reading/writing of Amber OFF C-terminal AA libs """
        offlib = AmberOFFLibrary.parse(get_fn('aminoct12.lib'))
        outfile = StringIO.StringIO()
        AmberOFFLibrary.write(offlib, outfile)
        outfile.seek(0)
        offlib2 = AmberOFFLibrary.parse(outfile)
        self._check_read_written_libs(offlib, offlib2)

    def testReadWriteNTerm(self):
        """ Tests reading/writing of Amber OFF N-terminal AA libs """
        offlib = AmberOFFLibrary.parse(get_fn('aminont12.lib'))
        outfile = StringIO.StringIO()
        AmberOFFLibrary.write(offlib, outfile)
        outfile.seek(0)
        offlib2 = AmberOFFLibrary.parse(outfile)
        self._check_read_written_libs(offlib, offlib2)

    def testReadWriteSolventLib(self):
        """ Tests reading/writing of Amber OFF solvent libs """
        offlib = AmberOFFLibrary.parse(get_fn('solvents.lib'))
        outfile = StringIO.StringIO()
        AmberOFFLibrary.write(offlib, outfile)
        outfile.seek(0)
        offlib2 = AmberOFFLibrary.parse(outfile)

    def _check_read_written_libs(self, offlib, offlib2):
        # Check that offlib and offlib2 are equivalent
        self.assertEqual(len(offlib), len(offlib2))
        self.assertEqual(offlib.keys(), offlib2.keys())
        for key in offlib.keys():
            r1 = offlib[key]
            r2 = offlib2[key]
            # Check residues
            self.assertEqual(len(r1), len(r2))
            self.assertIs(r1.type, r2.type)
            # Check head and tail
            if r1.head is None or r2.head is None:
                self.assertIs(r1.head, None)
                self.assertIs(r2.head, None)
            else:
                self.assertEqual(r1.head.name, r2.head.name)
                self.assertEqual(r1.head.type, r2.head.type)
                self.assertEqual(r1.head.idx, r2.head.idx)
            if r1.tail is None or r2.tail is None:
                self.assertIs(r1.tail, None)
                self.assertIs(r2.tail, None)
            else:
                self.assertEqual(r1.tail.name, r2.tail.name)
                self.assertEqual(r1.tail.type, r2.tail.type)
                self.assertEqual(r1.tail.idx, r2.tail.idx)
            # Check atom properties
            for a1, a2 in zip(r1, r2):
                self.assertEqual(a1.name, a2.name)
                self.assertEqual(a1.type, a2.type)
                self.assertAlmostEqual(a1.charge, a2.charge)
                self.assertAlmostEqual(a1.xx, a2.xx, places=4)
                self.assertAlmostEqual(a1.xy, a2.xy, places=4)
                self.assertAlmostEqual(a1.xz, a2.xz, places=4)
                self.assertEqual(a1.vx, a2.vx)
                self.assertEqual(a1.vy, a2.vy)
                self.assertEqual(a1.vz, a2.vz)
            # Check bonds
            self.assertEqual(len(r1.bonds), len(r2.bonds))
            for b1, b2 in zip(r1.bonds, r2.bonds):
                self.assertEqual(b1.atom1.name, b2.atom1.name)
                self.assertEqual(b1.atom2.name, b2.atom2.name)

class TestAmberOFFLeapCompatibility(unittest.TestCase):
    """ Tests the AmberOFFLibrary classes written in LEaP """

    def setUp(self):
        self.tleap = utils.which('tleap')
        self.cwd = os.getcwd()
        try:
            os.mkdir(get_fn('writes'))
        except OSError:
            pass
        os.chdir(get_fn('writes'))

    def tearDown(self):
        try:
            for f in os.listdir(get_fn('writes')):
                os.unlink(get_fn(f, written=True))
            os.rmdir(get_fn('writes'))
        except OSError:
            pass
        os.chdir(self.cwd)

    @skipIf(utils.which('tleap') is None, "Cannot test without tleap")
    def testAmberAminoInternal(self):
        """ Test that the internal AA OFF library writes work with LEaP """
        # First create the parm to test against... we are in "writes" right now
        offlib = AmberOFFLibrary.parse(get_fn('amino12.lib'))
        AmberOFFLibrary.write(offlib, 'testinternal.lib')
        f = open('tleap_orig.in', 'w')
        f.write("""\
source leaprc.ff12SB
l = sequence {ALA ARG ASH ASN ASP CYM CYS CYX GLH GLN GLU GLY HID HIE HIP \
              HYP ILE LEU LYN LYS MET PHE PRO SER THR TRP TYR VAL}
set default PBRadii mbondi2
savePDB l alphabet.pdb
saveAmberParm l alphabet.parm7 alphabet.rst7
quit
""")
        f.close()
        # Now create the leaprc for our new files
        f = open('tleap_new.in', 'w')
        f.write("""\
loadAmberParams parm10.dat
loadAmberParams frcmod.ff12SB
loadOFF testinternal.lib
l = sequence {ALA ARG ASH ASN ASP CYM CYS CYX GLH GLN GLU GLY HID HIE HIP \
              HYP ILE LEU LYN LYS MET PHE PRO SER THR TRP TYR VAL}
savePDB l alphabet2.pdb
saveAmberParm l alphabet2.parm7 alphabet2.rst7
quit
""")
        f.close()
        os.system('tleap -f tleap_orig.in > tleap_orig.out 2>&1')
        os.system('tleap -f tleap_new.in > tleap_new.out 2>&1')
        # Compare the resulting files
        pdb1 = read_PDB('alphabet.pdb')
        pdb2 = read_PDB('alphabet2.pdb')
        parm1 = AmberParm('alphabet.parm7', 'alphabet.rst7')
        parm2 = AmberParm('alphabet2.parm7', 'alphabet2.rst7')
        # Since there are some specific parts of the leaprc that affect default
        # radii, change it here intentionally
        changeRadii(parm1, 'mbondi2').execute()
        changeRadii(parm2, 'mbondi2').execute()
        self._check_corresponding_files(pdb1, pdb2, parm1, parm2)

    @skipIf(utils.which('tleap') is None, "Cannot test without tleap")
    def testAmberAminoTermini(self):
        """ Test that the terminal AA OFF library writes work with LEaP """
        offlib1 = AmberOFFLibrary.parse(get_fn('aminoct12.lib'))
        offlib2 = AmberOFFLibrary.parse(get_fn('aminont12.lib'))
        AmberOFFLibrary.write(offlib1, 'testct.lib')
        AmberOFFLibrary.write(offlib2, 'testnt.lib')
        # Test all pairs a random set of 10 pairs
        keys1 = [random.choice(list(offlib1.keys())) for i in range(10)]
        keys2 = [random.choice(list(offlib2.keys())) for i in range(10)]
        for key1, key2 in zip(keys1, keys2):
            f = open('tleap_orig.in', 'w')
            f.write("""\
source leaprc.ff12SB
l = sequence {%s %s}
savePDB l alphabet.pdb
saveAmberParm l alphabet.parm7 alphabet.rst7
quit
""" % (key1, key2))
            f.close()
            f = open('tleap_new.in', 'w')
            f.write("""\
loadAmberParams parm10.dat
loadAmberParams frcmod.ff12SB
loadOFF testct.lib
loadOFF testnt.lib
l = sequence {%s %s}
savePDB l alphabet2.pdb
saveAmberParm l alphabet2.parm7 alphabet2.rst7
quit
""" % (key1, key2))
            f.close()
            os.system('tleap -f tleap_orig.in > tleap_orig.out 2>&1')
            os.system('tleap -f tleap_new.in > tleap_new.out 2>&1')
            # Compare the resulting files
            pdb1 = read_PDB('alphabet.pdb')
            pdb2 = read_PDB('alphabet2.pdb')
            parm1 = AmberParm('alphabet.parm7', 'alphabet.rst7')
            parm2 = AmberParm('alphabet2.parm7', 'alphabet2.rst7')
            # Since there are some specific parts of the leaprc that affect
            # default radii, change it here intentionally
            changeRadii(parm1, 'mbondi2').execute()
            changeRadii(parm2, 'mbondi2').execute()
            self._check_corresponding_files(pdb1, pdb2, parm1, parm2, False)

    def _check_corresponding_files(self, pdb1, pdb2, parm1, parm2, tree=True):
        self.assertEqual(len(pdb1.atoms), len(pdb2.atoms))
        self.assertEqual(len(parm1.atoms), len(parm2.atoms))
        self.assertEqual(len(parm1.bonds), len(parm2.bonds))
        for a1, a2 in zip(pdb1.atoms, pdb2.atoms):
            self.assertEqual(a1.name, a2.name)
            self.assertEqual(a1.atomic_number, a2.atomic_number)
        for a1, a2 in zip(parm1.atoms, parm2.atoms):
            # Check EVERYTHING
            self.assertIsNot(a1, a2)
            self.assertEqual(a1.name, a2.name)
            self.assertEqual(a1.type, a2.type)
            self.assertEqual(a1.nb_idx, a2.nb_idx)
            self.assertEqual(a1.atomic_number, a2.atomic_number)
            self.assertEqual(a1.atom_type.rmin, a2.atom_type.rmin)
            self.assertEqual(a1.atom_type.epsilon, a2.atom_type.epsilon)
            self.assertEqual(a1.radii, a2.radii)
            self.assertEqual(a1.screen, a2.screen)
            # Ugh. OFF libs are inconsistent
            if tree:
                self.assertEqual(a1.tree, a2.tree)
            self.assertEqual(len(a1.bonds), len(a2.bonds))
            self.assertEqual(len(a1.angles), len(a2.angles))
            self.assertEqual(len(a1.dihedrals), len(a2.dihedrals))
            set1 = set([a.name for a in a1.bond_partners])
            set2 = set([a.name for a in a2.bond_partners])
            self.assertEqual(set1, set2)
            set1 = set([a.name for a in a1.angle_partners])
            set2 = set([a.name for a in a2.angle_partners])
            self.assertEqual(set1, set2)
            set1 = set([a.name for a in a1.dihedral_partners])
            set2 = set([a.name for a in a2.dihedral_partners])
            self.assertEqual(set1, set2)
            # Check residue properties
            self.assertEqual(a1.residue.name, a2.residue.name)

if __name__ == '__main__':
    unittest.main()
