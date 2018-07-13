# Copyright 2016-2018 Carl Poelking, Fawzi Mohamed, Ankit Kariryaa
# 
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

from __future__ import print_function
from builtins import zip
from builtins import str
from builtins import map
from builtins import range
from builtins import object
import os
import sys
import re
import numpy as np

# TODO Distinguish: number_of_steps vs number_of_steps_equilibration
# TODO Check units and install conversions
# TODO - Pressure
# TODO Check sampling_method

UNITCONV_DLPOLY_TO_SI = {
'time' : 1e-12, # ps to s
'length' : 1e-10, # AA to m
'mass' : 1.6605402e-27, # u to kg
'charge' : 1.6021733e-19, # e to C
'energy' : 1.6605402e-23, # 10*J/mol to J
'pressure' : 1.6605402e+7, # 163.88 atm to Pa
'pressure_katm' : 1.01325000e+8, # katm to Pa
'temperature' : 1. # K to K
}

UNITCONV_DLPOLY_CUSTOM_TO_SI = {
'energy_kj_mol' : 1.6605402e-21, # kJ/mol to J
'energy_kj'    : 1.6605402e-21, # kJ/mol to J
'energy_ev' : 1.6021733e-19, # eV to J
'energy_kcal_mol' : 4.184*1.6605402e-21, # kcal/mol to J
'energy_kcal'    : 4.184*1.6605402e-21, # kcal/mol to J
'energy_kelvin_boltzmann' : None,
'energy_k'               : None,
'energy_dl_polyinternalunits_10j_mol' : 1.6605402e-23 # 10*J/mol to J
}

# =================
# TRANSLATION RULES
# =================

KEY_TRANSFORM_SIM_CTRL = {
'simulation_temperature_k' : 'x_dl_poly_thermostat_target_temperature',
'simulation_pressure_katms' : 'x_dl_poly_barostat_target_pressure',
'integration' : 'x_dl_poly_integrator_type',
'ensemble' : 'ensemble_type',
'thermostat_relaxation_time_ps' : 'x_dl_poly_thermostat_tau',
'barostat_relaxation_time_ps' : 'x_dl_poly_barostat_tau',
'selected_number_of_timesteps' : 'x_dl_poly_number_of_steps_requested',
'equilibration_period_steps' : 'number_of_steps_equil_requested',
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
'fixed_simulation_timestep_ps' : 'x_dl_poly_integrator_dt',
'data_dumping_interval_steps' : None,
'allocated_job_run_time_s' : None,
'allocated_job_close_time_s' : None
}

KEY_TRANSFORM_SYS_SPEC = {
'energy_units' : 'energy_units',
'number_of_molecular_types' : 'n_molecular_types'
}

KEY_TRANSFORM_MOL_GLOBAL = {
'molecular_species_type' : 'molecule_type_id',
'name_of_species' : 'molecule_type_name',
'number_of_molecules' : 'number_of_molecules'
}

KEY_RULES_CONTROLS = {
'ensemble' :    lambda l: [ s.lower() for s in l[1:] ],
'temperature' : lambda l: l[-1],
'pressure' :    lambda l: l[-1],
'timestep' :    lambda l: l[-1],
'steps':        lambda l: l[-1],
'equilibration':lambda l: l[-1],
'cutoff':       lambda l: l[-1]
}

KEY_RULES_CONTROLS_EXPAND_KEY = {
'ensemble':'ensemble',
'temp':'temperature',
'temperature':'temperature',
'pres':'pressure',
'pressure':'pressure',
'timestep':'timestep',
'steps':'steps',
'equilibration':'equilibration',
'equil':'equilibration',
'cut':'cutoff',
'rcut':'cutoff',
'cutoff':'cutoff'
}


# ===================
# FILE & BLOCK STREAM
# ===================

