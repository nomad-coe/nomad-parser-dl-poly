import os
import sys
import re
import json
import logging
import setup_paths

from nomadcore.local_meta_info import loadJsonFile, InfoKindEl
from nomadcore.parser_backend import JsonParseEventsWriterBackend
from contextlib import contextmanager

from libDlPolyParser import *

try:
    from momo import osio, endl, flush
    #osio.ConnectToFile('dl_poly.log')
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
def log(msg, highlight=osio.ww, enter=endl):
    if osio:
        osio << highlight << msg << enter
    return

# CONTEXT GUARD
@contextmanager
def open_section(p, name):
    gid = p.openSection(name)
    yield
    p.closeSection(name, gid)   

def push(jbe, terminal, key1, fct=lambda x: x.As(), key2=None):
    if key2 == None: key2 = key1
    value =  fct(terminal[key2])
    jbe.addValue(key1, value)
    return value

def parse(output_file_name):
    jbe = JsonParseEventsWriterBackend(meta_info_env)
    jbe.startedParsingSession(output_file_name, parser_info)
    
    # PARSE CONTROLS ...
    ctrl_file_name = 'CONTROL'
    terminal_ctrls = DlPolyControls(osio)
    terminal_ctrls.ParseControls(ctrl_file_name)    
    # PARSE OUTPUT / TOPOLOGY ...
    output_file_name = 'OUTPUT'
    terminal = DlPolyParser(osio)
    terminal.ParseOutput(output_file_name)    
    # PARSE TRAJECTORY ...
    cfg_file_name = 'CONFIG'
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
    
    ofs = open('keys.log', 'w')
    terminals = [ctr, out, top, trj]
    for t in terminals:
        keys = sorted(t.data.keys())
        for key in keys:
            ofs.write('[%s] %s\n' % (t.logtag, key))
        ofs.write('\n')
    ofs.close()
    
    # PUSH TO BACKEND
    with open_section(jbe, 'section_run'):
        push(jbe, out, 'program_name')
        push(jbe, out, 'program_version')
        push(jbe, out, 'program_info', key2='program_version_date')

        with open_section(jbe, 'section_topology'):
            push(jbe, top, 'number_of_topology_molecules', lambda s: s.As(int))
            push(jbe, top, 'number_of_topology_atoms', lambda s: s.As(int))
            # Molecule types
            for mol in top.molecules:
                with open_section(jbe, 'section_molecule_type'):
                    push(jbe, mol, 'molecule_type_name')
                    push(jbe, mol, 'number_of_atoms_in_molecule', lambda s: s.As(int))
                    # TODO settings_atom_... is abstract type => set atom_in_molecule_charge via list,
                    # TODO same for atom_in_molecule_name
                    # TODO atom_to_molecule, molecule_to_molecule_type, atom_in_molecule_to_atom_type_ref
                    for atom in mol.atoms:
                        with open_section(jbe, 'settings_atom_in_molecule'):
                            push(jbe, atom, 'atom_in_molecule_charge', lambda s: s.As(float), 'atom_charge')
                            push(jbe, atom, 'atom_in_molecule_name', lambda s: s.As(), 'atom_name')
            # Atom types
            for mol in top.molecules:
                for atom in mol.atoms:
                    with open_section(jbe, 'section_atom_type'):
                        push(jbe, atom, 'atom_type_name', lambda s: s.As(), 'atom_name')
                        push(jbe, atom, 'atom_type_mass', lambda s: s.As(float), 'atom_mass')
                        push(jbe, atom, 'atom_type_charge', lambda s: s.As(float), 'atom_charge')
            

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

    log("Parsing ...", green)
    output_file_name = sys.argv[1]
    parse(output_file_name)    
    log("... Done.", green)
    

