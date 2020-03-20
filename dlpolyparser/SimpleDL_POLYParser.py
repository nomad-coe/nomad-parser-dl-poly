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
from builtins import range
from builtins import object
import numpy as np
import math
from nomadcore.simple_parser import mainFunction
from nomadcore.simple_parser import SimpleMatcher as SM
from nomadcore.local_meta_info import loadJsonFile, InfoKindEl
from nomadcore.caching_backend import CachingLevel
import re, os, sys, json, logging


class DL_POLYParserContext(object):
	def __init__(self):
		self.cell	= []
		return
	def onClose_section_run(self, backend, gIndex, section):
		print("<onClose_section_run>")
		return
	def onClose_section_method(self, backend, gIndex, section):
		print("<onClose_section_method>")
		return
	def onClose_section_system(self, backend, gIndex, section):
		print("<onClose_section_system>")
		return
	def onClose_x_dl_poly_section_md_molecule_type(self, backend, gIndex, section):
		print("<onClose_molecule_type>")
		return

def test_adhoc(parser):
	return None
	for i in range(10):
		ln = parser.fIn.readline()
		print(ln)
		parser.fIn.pushbackLine(ln)
	#print len(parser.backend.openSections)
	return None

mainFileDescription = SM(name = 'root',
	 weak = True,
	 startReStr = "",
	 subMatchers = [

		SM(name = 'newRun',
		    startReStr = r" \*\* DL_POLY \*\*  authors:   i.t.todorov   &   w.smith  \** P \**",
		    repeats = False,
		    required = True,
		    forwardMatch = True,
			adHoc = test_adhoc,
		    sections   = ['section_run'],
		    subMatchers = [
				SM(name = 'progHeader',
					startReStr = r" \*\* DL_POLY \*\*  authors:   i.t.todorov   &   w.smith  \** P \**",
					subMatchers = [
						SM(r"\s*\*\*\s*\*\*  version:  (?P<program_version>[0-9a-zA-Z_.]*)    / \s* (?P<x_dl_poly_program_version_date>[\w]*\s*[\w]*)\s*\** O \**"),
						SM(r"\s*\**  when publishing research data obtained using (?P<program_name>[0-9a-zA-Z_.]*)  \**"),
						SM(r"\s*\**\s*(?P<x_dl_poly_system_description>[0-9a-zA-Z_()]*)\s*\**")
					]),
				SM(name = 'mdParams',
					startReStr = r"\s*SIMULATION CONTROL PARAMETERS\s*",
					required = True,
					sections = ['section_method'],
					subMatchers = [
						SM(r"\s*simulation temperature \(K\)\s*(?P<x_dl_poly_thermostat_temperature>[-+0-9.eEdD]*)\s*"),
						SM(r"\s*equilibration period \(steps\)\s*(?P<x_dl_poly_step_number_equilibration>[0-9]*)\s*"),
						SM(r"\s*selected number of timesteps\s*(?P<x_dl_poly_step_number>[0-9]*)\s*")
					]),

				# Open system
				# ... open topology
				# ... ... store <numberofmoleculetypes>
				# ... ... open molecule type id1
				# ... ... open molecule type ...

				SM(name = 'mdSystem',
					startReStr = r"\s*SYSTEM SPECIFICATION\s*",
					required = True,
					sections = ['section_system'],
					subMatchers = [
						SM(name = 'mdTopology',
							startReStr = r"\s*number of molecular types\s*[0-9]*\s*",
							required = True,
							forwardMatch = True,
							sections = ['x_dl_poly_section_md_topology'],
							subMatchers = [
								SM(r"\s*number of molecular types\s*(?P<x_dl_poly_md_molecular_types>[0-9]*)"),
								SM(name = 'mdTopologyMolecule',
									startReStr = r"\s*molecular species type\s*[0-9]*\s*",
									repeats = True,
									required = True,
									forwardMatch = True,
									sections = ['x_dl_poly_section_md_molecule_type'],
									subMatchers = [
										SM(r"\s*molecular species type\s*(?P<x_dl_poly_md_molecule_type_id>[0-9]*)\s*"),
										SM(r"\s*name of species:\s*(?P<x_dl_poly_md_molecule_type_name>[\w]* [\w]*)\s*")
									])
							])
						#SM(r"\s*number of molecular types\s*(?P<dl_poly_molecular_types_number>[0-9]*)\s*"),
						#SM(name = 'mdTopologyMolecule',
						#startReStr = r"\s*molecular species type\s*[0-9]*\s*",
						#repeats = True,
						#required = True,
						#sections = ['dl_poly_section_molecule_types'],
						#subMatchers = [\
						#])
					])
			])
	])


