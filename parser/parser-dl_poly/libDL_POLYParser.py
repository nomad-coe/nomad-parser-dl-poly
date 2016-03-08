import os
import sys
import re



KEY_TRANSFORM_SIM_CTRL = {
'simulation_temperature_k' : 'thermostat_T',
'simulation_pressure_katms' : 'barostat_P',
'integration' : 'integrator',
'ensemble' : None,
'thermostat_relaxation_time_ps' : 'thermostat_tau',
'barostat_relaxation_time_ps' : 'barostat_tau',
'selected_number_of_timesteps' : 'n_steps',
'equilibration_period_steps' : 'n_steps_equ',
'temperature_scaling_on_during' : None,
'temperature_scaling_interval' : None,
'equilibration_included_in_overall' : None,
'data_printing_interval_steps' : None,
'statistics_file_interval' : None,
'data_stacking_interval_steps' : None,
'real_space_cutoff_angs' : 'rc_angs',
'vdw_cutoff_angs' : 'rc_vdw_angs',
'electrostatics' : None,
'ewald_sum_precision' : None,
'ewald_convergence_parameter_a^-1' : None,
'extended_coulombic_exclusion' : None,
'cutoff_padding_reset_to_angs' : None,
'vdw_cutoff_reset_to_angs' : None,
'fixed_simulation_timestep_ps' : None,
'data_dumping_interval_steps' : None,
'allocated_job_run_time_s' : None,
'allocated_job_close_time_s' : None
}

KEY_TRANSFORM_SYS_SPEC = {
'energy_units' : 'energy_units',
'number_of_molecular_types' : 'n_molecular_types'
}       


class FileStream(object):
    def __init__(self, filename=None):
        if filename:
            self.ifs = open(filename, 'r')
        else:
            self.ifs = None
    def SkipTo(self, expr):
        while True:
            ln = self.ifs.readline()
            if expr in ln:
                break
        return ln
    def SkipToMatch(self, expr):
        while True:            
            ln = self.ifs.readline()
            m = re.search(expr, ln)
            if m:
                return ln
            if self.all_read(): break
        return None
    def GetBlock(self, expr1, expr2):
        inside = False
        outside = False
        block = ''
        block_stream = BlockStream()
        while True:
            last_pos = self.ifs.tell()
            ln = self.ifs.readline()
            if expr1 in ln: inside = True
            if expr2 in ln: outside = True
            if inside and not outside:
                # Inside the block
                block += ln
                block_stream.append(ln)
            elif inside and outside:
                self.ifs.seek(last_pos)
                # Block finished
                break
            else:
                # Block not started yet
                pass
            if self.all_read(): break
        return block_stream  
    def GetBlockSequence(self, 
            expr_start, 
            expr_new, 
            expr_end, 
            remove_eol=True, 
            skip_empty=True):
        inside = False
        outside = False
        # Setup dictionary to collect blocks
        blocks = { expr_start : [] }
        for e in expr_new:
            blocks[e] = []
        # Assume structure like this (i <> inside, o <> outside)
        # Lines with 'i' get "eaten"
        # """
        # o ...
        # i <expr_start>
        # i ...
        # i <expr_new[1]>
        # i ...
        # i <expr_new[0]>
        # i ...
        # o <expr_end>
        # o ...
        # """
        key = None
        while True:
            # Log line position
            last_pos = self.ifs.tell()
            ln = self.ifs.readline()            
            # Figure out where we are
            if not inside and expr_start in ln:
                #print "Enter", expr_start
                inside = True
                key = expr_start
                new_block = BlockStream(key)
                blocks[key].append(new_block)
            for expr in expr_new:
                if inside and expr in ln:
                    #print "Enter", expr
                    key = expr
                    new_block = BlockStream(key)
                    blocks[key].append(new_block)
            if inside and expr_end != None and expr_end in ln:
                outside = True
            if inside and not outside:
                # Inside a block
                if remove_eol: ln = ln.replace('\n', '')
                if skip_empty and ln == '': pass
                else: blocks[key][-1].append(ln)
            elif inside and outside:
                # All blocks finished
                self.ifs.seek(last_pos)
                break
            else:
                # No blocks started yet
                pass
            if self.all_read(): break
        return blocks
    def all_read(self):
        return self.ifs.tell() == os.fstat(self.ifs.fileno()).st_size
    def readline(self):
        return ifs.readline()
    def nextline(self):
        while True:
            ln = self.ifs.readline()
            if ln.strip() != '':
                return ln
            else: pass
            if self.all_read(): break
        return ln
    def ln(self):
        return self.nextline()
    def sp(self):
        return self.ln().split()
    def skip(self, n):
        for i in range(n):
            self.ln()
        return
    
