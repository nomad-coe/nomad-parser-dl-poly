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

from builtins import range
import os
import sys
import re
import json
import logging
import numpy as np

from nomadcore.local_meta_info import loadJsonFile, InfoKindEl
from contextlib import contextmanager

from dlpolyparser.libDlPolyParser import *

try:
    from dlpolyparser.libMomo import osio, endl, flush
    # osio.ConnectToFile('parser.osio.log')
    # green = osio.mg
    osio = endl = flush = None
    green = None
except:
    osio = endl = flush = None
    green = None


# parser_info = {
#     "name": "parser-dl-poly",
#     "version": "0.0",
#     "json": "../../../../nomad-meta-info/meta_info/nomad_meta_info/dl_poly.nomadmetainfo.json"
# }

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

def push(jbe, terminal, key1, fct=lambda x: x.As(), key2=None, conv=None):
    if key2 == None: key2 = key1
    value =  fct(terminal[key2])
    if conv:
        jbe.addValue(key1, value*conv)
    else:
        jbe.addValue(key1, value)
    return value

def push_array(jbe, terminal, key1, fct=lambda x: x.As(), key2=None, conv=None):
    if key2 == None: key2 = key1
    value =  np.asarray(fct(terminal[key2]))
    if conv:
        jbe.addArrayValues(key1, value*conv)
    else:
        jbe.addArrayValues(key1, value)
    return value

def push_value(jbe, value, key, conv=None):
    if conv:
        jbe.addValue(key, value*conv)
    else:
        jbe.addValue(key, value)
    return value

def push_array_values(jbe, value, key, conv=None):
    if conv:
        jbe.addArrayValues(key, value*conv)
    else:
        jbe.addArrayValues(key, value)
    return value


# class DlPolyParser():
#    """ A proper class envolop for running this parser from within python. """
#    def __init__(self, backend, **kwargs):
#        self.backend_factory = backend

#     from unittest.mock import patch
#     logging.info('dl-poly parser started')
#     logging.getLogger('nomadcore').setLevel(logging.WARNING)
#     backend = self.backend_factory(metaInfoEnv)
#     # Rename parser
#     def parse(self, mainfile):


logger = logging.getLogger("nomad.DLPolyParser")


class DlPolyParserWrapper():
    """ A proper class envolop for running this parser using Noamd-FAIRD infra. """
    def __init__(self, backend, **kwargs):
        self.backend_factory = backend

    def parse(self, mainfile):
        logging.info('dl-poly parser started')
        logging.getLogger('nomadcore').setLevel(logging.WARNING)
        backend = self.backend_factory("dl_poly.nomadmetainfo.json")
        # Call the old parser without a class.
        parserInfo = {'name': 'dl_poly-parser', 'version': '0.0'}
        backend = parse_without_class(mainfile, backend, parserInfo)
        return backend