class FileStream(object):
    def __init__(self, filename=None):
        if filename:
            self.ifs = open(filename, 'r')
        else:
            self.ifs = None
        return
    def SkipTo(self, expr):
        while True:
            ln = self.ifs.readline()
            if expr in ln:
                break
            if self.all_read():
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
    def close(self):
        self.ifs.close()
    def nextline(self):
        while True:
            ln = self.ifs.readline().replace('\n','').strip()
            if ln != '':
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

# ================
# DLPOLY TERMINALS
# ================

class DlPolyParser(object):
    def __init__(self, log=None):
        self.output_file = 'OUTPUT'
        self.log = log
        self.data = {}
        self.topology = None
        self.logtag = 'sim'
        # KEY DEFAULT DICTIONARIES
        self.missing_keys_lh = [] # Transform keys that were not found in output
        self.missing_keys_rh = []
        self.ignored_keys = [] # Raw keys that did not have a transform
        self.keys_not_found = [] # Searches that failed
        # STORES TIME/STEP VARIABLES (ENERGY, ...)
        self.step_data = {}
        self.time_data = {}
        return
    def __getitem__(self, key):
        self.selected_data_item = self.data[key]
        return self
    def As(self, typ=None):
        if typ == None:
            typ = type(self.selected_data_item)
        return typ(self.selected_data_item)
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
        if key not in self.data:
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
            if key_in not in block_data:
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
            if key not in key_map:
                # Missing key in transform map
                self.ignored_keys.append(key)
        return
    def ParseOutput(self, output_file):        
        if self.log: 
            self.log << self.log.mg << "Start simulation method ..." << self.log.endl
        
        ifs = FileStream(output_file)
        self.Set('program_name', 'DL_POLY')
        self.Set('sampling_method', 'molecular_dynamics')
        
        # HEADER & NODE STRUCTURE
        ln = ifs.SkipTo('** DL_POLY **')
        self.SearchMapKeys('version:\s*(\d+.\d+)\s*/\s*(\w+\s*\d+)', ifs.ln(), ['program_version', 'program_version_date'])
        self.SearchMapKeys('execution on\s*(\d+)\s*node', ifs.ln(), ['n_nodes'])
        ln = ifs.SkipTo('node/domain decomposition')
        self.Set('domain_decomposition', list(map(int, ln.split()[-3:])))
        
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
        expr_total = 'total number of molecules'
        expr_new = [ expr_molecule, expr_vdw, expr_config, expr_total ]
        expr_end = 'all reading and connectivity checks DONE'
        blocks = ifs.GetBlockSequence(expr_start, expr_new, expr_end)
        # Sanity checks ...
        assert len(blocks[expr_vdw]) == len(blocks[expr_start]) == len(blocks[expr_config]) == 1
        assert len(blocks[expr_molecule]) >= 1
        assert len(blocks[expr_total]) == 1
        block_sys_spec = blocks[expr_start][0]
        block_config = blocks[expr_config][0]
        block_molecules = blocks[expr_molecule]
        block_vdw = blocks[expr_vdw][0]
        # Generate ...  
        self.topology = DlPolyTopology(block_sys_spec, block_config, block_molecules, block_vdw, self)        

        # RUNTIME SYSTEM PROPS: ENERGIES, PRESSURE, ...
        block = ifs.GetBlock('step     eng_tot', 'elapsed cpu time')
        step_start_new = False
        have_step = False
        have_time = False
        step_dict_list = {}
        time_dict_list = {}
        while not block.all_read():
            ln = block.ln()
            if '---------------' in ln:
                step_start_new = True
                continue
            if 'step' in ln:
                block.ln()
                block.ln()
                continue
            sp = ln.split()
            if sp == []: continue
            if step_start_new:
                # step eng_tot ...
                step_dict = {}
                step_nr = int(sp[0])
                step_dict['eng_tot'] = float(sp[1])
                step_dict_list[step_nr] = step_dict
                step_start_new = False
                # time ...
                ln = block.ln()
                sp = ln.split()
                time = float(sp[0])
                time_dict = {}
                time_dict['eng_tot'] = step_dict['eng_tot']
                time_dict_list[time] = time_dict
            else:
                pass
        self.step_data = step_dict_list
        self.time_data = time_dict_list
        #for item in step_dict_list:
        #    print("STEP", item, step_dict_list[item])
        #for item in time_dict_list:
        #    print("TIME", item, time_dict_list[item])
        ifs.close()
        return


