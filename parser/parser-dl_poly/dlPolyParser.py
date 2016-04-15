import os
import sys
import re
import json
import logging
import setup_paths
import numpy as np

from nomadcore.local_meta_info import loadJsonFile, InfoKindEl
from nomadcore.parser_backend import JsonParseEventsWriterBackend
from contextlib import contextmanager

from libDlPolyParser import *

try:
    from libMomo import osio, endl, flush
    osio.ConnectToFile('parser.osio.log')
    green = osio.mg
except:
    osio = endl = flush = None
    green = None
    

parser_info = {
    "name": "parser-dl-poly", 
    "version": "0.0",
    "json": "../../../../nomad-meta-info/meta_info/nomad_meta_info/dl_poly.nomadmetainfo.json"
}

# LOGGING
def log(msg, highlight=None, enter=endl):
    if osio:
        if highlight==None: hightlight = osio.ww
        osio << highlight << msg << enter
    return

# CONTEXT GUARD
@contextmanager
def open_section(p, name):
    gid = p.openSection(name)
    yield gid
    p.closeSection(name, gid)   

def push(jbe, terminal, key1, fct=lambda x: x.As(), key2=None):
    if key2 == None: key2 = key1
    value =  fct(terminal[key2])
    jbe.addValue(key1, value)
    return value

def push_array(jbe, terminal, key1, key2=None):
    if key2 == None: key2 = key1
    value =  np.asarray(terminal[key2])
    jbe.addValue(key1, value)
    return value

def push_value(jbe, value, key):
    jbe.addValue(key, value)
    return value

def push_array_values(jbe, value, key):
    jbe.addArrayValues(key, value)
    return value

