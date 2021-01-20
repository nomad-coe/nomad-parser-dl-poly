#
# Copyright The NOMAD Authors.
#
# This file is part of NOMAD.
# See https://nomad-lab.eu for further info.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import numpy as np            # pylint: disable=unused-import
import typing                 # pylint: disable=unused-import
from nomad.metainfo import (  # pylint: disable=unused-import
    MSection, MCategory, Category, Package, Quantity, Section, SubSection, SectionProxy,
    Reference
)
from nomad.metainfo.legacy import LegacyDefinition

from nomad.datamodel.metainfo import public

m_package = Package(
    name='dl_poly_nomadmetainfo_json',
    description='None',
    a_legacy=LegacyDefinition(name='dl_poly.nomadmetainfo.json'))


class x_dl_poly_section_md_molecule_type(MSection):
    '''
    Section to store molecule type information
    '''

    m_def = Section(validate=False, a_legacy=LegacyDefinition(name='x_dl_poly_section_md_molecule_type'))

    x_dl_poly_md_molecule_type_id = Quantity(
        type=np.dtype(np.int32),
        shape=[],
        description='''
        Molecule type id
        ''',
        a_legacy=LegacyDefinition(name='x_dl_poly_md_molecule_type_id'))

    x_dl_poly_md_molecule_type_name = Quantity(
        type=str,
        shape=[],
        description='''
        Molecule type name
        ''',
        a_legacy=LegacyDefinition(name='x_dl_poly_md_molecule_type_name'))


class x_dl_poly_section_md_topology(MSection):
    '''
    Section modelling the MD topology
    '''

    m_def = Section(validate=False, a_legacy=LegacyDefinition(name='x_dl_poly_section_md_topology'))

    x_dl_poly_md_molecular_types = Quantity(
        type=np.dtype(np.int32),
        shape=[],
        description='''
        Number of molecular types in topology
        ''',
        a_legacy=LegacyDefinition(name='x_dl_poly_md_molecular_types'))

    x_dl_poly_section_md_molecule_type = SubSection(
        sub_section=SectionProxy('x_dl_poly_section_md_molecule_type'),
        repeats=True,
        a_legacy=LegacyDefinition(name='x_dl_poly_section_md_molecule_type'))


class section_sampling_method(public.section_sampling_method):

    m_def = Section(validate=False, extends_base_section=True, a_legacy=LegacyDefinition(name='section_sampling_method'))

    x_dl_poly_barostat_target_pressure = Quantity(
        type=np.dtype(np.float64),
        shape=[],
        unit='pascal',
        description='''
        MD barostat target pressure.
        ''',
        categories=[public.settings_molecular_dynamics, public.settings_barostat, public.settings_sampling],
        a_legacy=LegacyDefinition(name='x_dl_poly_barostat_target_pressure'))

    x_dl_poly_barostat_tau = Quantity(
        type=np.dtype(np.float64),
        shape=[],
        unit='second',
        description='''
        MD barostat relaxation time.
        ''',
        categories=[public.settings_molecular_dynamics, public.settings_barostat, public.settings_sampling],
        a_legacy=LegacyDefinition(name='x_dl_poly_barostat_tau'))

    x_dl_poly_integrator_dt = Quantity(
        type=np.dtype(np.float64),
        shape=[],
        unit='second',
        description='''
        MD integration time step.
        ''',
        categories=[public.settings_molecular_dynamics, public.settings_integrator, public.settings_sampling],
        a_legacy=LegacyDefinition(name='x_dl_poly_integrator_dt'))

    x_dl_poly_integrator_type = Quantity(
        type=str,
        shape=[],
        description='''
        MD integrator type, valid values are defined in the integrator_type wiki page.
        ''',
        categories=[public.settings_molecular_dynamics, public.settings_integrator, public.settings_sampling],
        a_legacy=LegacyDefinition(name='x_dl_poly_integrator_type'))

    x_dl_poly_number_of_steps_requested = Quantity(
        type=np.dtype(np.float64),
        shape=[],
        description='''
        Number of requested MD integration time steps.
        ''',
        categories=[public.settings_molecular_dynamics, public.settings_integrator, public.settings_sampling],
        a_legacy=LegacyDefinition(name='x_dl_poly_number_of_steps_requested'))

    x_dl_poly_thermostat_target_temperature = Quantity(
        type=np.dtype(np.float64),
        shape=[],
        unit='kelvin',
        description='''
        MD thermostat target temperature.
        ''',
        categories=[public.settings_molecular_dynamics, public.settings_thermostat, public.settings_sampling],
        a_legacy=LegacyDefinition(name='x_dl_poly_thermostat_target_temperature'))

    x_dl_poly_thermostat_tau = Quantity(
        type=np.dtype(np.float64),
        shape=[],
        unit='second',
        description='''
        MD thermostat relaxation time.
        ''',
        categories=[public.settings_molecular_dynamics, public.settings_thermostat, public.settings_sampling],
        a_legacy=LegacyDefinition(name='x_dl_poly_thermostat_tau'))


class section_run(public.section_run):

    m_def = Section(validate=False, extends_base_section=True, a_legacy=LegacyDefinition(name='section_run'))

    x_dl_poly_program_version_date = Quantity(
        type=str,
        shape=[],
        description='''
        Program version date
        ''',
        a_legacy=LegacyDefinition(name='x_dl_poly_program_version_date'))

    x_dl_poly_system_description = Quantity(
        type=str,
        shape=[],
        description='''
        Simulation run title
        ''',
        a_legacy=LegacyDefinition(name='x_dl_poly_system_description'))


class section_system(public.section_system):

    m_def = Section(validate=False, extends_base_section=True, a_legacy=LegacyDefinition(name='section_system'))

    x_dl_poly_section_md_topology = SubSection(
        sub_section=SectionProxy('x_dl_poly_section_md_topology'),
        repeats=True,
        a_legacy=LegacyDefinition(name='x_dl_poly_section_md_topology'))


class section_method(public.section_method):

    m_def = Section(validate=False, extends_base_section=True, a_legacy=LegacyDefinition(name='section_method'))

    x_dl_poly_step_number_equilibration = Quantity(
        type=np.dtype(np.int32),
        shape=[],
        description='''
        MD equilibration step number
        ''',
        a_legacy=LegacyDefinition(name='x_dl_poly_step_number_equilibration'))

    x_dl_poly_step_number = Quantity(
        type=np.dtype(np.int32),
        shape=[],
        description='''
        MD total step number
        ''',
        a_legacy=LegacyDefinition(name='x_dl_poly_step_number'))

    x_dl_poly_thermostat_temperature = Quantity(
        type=np.dtype(np.float64),
        shape=[],
        description='''
        Thermostat coupling temperature
        ''',
        a_legacy=LegacyDefinition(name='x_dl_poly_thermostat_temperature'))


m_package.__init_metainfo__()
