###Imported Packages###
import os
import numpy as np
import math

import wx
from wx.lib.plot import PolyLine, PlotCanvas, PlotGraphics, PolyMarker
import wx.lib.agw.multidirdialog as MDD

from Goodman_Nastran import *

###Global Constants###
title = 'Goodman Test' #title of window
size = (850,500) #size of window
frame_style = wx.DEFAULT_FRAME_STYLE & ~(wx.RESIZE_BORDER | wx.MAXIMIZE_BOX) #prevent resizing and maximizing
delimeter = 5 #number of pixels of space between graphical objects
yield_factor = 1.2 # Yield in compression is larger than tension

###############################MAKE MATERIAL CHANGES HERE###############################
#TO CALULATE SN FOR ALL CYCLES FOR A MATERIAL, TWO POINTS (CYCLES, SN [MPA]) ARE REQUIRED

cycles = ["10,000", "50,000", "100,000", "150,000", "152,000", "250,000", "500,000", "1,000,000"]
stresses = {"80-55-06 Ductile Iron":{'Sy':float(6.895*55.),
                                     'Su':float(6.895*80.),
                                     'Sn':{"10,000":float(350),
                                           "152,000":float(235)}},
            
            "130-90-09 Austered Ductile Iron":{'Sy':float(6.895*55.),
                                               'Su':float(6.895*130.),
                                               'Sn':{"10,000":float(478),
                                                     "152,000":float(341.7)}}
            }
materials = list(stresses)

########################################################################################

###Functions###
def eval_loglog(x0, y0, x1, y1, n):
    return y0*math.pow(n/x0,((math.log10(y1/y0))/(math.log10(x1/x0))))

def init_materials():
    for mat in materials:
        points = stresses[mat]['Sn']
        n = list(points)
        Sn = [points[n[0]], points[n[1]]]
        for cyc in cycles:
            points[cyc] = eval_loglog(int(n[0].replace(',','')), Sn[0], int(n[1].replace(',','')), Sn[1], int(cyc.replace(',','')))