class DlPolyControls(DlPolyParser):
    def __init__(self, log=None):
        super(DlPolyControls, self).__init__(log)
        self.logtag = 'ctr'
        return
    def ParseControls(self, ctrl_file):
        if self.log: 
            self.log << self.log.mg << "Start controls ..." << self.log.endl        
        ifs = FileStream(ctrl_file)
        while not ifs.all_read():
            ln = ifs.ln()
            if ln == '' or ln[0:1] == '#': continue
            sp = ln.split()
            key = sp[0]
            try:
                key_long = KEY_RULES_CONTROLS_EXPAND_KEY[key]
                self.Set(key_long, KEY_RULES_CONTROLS[key_long](sp))
            except KeyError:
                self.ignored_keys.append(key)
                pass
        ifs.close()
        return
        

class DlPolyFrame(DlPolyParser):
    def __init__(self, log=None):
        super(DlPolyFrame, self).__init__(log)
        self.atoms = []
        self.has_velocities = False
        self.has_forces = False
        self.has_energy_total = False
        self.energy_total = None
        self.position_matrix = None
        self.pbc_booleans = None
        self.box_matrix = np.zeros((3,3))
    def ParseAtoms(self, ifs, n_atoms, log_level):
        # Log level
        if log_level > 0:
            self.has_velocities = True
            if log_level > 1:
                self.has_forces = True
        # Create atoms
        for i in range(n_atoms):
            atom_name, atom_id = tuple(ifs.ln().split()[0:2]) # This leaves out weight, charge, rsd
            xyz = [float(x) for x in ifs.ln().split()]
            records = [atom_name, atom_id, xyz]
            record_labels = ['atom_name', 'atom_id', 'xyz']
            if log_level > 0:
                vel = [float(x) for x in ifs.ln().split()]
                records.append(vel)
                record_labels.append('vel')
                if log_level > 1:
                    force = [float(x) for x in ifs.ln().split()]
                    records.append(force)
                    record_labels.append('force')
            new_atom = DlPolyAtom(records, record_labels, self)
            self.atoms.append(new_atom)
        assert len(self.atoms) == n_atoms 
        # Position matrix
        self.position_matrix = np.zeros((n_atoms, 3))
        for i in range(n_atoms):
            self.position_matrix[i] = np.array(self.atoms[i]['xyz'].As())
        # Velocity matrix
        if self.has_velocities:
            self.velocity_matrix = np.zeros((n_atoms, 3))
            for i in range(n_atoms):
                self.velocity_matrix[i] = np.array(self.atoms[i]['vel'].As())
        if self.has_forces:
            self.force_matrix = np.zeros((n_atoms, 3))
            for i in range(n_atoms):
                self.force_matrix[i] = np.array(self.atoms[i]['force'].As())
        return
    def ParseBox(self, ifs, pbc_type):
        # PBC booleans
        if pbc_type == 6:
            self.pbc_booleans = np.array([ True, True, False ])
        elif pbc_type > 0:
            self.pbc_booleans = np.array([ True, True, True ])
        else:
            self.pbc_booleans = np.array([ False, False, False ])
        # Box
        if pbc_type > 0:
            a = [float(x) for x in ifs.ln().split()]
            b = [float(x) for x in ifs.ln().split()]
            c = [float(x) for x in ifs.ln().split()]
            self.Set('box_a', a)
            self.Set('box_b', b)
            self.Set('box_c', c)
            # Box matrix
            # ATTENTION First index: x,y,z; second index: a,b,c
            for i in range(3):
                self.box_matrix[i][0] = a[i]
                self.box_matrix[i][1] = b[i]
                self.box_matrix[i][2] = c[i]  
        return
    def ParseFrame(self, ifs, step_data, time_data):
        ln = ifs.ln()
        directives = ln.split()
        #print(directives)
        assert 'timestep' == directives[0]
        # Frame meta-info
        self.Set('timestep', directives[1])
        self.Set('n_atoms', directives[2])
        self.Set('log_level', directives[3])
        self.Set('pbc_type', directives[4])
        self.Set('dt', directives[5])
        self.Set('time_value', self['timestep'].As(int)*self['dt'].As(float))
        n_atoms = self['n_atoms'].As(int)
        pbc_type = self['pbc_type'].As(int)
        # Look-up trajectory data
        step = self['timestep'].As(int)
        if step in step_data:
            if 'eng_tot' in step_data[step]:
                self.has_energy_total = True
                self.energy_total = step_data[step]['eng_tot']
        # Logging level
        log_level = self['log_level'].As(int)
        # Box
        self.ParseBox(ifs, pbc_type)
        # Atoms
        self.ParseAtoms(ifs, n_atoms, log_level)
        return
        