class BlockStream(FileStream):
    def __init__(self, label=None):
        super(BlockStream, self).__init__(None)
        self.ifs = self
        self.lns = []
        self.idx = 0
        self.label = label
    def append(self, ln):
        self.lns.append(ln)
    def readline(self):
        if self.all_read():
            return ''        
        ln = self.lns[self.idx]
        self.idx += 1
        return ln
    def all_read(self):
        return self.idx > len(self.lns)-1
    def tell(self):
        return self.idx
    def cat(self, remove_eol=True, add_eol=False):
        cat = ''
        for ln in self.lns:
            if remove_eol:
                cat += ln.replace('\n', '')
            elif add_eol:
                cat += ln+'\n'
            else:
                cat += ln
        return cat


class DlPolyParser(object):
    def __init__(self, log=None):
        self.output_file = 'OUTPUT'
        self.log = log
        self.data = {}
        self.topology = None
        self.logtag = 'sim'
        
        self.missing_keys_lh = [] # Transform keys that were not found in output
        self.missing_keys_rh = []
        self.ignored_keys = [] # Raw keys that did not have a transform
        self.keys_not_found = [] # Searches that failed
        return
    def SummarizeKeyDefaults(self):
        if not self.log: return
        if len(self.missing_keys_lh):
            self.log << self.log.my \
                << "[%s] Keys from transformation maps that went unused (=> set to 'None'):" \
                % self.logtag << self.log.endl
            for lh, rh in zip(self.missing_keys_lh, self.missing_keys_rh):
                self.log << self.log.item << "Key = %-25s <> %25s" % (rh, lh) << self.log.endl
        if len(self.ignored_keys):
            self.log << self.log.mb \
                << "[%s] Keys from XY mapping that were not transformed (=> not stored):" \
                % self.logtag << self.log.endl
            for key in self.ignored_keys:
                self.log << self.log.item << "Key =" << key << self.log.endl
        if len(self.keys_not_found):
            self.log << self.log.mr \
                << "[%s] Keys from searches that failed (=> set to 'None'):" \
                % self.logtag << self.log.endl
            for key in self.keys_not_found:
                self.log << self.log.item << "Key =" << key << self.log.endl
        return
    def Set(self, key, value):
        if self.log:
            self.log << "Set [%s]   %-40s = %s" % (self.logtag, key, str(value)) << self.log.endl
        if not self.data.has_key(key):
            self.data[key] = value
        else:
            raise KeyError("Key already exists: '%s'" % key)
        return
    def SearchMapKeys(self, expr, ln, keys):
        s = re.search(expr, ln)
        try:
            for i in range(len(keys)):
                self.Set(keys[i], s.group(i+1).strip())
        except AttributeError:
            for i in range(len(keys)):
                self.Set(keys[i], None)
                self.keys_not_found.append(keys[i])
        return
    def ReadBlockXy(self, block):
        lns = block.lns
        block_data = {}
        for ln in lns:
            ln = ln.replace('\n','')
            if ln == '':
                continue
            if ':' in ln:
                sp = ln.split(':')
                x = sp[0].strip().split()
                y = sp[1].strip()
            elif '=' in ln:
                sp = ln.split('=')
                x = sp[0].strip().split()
                y = sp[1].strip()
            else:
                sp = ln.split()
                x = sp[:-1]
                y = sp[-1]
            key = ''
            for i in range(len(x)-1):                
                xi = x[i].replace('(','').replace(')','').lower()
                key += '%s_' % xi
            key += '%s' % x[-1].replace('(','').replace(')','').lower()
            value = y
            block_data[key] = value
        return block_data
    def ApplyBlockXyData(self, block_data, key_map):
        for key_in in key_map:
            key_out = key_map[key_in]            
            if not block_data.has_key(key_in):
                # Missing key in output
                self.missing_keys_lh.append(key_in)
                self.missing_keys_rh.append(key_out)
                value = None
            else:
                value = block_data[key_in]
            if key_out == None:
                key_out = key_in
            self.Set(key_out, value)
        for key in block_data:
            if not key_map.has_key(key):
                # Missing key in transform map
                self.ignored_keys.append(key)
        return
    def ParseOutput(self, output_file):        
        if self.log: 
            self.log << self.log.endl << self.log.endl
            self.log << "DlPolyParser::ParseOutput" << self.log.endl
            self.log << self.log.mg << "Start simulation method ..." << self.log.endl
        
        ifs = FileStream(output_file)
        
        # HEADER & NODE STRUCTURE
        ln = ifs.SkipTo('** DL_POLY **')
        self.SearchMapKeys('version:\s*(\d+.\d+)\s*/\s*(\w+\s*\d+)', ifs.ln(), ['version', 'version_date'])
        self.SearchMapKeys('execution on\s*(\d+)\s*node', ifs.ln(), ['n_nodes'])
        ln = ifs.SkipTo('node/domain decomposition')
        self.Set('domain_decomposition', map(int, ln.split()[-3:]))
        
        # SIMULATION TITLE
        ln = ifs.SkipToMatch('^\s+\*+$')
        ifs.skip(2)
        self.SearchMapKeys('\*+\s([\w+\s\(\)]*)\s\*+', ifs.ln(), ['title'])
        
        # SIMULATION CONTROL PARAMETERS
        block = ifs.GetBlock('SIMULATION CONTROL PARAMETERS', 'SYSTEM SPECIFICATION')        
        block_data = self.ReadBlockXy(block)
        self.ApplyBlockXyData(block_data, KEY_TRANSFORM_SIM_CTRL)        
        
        # TOPOLOGY
        expr_start = 'SYSTEM SPECIFICATION'
        expr_molecule = 'molecular species type'
        expr_config = 'configuration file name'
        expr_vdw = 'number of specified vdw potentials'
        expr_new = [ expr_molecule, expr_vdw, expr_config ]
        expr_end = 'all reading and connectivity checks DONE'
        blocks = ifs.GetBlockSequence(expr_start, expr_new, expr_end)
        # Sanity checks ...
        assert len(blocks[expr_vdw]) == len(blocks[expr_start]) == len(blocks[expr_config]) == 1
        assert len(blocks[expr_molecule]) >= 1
        block_sys_spec = blocks[expr_start][0]
        block_config = blocks[expr_config][0]
        block_molecules = blocks[expr_molecule]
        block_vdw = blocks[expr_vdw][0]
        # Generate ...  
        self.topology = DlPolyTopology(block_sys_spec, block_config, block_molecules, block_vdw, self)
        
        
        self.SummarizeKeyDefaults()
        self.topology.SummarizeKeyDefaults()
        self.log.okquit()
        
        return

        