def parse_without_class(output_file_name, backend, parser_info):
    """ Parse method to parse mainfile and write output to backend."""
    jbe = backend
    jbe.startedParsingSession(output_file_name, parser_info)

    base_dir = os.path.dirname(os.path.abspath(output_file_name))

    # PARSE CONTROLS ...
    ctrl_file_name = os.path.join(base_dir, 'CONTROL')
    terminal_ctrls = DlPolyControls(osio)
    terminal_ctrls.ParseControls(ctrl_file_name)

    # PARSE OUTPUT / TOPOLOGY ...
    output_file_name = os.path.join(base_dir, 'OUTPUT')
    terminal = DlPolyParser(osio)
    terminal.ParseOutput(output_file_name)

    # PARSE CONFIG ...
    cfg_file_name = os.path.join(base_dir, 'CONFIG')
    terminal_cfg = DlPolyConfig(osio)
    terminal_cfg.ParseConfig(cfg_file_name)

    # PARSE TRAJECTORY
    trj_file_name = os.path.join(base_dir, 'HISTORY')
    terminal_trj = DlPolyTrajectory(osio)
    terminal_trj.ParseTrajectory(trj_file_name, terminal.step_data, terminal.time_data)

    # SUMMARIZE KEY-TABLE DEFAULTS ...
    terminal.SummarizeKeyDefaults()
    terminal.topology.SummarizeKeyDefaults()
    terminal_ctrls.SummarizeKeyDefaults()
    terminal_cfg.SummarizeKeyDefaults()
    terminal_trj.SummarizeKeyDefaults()

    # ABBREVIATE ...
    ctr = terminal_ctrls
    out = terminal
    top = terminal.topology
    cfg = terminal_cfg
    trj = terminal_trj
    terminals = [ctr, out, top, cfg, trj]

    # ESTABLISH (ENERGY) UNITS
    unit_energy = top['energy_units'].As(str).lower().replace(' ','').replace('/','_').replace('(','_').replace(')','')
    UNITCONV_DLPOLY_TO_SI['energy'] = UNITCONV_DLPOLY_CUSTOM_TO_SI['energy_%s' % unit_energy]

    # ofs = open('parser.keys.log', 'w')
    # for quantity, conv in UNITCONV_DLPOLY_TO_SI.items():
    #     ofs.write('Unit [%s] = %e SI\n' % (quantity, conv))
    # ofs.write('\n')
    # for t in terminals:
    #     keys = sorted(t.data.keys())
    #     for key in keys:
    #         ofs.write('[%s] %s = %s\n' % (t.logtag, key, t[key].As(str)))
    #     ofs.write('\n')
    # ofs.close()

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
                        push(jbe, atom, 'atom_type_mass', lambda s: s.As(float), 'atom_mass', conv=UNITCONV_DLPOLY_TO_SI['mass'])
                        push(jbe, atom, 'atom_type_charge', lambda s: s.As(float), 'atom_charge', conv=UNITCONV_DLPOLY_TO_SI['charge'])
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

                    push_array(jbe, mol, 'atom_in_molecule_name')
                    push_array(jbe, mol, 'atom_in_molecule_charge', conv=UNITCONV_DLPOLY_TO_SI['charge'])
                    push_array_values(jbe, np.asarray(atom_gid_list), 'atom_in_molecule_to_atom_type_ref')
            # Global molecule type map
            molecule_to_molecule_type = []
            for mol in top.molecules:
                type_name_this_mol = mol['molecule_type_name'].As()
                type_gid_this_mol = molecule_type_name_to_type_gid[type_name_this_mol]
                n_this_mol = mol['number_of_molecules'].As(int)
                for i in range(n_this_mol):
                    molecule_to_molecule_type.append(type_gid_this_mol)
            push_array_values(jbe, np.asarray(molecule_to_molecule_type), 'molecule_to_molecule_type_map')

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
            push_array_values(jbe, np.asarray(atoms_to_molidx_atomidx), 'atom_to_molecule')

        # SAMPLING-METHOD SECTION
        sec_sampling_method_ref = None
        with open_section(jbe, 'section_sampling_method') as gid_sec_sampling_method:
            sec_sampling_method_ref = gid_sec_sampling_method
            # Ensemble
            ensemble = push(jbe, out, 'ensemble_type', lambda s: s.As().split()[0].upper())
            # Method
            push(jbe, out, 'sampling_method')
            push(jbe, out, 'x_dl_poly_integrator_type')
            push(jbe, out, 'x_dl_poly_integrator_dt', lambda s: s.As(float))
            push(jbe, out, 'x_dl_poly_number_of_steps_requested', lambda s: s.As(int))
            # Coupling
            if 'T' in ensemble:
                push(jbe, out, 'x_dl_poly_thermostat_target_temperature', lambda s: s.As(float), conv=UNITCONV_DLPOLY_TO_SI['temperature'])
                push(jbe, out, 'x_dl_poly_thermostat_tau', lambda s: s.As(float))
                pass
            if 'P' in ensemble:
                push(jbe, out, 'x_dl_poly_barostat_target_pressure', lambda s: s.As(float), conv=UNITCONV_DLPOLY_TO_SI['pressure_katm'])
                push(jbe, out, 'x_dl_poly_barostat_tau', lambda s: s.As(float), conv=UNITCONV_DLPOLY_TO_SI['time'])
                pass
            pass

        # METHOD SECTION
        sec_method_ref = None
        with open_section(jbe, 'section_method') as gid_sec_method:
            sec_method_ref = gid_sec_method
            push_value(jbe, 'force_field', 'calculation_method')

        # TODO Store state variables in frames/system description (temperature, pressure)
        # TODO Store interactions

        # SYSTEM DESCRIPTION
        refs_system_description = []
        all_frames = [cfg] + trj.frames # <- Initial config + trajectory
        for frame in all_frames:
            with open_section(jbe, 'section_system') as gid:
                refs_system_description.append(gid)
                # Configuration core
                atom_labels = np.array(
                    [ atom['atom_name'].As().replace('+','').replace('-','') for atom in frame.atoms ])
                push_array_values(jbe, atom_labels, 'atom_labels')
                # push_array_values(jbe, atom_species, 'atom_atom_numbers')
                push_array_values(jbe, frame.position_matrix, 'atom_positions', conv=UNITCONV_DLPOLY_TO_SI['length'])
                push_array_values(jbe, frame.box_matrix, 'simulation_cell', conv=UNITCONV_DLPOLY_TO_SI['length'])
                push_array_values(jbe, frame.pbc_booleans, 'configuration_periodic_dimensions')
                if frame.has_velocities:
                    push_array_values(jbe, frame.velocity_matrix, 'atom_velocities', conv=UNITCONV_DLPOLY_TO_SI['length']/UNITCONV_DLPOLY_TO_SI['time'])
                if frame.has_forces:
                    # TODO Wouldn't it be simpler if forces were added here?
                    pass
                pass

        # SINGLE CONFIGURATIONS
        refs_single_configuration = []
        i_frame = -1
        for frame in all_frames:
            i_frame += 1
            with open_section(jbe, 'section_single_configuration_calculation') as gid:
                refs_single_configuration.append(gid)
                # Reference system description section
                ref_system = refs_system_description[i_frame]
                push_value(jbe, ref_system, 'single_configuration_calculation_to_system_ref')
                # Energy total
                if frame.has_energy_total:
                    push_value(jbe, frame.energy_total, 'energy_total', conv=UNITCONV_DLPOLY_TO_SI['energy'])
                # Forces
                if frame.has_forces:
                    push_array_values(jbe, frame.force_matrix, 'atom_forces', conv=UNITCONV_DLPOLY_TO_SI['mass']*UNITCONV_DLPOLY_TO_SI['length']/UNITCONV_DLPOLY_TO_SI['time']**2)
                # Method reference
                push_value(jbe, sec_method_ref, 'single_configuration_to_calculation_method_ref')
                pass

        # FRAME-SEQUENCE SECTION
        with open_section(jbe, 'section_frame_sequence'):
            push_value(jbe, len(all_frames), 'number_of_frames_in_sequence')
            # Reference configurations and sampling method
            push_value(jbe, sec_sampling_method_ref, 'frame_sequence_to_sampling_ref')
            refs_config = np.array(refs_single_configuration)
            push_array_values(jbe, refs_config, 'frame_sequence_local_frames_ref')
            time_values = np.array([ frame['time_value'].As(float)*UNITCONV_DLPOLY_TO_SI['time'] for frame in trj.frames ])
            push_array_values(jbe, time_values, 'frame_sequence_time')
            pass

    jbe.finishedParsingSession("ParseSuccess", None)
    return jbe

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


