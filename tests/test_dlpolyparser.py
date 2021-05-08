#
# Copyright The NOMAD Authors.
#
# This file is part of NOMAD. See https://nomad-lab.eu for further info.
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

import pytest
import numpy as np

from nomad.datamodel import EntryArchive
from dlpolyparser import DLPolyParser


def approx(value, abs=0, rel=1e-6):
    return pytest.approx(value, abs=abs, rel=rel)


@pytest.fixture(scope='module')
def parser():
    return DLPolyParser()


def test_basic(parser):
    archive = EntryArchive()

    parser.parse('tests/data/dl-poly-test1/OUTPUT', archive, None)

    sec_run = archive.section_run[0]
    assert sec_run.program_version == '4.07    /    january  2015'

    sec_system = archive.section_run[0].section_system[0]
    assert sec_system.lattice_vectors[2][2].magnitude == approx(9.878128e-09)
    assert sec_system.atom_labels[10] == 'Na'
    assert np.shape(sec_system.atom_positions) == (27000, 3)
    assert sec_system.atom_positions[3][1].magnitude == approx(-1.98512856e-09)
    assert np.shape(sec_system.atom_velocities) == (27000, 3)

    sec_sccs = sec_run.section_single_configuration_calculation
    assert sec_sccs[3].energy_total.magnitude == approx(-1.5993482e-14)
    assert sec_sccs[0].atom_forces[50][2].magnitude == approx(-2.85217134e-10)