class DlPolyTopology(DlPolyParser):
    def __init__(self, block_sys_spec, block_config, block_mols, block_vdw, parser):
        super(DlPolyTopology, self).__init__(parser.log)
        self.logtag = 'top'
        
        if self.log: self.log << self.log.mg << "Start topology ..." << self.log.endl
        
        # Meta specification (energy values, # molecular types)
        sys_spec = parser.ReadBlockXy(block_sys_spec)
        self.ApplyBlockXyData(sys_spec, KEY_TRANSFORM_SYS_SPEC)
        
        # Config specification (config-file name/title, box vectors, box volume)
        config_str = block_config.cat(remove_eol=False, add_eol=True)
        self.SearchMapKeys('configuration file name:\s([\w+\s\(\)]*)\s\n', config_str, ['config_file_name'])
        self.SearchMapKeys('selected image convention\s*(\d+)\s*\n', config_str, ['image_convention'])
        triple_str='\s*([0-9a-zA-Z_.]*)'*3+'\n'
        search_str = 'simulation cell vectors\s*\n' + 3*triple_str
        self.SearchMapKeys(search_str, config_str, ['box_ax', 'box_ay', 'box_az', 'box_bx', 'box_by', 'box_bz', 'box_cx', 'box_cy', 'box_cz'])
        self.SearchMapKeys('system volume\s*([-+0-9.eEdD]*)\s*\n', config_str, ['box_volume'])
        
        self.molecules = []
        # Molecule specification
        for block_mol in block_mols:
            if self.log: self.log << self.log.mg << "Start molecule ..." << self.log.endl
            new_mol = DlPolyMolecule(block_mol, self)
            
        return


KEY_TRANSFORM_MOL_GLOBAL = {
'molecular_species_type' : 'molecule_type_id',
'name_of_species' : 'molecule_type_name',
'number_of_molecules' : 'n_instances_molecule_type'
}

class DlPolyMolecule(DlPolyParser):
    def __init__(self, mol_stream, parser):
        super(DlPolyMolecule, self).__init__(parser.log)
        self.logtag = 'mol'
        
        # PARTITION ONTO BLOCKS
        expr_global = 'molecular species type'
        expr_atoms = 'number of atoms/sites'
        expr_bonds = 'number of bonds'
        expr_bond_constraints = 'number of bond constraints'
        expr_angles = 'number of bond angles'
        expr_dihedrals = 'number of dihedral angles'
        expr_inv_angles = 'number of inversion angles'        
        expr_start = expr_global
        expr_new = [ expr_atoms, expr_bonds, expr_bond_constraints, expr_angles, expr_dihedrals, expr_inv_angles ]
        expr_end = None        
        blocks = mol_stream.GetBlockSequence(expr_start, expr_new, expr_end)
        # Sanity checks ...
        for key in expr_new:
            assert len(blocks[key]) <= 1
        assert len(blocks[expr_atoms]) == 1
        
        # PARSE GLOBAL
        block = blocks[expr_global][0]
        block_data = self.ReadBlockXy(block)
        self.ApplyBlockXyData(block_data, KEY_TRANSFORM_MOL_GLOBAL)
        
        # PARSE ATOMS
        block = blocks[expr_atoms][0]
        while not block.all_read():
            print block.ln()
        
        return
        
        
        
        
        
        
        