"""
mainFileDescription = SM(name = 'root',
     weak = True,
     startReStr = "",
     subMatchers = [

        SM(name = "newRun",
        startReStr = r"",
        #repeats = True,
        required = True,
        forwardMatch = True,
        sections   = ["section_run"],
        subMatchers = [

            SM(startReStr = "Number of k-points\s*",
               forwardMatch = True,
               sections = ["section_system"],
               subMatchers = [

                   SM(startReStr = "Number of k-points\s*",
                      forwardMatch = True,
                      sections = ["section_single_configuration_calculation"],
                      subMatchers = [

                          SM(startReStr = "Number of k-points\s*",
                             forwardMatch = True,
                             sections = ["section_eigenvalues_group"],
                             subMatchers = [

                                 SM(startReStr = "Number of k-points\s*",
                                    sections = ["section_eigenvalues"],
                                    forwardMatch = True,
                                    subMatchers = [

                                     SM(startReStr = "K\-point\s*[0-9]+\s*",
                                        sections = ["dl_poly_section_k_points"],
                                        forwardMatch = True,
                                        repeats = True,
                                        subMatchers = [

                                            SM(r"K\-point\s*[0-9]+\s*(?P<dl_poly_store_k_points> [-\d\.]+\s+[-\d\.]+\s+[-\d\.]+)",
                                               repeats = True),

                                                SM(name = 'Eigen',
                                                   startReStr = r"Spin component\s*[0-9]+\s*",
                                                   sections = ['dl_poly_section_eigenvalues'],
                                                   repeats = True,
                                                   subMatchers = [

                                                      SM(r"\s*(?P<dl_poly_store_eigenvalues> [-\d\.]+)",
                                                         repeats = True)

                                                   ]), # CLOSING dl_poly_section_eigenvalues

                                        ]), # CLOSING dl_poly_section_k_points

                                    ]), # CLOSING section_eigenvalues

                            ]), # CLOSING section_eigenvalues_group

                      ]), # CLOSING section_single_configuration_calculation

            ]), # CLOSING section_system

]), # CLOSING SM newRun


])
"""

# THIS PARSER
parserInfo = {'name':'dl_poly-parser', 'version': '0.0'}

# # LOAD METADATA
# metaInfoPath = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),"../../../../nomad-meta-info/meta_info/nomad_meta_info/dl_poly.nomadmetainfo.json"))
# metaInfoEnv, warnings = loadJsonFile(filePath = metaInfoPath, dependencyLoader = None, extraArgsHandling = InfoKindEl.ADD_EXTRA_ARGS, uri = None)

# CUSTOMIZE CACHING
cachingLevelForMetaName = {}


class DlPolyParser():
   """ A proper class envolop for running this parser from within python. """
   def __init__(self, backend, **kwargs):
       self.backend_factory = backend

   def parse(self, mainfile):
       from unittest.mock import patch
       logging.info('dl-poly parser started')
       logging.getLogger('nomadcore').setLevel(logging.WARNING)
       backend = self.backend_factory("dl_poly.nomadmetainfo.json")
       with patch.object(sys, 'argv', ['<exe>', '--uri', 'nmd://uri', mainfile]):
           mainFunction(
               mainFileDescription=mainFileDescription,
               metaInfoEnv=None,
               parserInfo = parserInfo,
               cachingLevelForMetaName = cachingLevelForMetaName,
               superContext=DL_POLYParserContext(),
               superBackend=backend,
			   onClose = {},
               defaultSectionCachingLevel = True)

       return backend