###GUI Frame Class###
class GoodmanFrame(wx.Frame):

    ###Initialization###
    def __init__(self, parent, title, size, style):
        super(GoodmanFrame, self).__init__(parent, title=title, size=size, style=style)
        
        self.panel = wx.Panel(self)
        self.hbox = wx.BoxSizer(wx.HORIZONTAL)

        self.init_font()
        self.init_vars()
        self.init_settings()
        self.init_graph()
        self.Centre()

        self.panel.SetSizer(self.hbox)

    def init_font(self):
        st = wx.StaticText()
        self.font = st.GetFont()
        self.font.PointSize += 1

    def init_vars(self):
        self.material = None
        self.material_selected = False
        self.cycle = None
        self.cycle_selected = False
        self.Sy = None
        self.Su = None
        self.Sn = None
        self.dir = os.getcwd()
        self.path = None
        self.X = None
        self.Y = None
        self.oavgs = None
        self.oamps = None
        self.loadcase_id = None
        
    def init_settings(self):
        vbox = wx.BoxSizer(wx.VERTICAL)

        ###Header###
        header = wx.StaticText(self.panel, label='Settings')
        header.SetFont(self.font)
        vbox.Add(header, 0, wx.ALL, delimeter)
        vbox.Add(wx.StaticLine(self.panel,), 0, wx.ALL|wx.EXPAND, delimeter)

        ###Material Selection###
        matHBox = wx.BoxSizer(wx.HORIZONTAL)
        matLabel = wx.StaticText(self.panel, label='Material of Part: ')
        matHBox.Add(matLabel, 0, wx.ALL, delimeter)
        self.matList = wx.ListBox(self.panel, size=(-1,-1), choices=materials, style=wx.LB_SINGLE)
        self.Bind(wx.EVT_LISTBOX, self.on_matList, self.matList)
        matHBox.Add(self.matList, 1, wx.ALL|wx.EXPAND, delimeter)
        vbox.Add(matHBox,1, wx.ALL|wx.EXPAND, delimeter)

        ###Cycle Selection###
        cycHBox = wx.BoxSizer(wx.HORIZONTAL)
        cycLabel = wx.StaticText(self.panel, label='Number of Fatigue Cycles: ')
        cycHBox.Add(cycLabel, 0, wx.ALL, delimeter)
        self.cycList = wx.ListBox(self.panel, size=(-1, 50), choices=cycles, style=wx.LB_SINGLE|wx.LB_ALWAYS_SB)
        self.Bind(wx.EVT_LISTBOX, self.on_cycList, self.cycList)
        cycHBox.Add(self.cycList, 1, wx.ALL|wx.EXPAND, delimeter)
        vbox.Add(cycHBox,1, wx.ALL|wx.EXPAND, delimeter)

        ###File Selection###
        fileLabel = wx.StaticText(self.panel, label='Path to Nastran (.op2) File:')
        vbox.Add(fileLabel, 0, wx.ALL, delimeter)
        fileHBox = wx.BoxSizer(wx.HORIZONTAL)
        self.fileText = wx.TextCtrl(self.panel, value="", style=wx.TE_READONLY)
        fileHBox.Add(self.fileText, 1, wx.ALL|wx.EXPAND, delimeter)
        self.fileBtn = wx.Button(self.panel, label='Select File')
        self.fileBtn.Bind(wx.EVT_BUTTON, self.on_selectFile)
        fileHBox.Add(self.fileBtn, 0, wx.ALL, delimeter)
        vbox.Add(fileHBox, 0, wx.ALL|wx.EXPAND, delimeter)

        ###Plot Title###
        titleLabel = wx.StaticText(self.panel, label='Plot Title: ')
        vbox.Add(titleLabel, 0, wx.ALL, delimeter)
        titleHBox = wx.BoxSizer(wx.HORIZONTAL)
        self.titleText = wx.TextCtrl(self.panel, value="")
        titleHBox.Add(self.titleText, 1, wx.ALL|wx.EXPAND, delimeter)
        self.titleBtn = wx.Button(self.panel, label='Update Title')
        self.titleBtn.Bind(wx.EVT_BUTTON, self.on_titleUpdate)
        titleHBox.Add(self.titleBtn, 0, wx.ALL, delimeter)
        vbox.Add(titleHBox, 0, wx.ALL|wx.EXPAND, delimeter)

        ###Run Button###
        self.runBtn = wx.Button(self.panel, label='Run Simulation')
        self.runBtn.Bind(wx.EVT_BUTTON, self.on_run)
        self.runBtn.Disable()
        vbox.Add(self.runBtn, 0, wx.ALL|wx.CENTER, delimeter)

        ###Save and Reset Buttons###
        btnHBox = wx.BoxSizer(wx.HORIZONTAL)
        self.saveBtn = wx.Button(self.panel, label='Save Plot')
        self.saveBtn.Bind(wx.EVT_BUTTON, self.on_save)
        self.saveBtn.Disable()
        btnHBox.Add(self.saveBtn, 0, wx.ALL|wx.CENTER, delimeter)
        self.resetBtn = wx.Button(self.panel, label='Reset')
        self.resetBtn.Bind(wx.EVT_BUTTON, self.on_reset)
        btnHBox.Add(self.resetBtn, 0, wx.ALL|wx.CENTER, delimeter)
        vbox.Add(btnHBox, 0, wx.ALL|wx.CENTER, delimeter)
        
        self.hbox.Add(vbox, 0, wx.ALL|wx.EXPAND, delimeter)

    def init_graph(self):
        vbox = wx.BoxSizer(wx.VERTICAL)
        
        ###Title###
        header = wx.StaticText(self.panel, label='Results')
        header.SetFont(self.font)
        vbox.Add(header, 0, wx.ALL, delimeter)    
        vbox.Add(wx.StaticLine(self.panel,), 0, wx.ALL|wx.EXPAND, delimeter)

        ###Graph###        
        self.canvas = PlotCanvas(self.panel, style=wx.BORDER_THEME)
        self.set_graphTitle()
        self.draw_graph(self.loadcase_id)
        vbox.Add(self.canvas, 1, wx.ALL|wx.EXPAND, delimeter)

        caseHBox = wx.BoxSizer(wx.HORIZONTAL)
        self.caseBtn1 = wx.ToggleButton(self.panel, label="Case 1")
        self.caseBtn1.Bind(wx.EVT_TOGGLEBUTTON, self.on_toggle1)
        self.caseBtn1.SetValue(True)
        caseHBox.Add(self.caseBtn1, 0, wx.ALL|wx.CENTER, delimeter)
        self.caseBtn2 = wx.ToggleButton(self.panel, label="Case 2")
        self.caseBtn2.Bind(wx.EVT_TOGGLEBUTTON, self.on_toggle2)
        caseHBox.Add(self.caseBtn2, 0, wx.ALL|wx.CENTER, delimeter)
        vbox.Add(caseHBox, 0, wx.ALL|wx.CENTER, delimeter)
        
        self.hbox.Add(vbox, 1, wx.ALL|wx.EXPAND, delimeter)

    ###Draw###
    def draw_graph(self, loadcase_id):
        ylim = 500
        objects = []
        if self.material_selected and self.cycle_selected:
            objects += self.get_lines(self.Sy, self.Sn, self.Su)
        if not None in (self.oavgs, self.oamps):
            oamps = self.oamps[loadcase_id]; oavgs = self.oavgs[loadcase_id]
            objects += self.get_points(oamps, oavgs)
            ylim = max(500, max(oavgs)+10)
        center_line = [(0, 0), (0, ylim)]
        objects.append(PolyLine(center_line, colour='Black', width=1))
        graphics = PlotGraphics(objects, self.title, "Mean Stress [MPa]", "Stress Amplitude [MPa]")
        xAxis = (-500, 500); yAxis = (0, ylim)
        self.canvas.Draw(graphics, xAxis, yAxis)

    def get_lines(self, Sy, Sn, Su):
        lines = []
        X = [-yield_factor*Sy,                                 # where Goodman intersects y=0 in compression
             yield_factor*(Sn-Sy),                             # leftmost point of horiz Sn line
             float(0),
             (Sy-Sn)/(float(1) - Sn/Su),                       # intersection of yield and Goodman line
             Sy]                                               # where Goodman intersects y=0 in tension
        Y = [float(0),
             Sn,                                               
             Sn,                                               # rightmost point of horiz Sn line
             Sy-X[3],
             float(0)]
        for i in range(len(X)-1):
            colour = 'Black' if i in [1, 2] else 'Red'
            end_points = [(X[i],Y[i]), (X[i+1],Y[i+1])]
            lines.append(PolyLine(end_points, colour=colour, width=2))
        return lines

    def get_points(self, oamps, oavgs):
        points = []
        for oamp, oavg in zip(oamps, oavgs):
            point = PolyMarker([(oamp, oavg)], size=1, colour='blue')
            points.append(point)
        return points

    def set_graphTitle(self, graph_title=None):
        if graph_title != None:
            self.title = graph_title
            self.canvas.fontSizeTitle = 13
        elif self.material_selected and self.cycle_selected:
            self.title = "Goodman Plot for " + self.material + " at " + self.cycle + " Cycles"
            self.canvas.fontSizeTitle = 11
        else:
            self.title = "Goodman Plot"
            self.canvas.fontSizeTitle = 15
        self.titleText.SetLabel(self.title)
                
    def set_stresses(self):
        if(self.material_selected and self.cycle_selected):
            self.Sy = stresses[self.material]['Sy']
            self.Su = stresses[self.material]['Su']
            self.Sn = stresses[self.material]['Sn'][self.cycle]

    def run_check(self):
        if not None in (self.Sy, self.Sn, self.path): self.runBtn.Enable()
        
    def read_file(self):
        GN = GoodmanNastran(self.path)
        (self.oavgs, self.oamps) = GN.get_stresses()
        self.loadcase_ids = GN.get_loadcase_ids()
        self.loadcase_id = self.loadcase_ids[0]

    ### Events ###
    def on_run(self, event):
        self.runBtn.SetLabel('Running...')
        for obj in [self.runBtn, self.matList, self.cycList, self.fileText, self.fileBtn]: obj.Disable()
        self.read_file()
        self.draw_graph(self.loadcase_id)
        self.saveBtn.Enable()
        self.runBtn.SetLabel('Complete')

    def on_save(self, event):
        self.canvas.SaveFile()
        self.saveBtn.Disable()

    def on_reset(self, event):
        self.init_vars()
        self.set_graphTitle()
        self.draw_graph(self.loadcase_id)
        self.matList.SetSelection(n=-1)
        self.cycList.SetSelection(n=-1)
        self.fileText.SetLabel('')
        self.fileBtn.SetLabel('Select File')
        self.runBtn.SetLabel('Run Simulation')
        for obj in [self.matList, self.cycList, self.fileText, self.fileBtn]: obj.Enable()
        self.saveBtn.Disable()
        

    def on_matList(self, event):
        self.material = event.GetEventObject().GetStringSelection()
        self.material_selected = True
        self.set_stresses()
        self.set_graphTitle()
        self.draw_graph(self.loadcase_id)
        self.run_check()

    def on_cycList(self, event):
        self.cycle = event.GetEventObject().GetStringSelection()
        self.cycle_selected = True
        self.set_stresses()
        self.set_graphTitle()
        self.draw_graph(self.loadcase_id)
        self.run_check()

    def on_selectFile(self, event):
        dlg = wx.FileDialog(self, message="Select a Nastran (.op2) file",
                            defaultDir = self.dir,
                            wildcard="OP2 files (*.op2*)|*.op2*",
                            style=wx.FD_OPEN|wx.FD_CHANGE_DIR)
        if dlg.ShowModal() == wx.ID_OK:
            self.path = dlg.GetPath()
            self.fileText.SetLabel(os.path.basename(self.path))
            self.fileBtn.SetLabel('Change File')
        dlg.Destroy()
        self.run_check()

    def on_titleUpdate(self, event):
        self.set_graphTitle(self.titleText.GetValue())
        self.draw_graph(self.loadcase_id)

    def on_toggle1(self, event):
        self.caseBtn2.SetValue(False)
        self.loadcase_id = self.loadcase_ids[0]
        self.draw_graph(self.loadcase_id)

    def on_toggle2(self, event):
        self.caseBtn1.SetValue(False)
        self.loadcase_id = self.loadcase_ids[1]
        self.draw_graph(self.loadcase_id)

if __name__ == '__main__':
    init_materials()
    app = wx.App()
    frame = GoodmanFrame(parent=None, title=title, size=size, style=frame_style)
    frame.Show()
    app.MainLoop()
    