class DlPolyTrajectory(DlPolyParser):
    def __init__(self, log=None):
        super(DlPolyTrajectory, self).__init__(log)
        self.logtag = 'trj'
        self.frames = [] # List of DlPolyFrame's        
    def ParseTrajectory(self, trj_file, step_data, time_data):
        if self.log:
            self.log << self.log.mg << "Start trajectory ..." << self.log.endl
        if not os.path.isfile(trj_file):
            trj_file = '__nofile__'
            pass
        else:
            ifs = FileStream(trj_file)
            title = ifs.ln().replace('\n','').strip()
            # Title
            self.Set('title', title)
            # Directives: logging, pbc
            directives = ifs.ln().split()
            self.Set('log_level', directives[0])
            self.Set('pbc_type', directives[1])
            # Frames
            while not ifs.all_read():
                new_frame = DlPolyFrame(self.log)
                new_frame.ParseFrame(ifs, step_data, time_data)
                self.frames.append(new_frame)
        if self.log:
            self.log << "Read %d frames from %s" % (len(self.frames), trj_file) << self.log.endl
        return


class DlPolyConfig(DlPolyFrame):
    def __init__(self, log=None):
        DlPolyFrame.__init__(self, log)        
        #super(DlPolyConfig, self).__init__(log)
        self.logtag = 'cfg'
        return
    def ParseConfig(self, trj_file):
        if self.log:
            self.log << self.log.mg << "Start configuration ..." << self.log.endl
        ifs = FileStream(trj_file)
        # Title
        title = ifs.ln().replace('\n','').strip()
        self.Set('title', title)
        self.Set('time_value', 0.)
        # Directives: logging, pbc
        directives = ifs.ln().split()
        self.Set('log_level', directives[0]) # 0 -> 1 -> 2: coords -> + vel. -> + forces
        self.Set('pbc_type', directives[1])  # 0 / ... / 6: no / cubic / orthorhom. / par.-epiped / xy
        self.Set('n_atoms', directives[2])
        n_atoms = self['n_atoms'].As(int)
        pbc_type = self['pbc_type'].As(int)
        # Logging level
        log_level = self['log_level'].As(int)
        # Box
        self.ParseBox(ifs, pbc_type)
        # Atom records
        self.ParseAtoms(ifs, n_atoms, log_level)
        return

# =======================
# DLPOLY TOPOLOGY OBJECTS
# =======================

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
        
        # Molecule specification
        self.molecules = []
        for block_mol in block_mols:
            if self.log: self.log << self.log.mg << "Start molecule ..." << self.log.endl
            new_mol = DlPolyMolecule(block_mol, self)
            self.molecules.append(new_mol)
        
        n_atoms_total = 0
        n_molecules_total = 0
        for mol in self.molecules:
            n_mol = mol['number_of_molecules'].As(int)
            n_atoms = mol['number_of_atoms_in_molecule'].As(int)
            n_atoms_total += n_mol*n_atoms
            n_molecules_total += n_mol
        self.Set('number_of_topology_atoms', n_atoms_total)
        self.Set('number_of_topology_molecules', n_molecules_total)
        return


