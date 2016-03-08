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
'real_space_cutoff_angs' : None,
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




         


class FileStream(object):
    def __init__(self, filename):
        self.ifs = open(filename, 'r')
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
        block_stream = FileBlockStream()
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
    
class FileBlockStream(FileStream):
    def __init__(self):
        self.ifs = self
        self.lns = []
        self.idx = 0
    def append(self, ln):
        self.lns.append(ln)
    def readline(self):
        if self.all_read():
            return ''        
        ln = self.lns.pop(self.idx)
        self.idx += 1
        return ln
    def all_read(self):
        return self.idx > len(self.lns)-1


class DlPolyParser(object):
    def __init__(self, log=None):
        self.output_file = 'OUTPUT'
        self.log = log
        self.data = {}
        return    
    def Set(self, key, value):
        if self.log:
            self.log << "Set   %-40s = %s" % (key, str(value)) << self.log.endl
        if not self.data.has_key(key):
            self.data[key] = value
        else:
            raise KeyError("Key already exists: '%s'" % key)
        return
    def SearchMapKeys(self, expr, ln, keys):
        s = re.search(expr, ln)
        for i in range(len(keys)):
            self.Set(keys[i], s.group(i+1).strip())
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
            if key_out == None:
                key_out = key_in
            if not block_data.has_key(key_in):
                self.log << "NOTE Missing key '%s' <> '%s'" % (key_in, key_out)
                value = ''
            else:
                value = block_data[key_in]
            self.Set(key_out, value)
        
    def ParseOutput(self, output_file):        
        if self.log: 
            self.log << self.log.endl << self.log.endl
            self.log << "DlPolyParser::ParseOutput" << self.log.endl
        
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
        self.SearchMapKeys('\*+\s([\w+\s]*)\s\*+', ifs.ln(), ['title'])
        
        # SIMULATION CONTROL PARAMETERS
        block = ifs.GetBlock('SIMULATION CONTROL PARAMETERS', 'SYSTEM SPECIFICATION')        
        block_data = self.ReadBlockXy(block)
        self.ApplyBlockXyData(block_data, KEY_TRANSFORM_SIM_CTRL)
        
        self.log.okquit()
        
        return

        


        
