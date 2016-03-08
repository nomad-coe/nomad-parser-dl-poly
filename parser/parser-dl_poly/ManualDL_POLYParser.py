import os
import sys
import re
import json
import logging
import setup_paths

from nomadcore.local_meta_info import loadJsonFile, InfoKindEl
from nomadcore.parser_backend import JsonParseEventsWriterBackend
from contextlib import contextmanager

from libDL_POLYParser import *

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


def parse(output_file_name):
    p  = JsonParseEventsWriterBackend(meta_info_env)
    o  = open_section
    p.startedParsingSession(output_file_name, parser_info)
    
    # PARSE CONTROLS
    ctrl_file_name = 'CONTROL'
    terminal_ctrls = DlPolyControls(osio)
    terminal_ctrls.ParseControls(ctrl_file_name)
    
    # PARSE OUTPUT / TOPOLOGY
    output_file_name = 'OUTPUT'
    terminal = DlPolyParser(osio)
    terminal.ParseOutput(output_file_name)
    
    # PARSE TRAJECTORY
    cfg_file_name = 'CONFIG'
    terminal_trj = DlPolyConfig(osio)
    terminal_trj.ParseConfig(cfg_file_name)    
    
    # SUMMARIZE KEY-TABLE DEFAULTS
    terminal.SummarizeKeyDefaults()
    terminal.topology.SummarizeKeyDefaults()
    terminal_ctrls.SummarizeKeyDefaults()
    terminal_trj.SummarizeKeyDefaults()
    
    osio.okquit()

    with o(p, 'section_run'):
        p.addValue('program_name', 'DL_POLY')

        with o(p, 'section_topology'):
            pass

        with o(p, 'section_sampling_method'):
            pass

        with o(p, 'section_frame_sequence'):
            pass

    p.finishedParsingSession("ParseSuccess", None)
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
    