def parse(output_file_name):
    jbe = JsonParseEventsWriterBackend(meta_info_env)
    jbe.startedParsingSession(output_file_name, parser_info)
    
    base_dir = os.path.dirname(os.path.abspath(output_file_name))
    # PARSE CONTROLS ...
    ctrl_file_name = os.path.join(base_dir, 'CONTROL')
    terminal_ctrls = DlPolyControls(osio)
    terminal_ctrls.ParseControls(ctrl_file_name)    
    # PARSE OUTPUT / TOPOLOGY ...
    terminal = DlPolyParser(osio)
    terminal.ParseOutput(output_file_name)    
    # PARSE TRAJECTORY ...
    cfg_file_name = os.path.join(base_dir, 'CONFIG')
    terminal_trj = DlPolyConfig(osio)
    terminal_trj.ParseConfig(cfg_file_name)
    # SUMMARIZE KEY-TABLE DEFAULTS ...
    terminal.SummarizeKeyDefaults()
    terminal.topology.SummarizeKeyDefaults()
    terminal_ctrls.SummarizeKeyDefaults()
    terminal_trj.SummarizeKeyDefaults()
    # ABBREVIATE ...
    ctr = terminal_ctrls
    out = terminal
    top = terminal.topology
    trj = terminal_trj
    
    ofs = open('parser.keys.log', 'w')
    terminals = [ctr, out, top, trj]
    for t in terminals:
        keys = sorted(t.data.keys())
        for key in keys:
            ofs.write('[%s] %s\n' % (t.logtag, key))
        ofs.write('\n')
    ofs.close()
    
    # PUSH TO BACKEND
    with open_section(jbe, 'section_run') as gid_run:
        push(jbe, out, 'program_name')
        push(jbe, out, 'program_version')
        #push(jbe, out, 'program_info', key2='program_version_date')
        
        # TOPOLOGY SECTION
        with open_section(jbe, 'section_topology') as gid_top:
            # Cross-referencing is done on-the-fly (as gid's become available)
            # a) <molecule_to_molecule_type> :         shape=(number_of_topology_molecules, [<gid>])
            # b) <atom_in_molecule_to_atom_type_ref> : shape=(number_of_atoms_in_molecule, [<gid>])
            # c) <atom_to_molecule> :                  shape=(number_of_topology_atoms, [<molidx>, <atomidx>])
            push(jbe, top, 'number_of_topology_molecules', lambda s: s.As(int))
            push(jbe, top, 'number_of_topology_atoms', lambda s: s.As(int))            
            # Atom types
            mol_type_atom_type_id_to_atom_type_gid = {}
            for mol in top.molecules:
                mol_name = mol['molecule_type_name'].As()
                mol_type_atom_type_id_to_atom_type_gid[mol_name] = {}
                for atom in mol.atoms:
                    # Add type
                    with open_section(jbe, 'section_atom_type') as gid_atom:
                        atom_id = atom['atom_id'].As(int)
                        mol_type_atom_type_id_to_atom_type_gid[mol_name][atom_id] = gid_atom
                        push(jbe, atom, 'atom_type_name', lambda s: s.As(), 'atom_name')
                        push(jbe, atom, 'atom_type_mass', lambda s: s.As(float), 'atom_mass')
                        push(jbe, atom, 'atom_type_charge', lambda s: s.As(float), 'atom_charge')           
            # Molecule types
            molecule_type_name_to_type_gid = {}
            for mol in top.molecules:
                mol_name = mol['molecule_type_name'].As()
                # Extract references of atoms to atom types
                atom_type_id_to_atom_type_gid = mol_type_atom_type_id_to_atom_type_gid[mol_name]
                atom_gid_list = []
                for atom in mol.atoms:
                    atom_id = atom['atom_id'].As(int)
                    atom_gid_list.append(atom_type_id_to_atom_type_gid[atom_id])
                # Add molecule                    
                with open_section(jbe, 'section_molecule_type') as gid_mol:
                    molecule_type_name_to_type_gid[mol['molecule_type_name'].As()] = gid_mol
                    push(jbe, mol, 'molecule_type_name')
                    push(jbe, mol, 'number_of_atoms_in_molecule', lambda s: s.As(int))
                    #push_array(jbe, mol, 'atom_in_molecule_name') #TODO
                    push_array_values(jbe, np.asarray(mol['atom_in_molecule_name']), 'atom_in_molecule_name')
                    #push_array(jbe, mol, 'atom_in_molecule_charge') # TODO
                    push_array_values(jbe, np.asarray(atom_gid_list), 'atom_in_molecule_to_atom_type_ref') #TODO
            # Global molecule type map
            molecule_to_molecule_type = []
            for mol in top.molecules:
                type_name_this_mol = mol['molecule_type_name'].As()
                type_gid_this_mol = molecule_type_name_to_type_gid[type_name_this_mol]
                n_this_mol = mol['number_of_molecules'].As(int)
                for i in range(n_this_mol):
                    molecule_to_molecule_type.append(type_gid_this_mol)
            #push_value(jbe, molecule_to_molecule_type, 'molecule_to_molecule_type_map') #TODO

            # Global atom map
            atoms_to_molidx_atomidx = []
            molidx = 0
            for mol in top.molecules:
                n_mol = mol['number_of_molecules'].As(int)
                for i in range(n_mol):
                    atomidx = 0
                    for atom in mol.atoms:
                        molidx_atomidx = [ molidx, atomidx ]
                        atoms_to_molidx_atomidx.append(molidx_atomidx)
                        atomidx += 1
                    molidx += 1
            #push_value(jbe, atoms_to_molidx_atomidx, 'atom_to_molecule') #TODO

        # SAMPLING-METHOD SECTION
        with open_section(jbe, 'section_sampling_method'):
            # Ensemble
            ensemble = push(jbe, out, 'ensemble_type', lambda s: s.As().split()[0].upper())           
            # Method
            push(jbe, out, 'sampling_method')
            push(jbe, out, 'integrator_type')
            push(jbe, out, 'integrator_dt', lambda s: s.As(float))
            push(jbe, out, 'number_of_steps_requested', lambda s: s.As(int))
            # Coupling
            if 'T' in ensemble:
                push(jbe, out, 'thermostat_target_temperature', lambda s: s.As(float))
                push(jbe, out, 'thermostat_tau', lambda s: s.As(float)) 
            if 'P' in ensemble:           
                push(jbe, out, 'barostat_target_pressure', lambda s: s.As(float))
                push(jbe, out, 'barostat_tau', lambda s: s.As(float))
            pass

        # FRAME-SEQUENCE SECTION
        with open_section(jbe, 'section_frame_sequence'):
            pass

    jbe.finishedParsingSession("ParseSuccess", None)
    return

if __name__ == '__main__':

    # CALCULATE PATH TO META-INFO FILE
    this_py_file = os.path.abspath(__file__)
    this_py_dirname = os.path.dirname(this_py_file)
    json_supp_file = parser_info["json"]
    meta_info_path = os.path.normpath(os.path.join(this_py_dirname, json_supp_file))

    # LOAD META-INFO FILE
    log("Meta-info from '%s'" % meta_info_path)
    meta_info_env, warns = loadJsonFile(
        filePath=meta_info_path,
        dependencyLoader=None,
        extraArgsHandling=InfoKindEl.ADD_EXTRA_ARGS,
        uri=None)

    output_file_name = sys.argv[1]
    parse(output_file_name)
    

