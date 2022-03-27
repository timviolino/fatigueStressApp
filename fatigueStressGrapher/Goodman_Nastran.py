import os
import copy
import math
import numpy as np
np.set_printoptions(precision=2, threshold=20, suppress=True)

import pyNastran
pkg_path = pyNastran.__path__[0]

from pyNastran.op2.op2 import OP2
from pyNastran.utils import print_bad_path
from pyNastran.op2.op2 import read_op2
from pyNastran.utils import object_methods, object_attributes

class GoodmanNastran():
    def __init__(self, file):
        # Read .op2 file data
        model = OP2()
        self.file = file
        model.read_op2(file, build_dataframe=False)
        self.loadcase_ids = list(model.ctria6_stress)
        self.init_results()
        self.stress = model.ctria6_stress
        stress_headers = self.stress[1].get_headers() #list of keys for each type of stress
        i_omax = stress_headers.index('omax') #index of column for max principle in stress matrix
        i_omin = stress_headers.index('omin') #index of column for min principle in stress matrix

        elements = self.define_elements() #creates list of element IDs excluding elements touching RBEs
        
        for i in self.loadcase_ids:
            data = self.stress[i].data
            
            # Record maximum principle stresses
            self.omaxes[i] = data[0, elements, i_omax] #save column as list
            self.omaxes[i] /= 1000 #convert from KPa to MPa
            print('Max Principle Stresses: ', self.omaxes[i], 'max = ', max(self.omaxes[i]),
                  'min = ', min(self.omaxes[i]), 'Length: ', len(self.omaxes[i]))
            
            # Record minimum principle stress
            self.omins[i] = data[0, elements, i_omin] #save column as list
            self.omins[i] /= 1000 #convert from KPa to MPa
            print('Min Principle Stresses =', self.omins[i], 'max = ', max(self.omins[i]),
                  'min = ', min(self.omins[i]), 'Length: ', len(self.omins[i]))

        for i in range(len(self.loadcase_ids)):
            i1 = self.loadcase_ids[i]
            i2 = self.loadcase_ids[i-1]
            
            # Calculate mean stress
            self.oavgs[i+1] = np.array([abs(omax+omin)/2 for omax, omin in zip(self.omaxes[i1], self.omins[i2])]) #apply formula at each element
            print('Average Stresses =', self.oavgs[i+1], max(self.oavgs[i+1]), min(self.oavgs[i+1]))
            
            # Calculate stress amplitude
            self.oamps[i+1] = np.array([(omax-omin)/2 for omax, omin in zip(self.omaxes[i1], self.omins[i2])]) #apply formula at each element
            print('Stress Amplitude =', self.oamps[i+1], max(self.oamps[i+1]), min(self.oamps[i+1]))

    def init_results(self):
        self.omaxes = {}
        self.omins = {}
        self.oavgs = {}
        self.oamps = {}
        
    def get_stresses(self):
        return (self.oavgs, self.oamps)

    def get_loadcase_ids(self):
        return self.loadcase_ids

    def extract_rbe_nodes(self):
        file = open(self.file, encoding='utf8', errors='ignore')
        s = file.read()
        i_bulk = s.index('BEGIN BULK')
        s = s[:i_bulk]
        nodes = []
        while 'RBE' in s:
            i_rbe = s.index('RBE')
            i_mesh = i_rbe+s[i_rbe:].index('MESH COLLECTOR')
            str_temp = s[i_rbe:i_mesh]
            node = ''
            nodes_temp = []
            for c in str_temp:
                if c in '0123456789':
                    node += c
                elif c in ' +' and len(node) > 0:
                    nodes_temp.append(int(node))
                    node = ''
            if nodes_temp[0] == 3: nodes.extend(nodes_temp[8:]) #removes frivolous values for RBE3's 
            else: nodes.extend(nodes_temp[7:]) #removes frivolous values for RBE2's
            s = s[i_mesh:]
        return nodes

    def define_elements(self):
        elements = self.stress[1].element_node[:, 0] #0 index - elements, 1 index - nodes
        nodes = self.stress[1].element_node[:, 1]
        uniq_els = np.unique(elements) #remove duplicate indices
        RBE_Nodes = self.extract_rbe_nodes() # Remove elements next to RBEs
        #removed = np.array([])
        for node in RBE_Nodes:
            i_node = np.where(nodes == node)[0]
            rigid_el = elements[i_node]
            i_el = []
            for n in rigid_el:
                try: i_el.append(np.where(uniq_els == n)[0].tolist()[0])
                except: continue
            #removed = np.concatenate((removed, np.take(uniq_els, i_el)))
            uniq_els = np.delete(uniq_els, i_el) #remove RBEs that touch current given node
        uniq_els = (8*uniq_els-(8*elements[0]-1)) # Adjust indices so that nodal stresses are ignored
        #removed = [int(x) for x in sorted(np.unique(removed).tolist())]
        #print(removed, 'length = ', len(removed))
        return uniq_els

if __name__ == '__main__':
    file = 'C:\\Users\\TVIOLIN\\Desktop\\pyNastran\\h00000000387587_1_sim1-solution_1.op2'
    GoodmanNastran(file)