class DlPolyMolecule(DlPolyParser):
    def __init__(self, mol_stream, parser):
        super(DlPolyMolecule, self).__init__(parser.log)
        self.logtag = 'mol'
        self.atoms = []
        
        # PARTITION ONTO BLOCKS
        expr_global = 'molecular species type'
        # Atoms ...
        expr_atoms = 'number of atoms/sites'
        # Interactions ...
        expr_bonds = 'number of bonds'
        expr_bond_constraints = 'number of bond constraints'
        expr_angles = 'number of bond angles'
        expr_dihedrals = 'number of dihedral angles'
        expr_inv_angles = 'number of inversion angles'
        # Block definitions ...
        expr_start = expr_global
        expr_new = [ expr_atoms, expr_bonds, expr_bond_constraints, expr_angles, expr_dihedrals, expr_inv_angles ]
        expr_end = None        
        blocks = mol_stream.GetBlockSequence(expr_start, expr_new, expr_end)
        # Sanity checks ...
        for key in expr_new:
            assert len(blocks[key]) <= 1
        assert len(blocks[expr_atoms]) == 1
        
        # PARSE GLOBALS
        block = blocks[expr_global][0]
        block_data = self.ReadBlockXy(block)
        self.ApplyBlockXyData(block_data, KEY_TRANSFORM_MOL_GLOBAL)
        
        # PARSE ATOMS
        if self.log: self.log << self.log.mg << "Start atoms ..." << self.log.endl
        block = blocks[expr_atoms][0]
        n_atoms = int(block.ln().split()[-1])
        self.Set('number_of_atoms_in_molecule', n_atoms)
        assert 'atomic characteristics' in block.ln()
        # Determine atom properties        
        atom_property_labels = block.ln().split()
        assert atom_property_labels[0] == 'site'
        atom_property_labels[0] = 'id'
        atom_property_labels = [ 'atom_%s' % l.lower() for l in atom_property_labels ]
        atom_count = 0
        # Read atom lines & create atoms
        while not block.all_read():
            atom_properties = block.ln().split()
            new_atom = DlPolyAtom(atom_properties, atom_property_labels, parser)
            self.atoms.append(new_atom)
            # Atom may repeat - make these repititions explicit
            atom_id = new_atom['atom_id'].As(int)
            atom_repeat = new_atom['atom_repeat'].As(int)
            for i in range(atom_repeat-1):
                next_id = atom_id+i+1
                assert int(atom_properties[0]) == next_id-1
                atom_properties[0] = atom_id+i+1
                new_atom = DlPolyAtom(atom_properties, atom_property_labels, parser)
                self.atoms.append(new_atom)
            # Keep track of total count
            atom_count += atom_repeat
            assert atom_count <= n_atoms
            if atom_count == n_atoms:
                break
        assert atom_count == n_atoms
        
        atom_charges = [ atom['atom_charge'].As(float) for atom in self.atoms ]
        atom_names = [ atom['atom_name'].As() for atom in self.atoms ]
        self.Set('atom_in_molecule_charge', atom_charges)
        self.Set('atom_in_molecule_name', atom_names)
        
        # TODO Parse interactions
        return


class DlPolyAtom(DlPolyParser):
    def __init__(self, atom_properties, atom_property_labels, parser):
        super(DlPolyAtom, self).__init__(parser.log)
        if self.log and not self.log.debug: self.log = None
        self.logtag = 'atm'
        for value, label in zip(atom_properties, atom_property_labels):
            self.Set(label, value)
        return
        
        
        

