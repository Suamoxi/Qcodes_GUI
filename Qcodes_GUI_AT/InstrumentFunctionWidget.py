# -*- coding: utf-8 -*-
"""
Created on Mon Apr 19 09:41:20 2021

@author: aurel
"""

"""
qcodes/instrument/base.py -> line 263
There u can find a set function for setting paramater defined by "name" to a value defined by "value"
"""

from PyQt5.QtWidgets import QApplication, QWidget, QLineEdit, QPushButton, QLabel, QShortcut, QDesktopWidget, \
    QRadioButton, QButtonGroup, QGroupBox, QHBoxLayout, QGridLayout, QVBoxLayout, QSizePolicy, QComboBox, QTextEdit
from PyQt5.QtCore import Qt, pyqtSlot
from inspect import signature

import sys
import qcodes
from qcodes import Parameter,ChannelList,Instrument
from Helpers import *
from AddNewParameterWidget import AddNewParameterWidget
from ThreadWorker import Worker, progress_func, print_output, thread_complete
from EditInstrumentParametersWidget import EditInstrumentParameterWidget
from qcodes.instrument.base import InstrumentBase


class FunctionWidget(QWidget):

    def __init__(self, instruments, dividers, active, thread_pool,
                 tracked_parameter=None, parent=None, instrument_name="",submodule_name = ""):
        """
        Constructor for EditInstrumentWidget window

        :param instruments: dictionary containing all instruments created in this instance of GUI
        :param dividers: dict of all divider created in this instance of GUI
        :param active: list of all opened instruments windows (one must be able to remove self from that list)
        :param thread_pool: thread managing pool of threads (shared with mainWindow)
        :param tracked_parameter: used for live mode of the instrument, only updates value of this parameter
        :param instrument_name: Name of an instrument to be edited
        :param parent: specify object that created this widget
        :param submodule: Allows to create an editInstrumentWidget for a submodule of an instrument, typically 
        for a Multi Channel Instrument, one window per channel 
        """
        super(FunctionWidget, self).__init__()
        self.parent = parent

        # a dict of all instruments that have been created so far
        self.instruments = instruments
        # a dict of all dividers that have been created so far (to be able to display them if any of them is attached to
        # currently observed instrument
        self.dividers = dividers
        # a list of EditInstrumentWidgets that are currently opened (to be able to remove self from that list)
        self.active = active
        # shared thread pool to be able to run longer actions in separate threads
        self.thread_pool = thread_pool
        # name of the instrument that is currently being edited
        self.instrument_name = instrument_name
        # instance of the instrument that is currently being edited
        self.submodule_name = submodule_name
        
        if self.submodule_name == "":   
            self.instrument = self.instruments[instrument_name]
        
        else:
            self.instrument = self.instruments[instrument_name].submodules[submodule_name]
        #self.instrument = self.instruments[instrument_name].submodule 
        # keep track of workers messing with this window
        self.live = False
        self.worker = None
        self.tracked_parameter = tracked_parameter

        # references to textboxes, because they need to be accessed often, to updated the values if live monitoring of
        # the instrument is turned on
        self.textboxes = {}
        self.textboxes_real_values = {}
        self.textboxes_divided_values = {}
        self.comboboxes = {}
        # references to buttons for editing inner parameters of each instrument parameter
        self.inner_function_btns = {}
        
        #Test to include the possibility of using functions and in the case of multi channels instruments a correct display
        #of all the parameters 
        
        self.modules = self.instrument.__dict__['submodules']
        self.functions = self.instrument.__dict__['functions']
        self.function_dic= {}
        
        self.init_ui()
        self.show()

    """""""""""""""""""""
    User interface
    """""""""""""""""""""
    def init_ui(self):
        """
        Hello

        :return: NoneType
        """
        # define initial position and size of this widget
        # position is defined in relative size to the size of the monitor
        _, _, width, height = QDesktopWidget().screenGeometry().getCoords()
        window_height = len(self.instrument.parameters)*30 + 200
        self.setGeometry((width - 600), int(0.05*height), 580, window_height)
        self.setMinimumSize(320, 260)
        # define title and icon of the widget
        if self.submodule_name == "":
            
            self.setWindowTitle("Functions of " + self.instrument_name.upper() + " instrument")
        else: 
           self.setWindowTitle("Functions of " + self.instrument_name.upper() + " instrument" + "_channel_" + self.submodule_name) 
        self.setWindowIcon(QtGui.QIcon("img/osciloscope_icon.png"))

        self.grid_layout = QGridLayout()
        self.setLayout(self.grid_layout)

        # show the name of the instrument that is being edited
        label = QLabel("Name:")
        self.layout().addWidget(label, 0, 0, 1, 1)
        self.instrument_name_txtbox = QLineEdit(self.instrument_name)
        self.layout().addWidget(self.instrument_name_txtbox, 0, 1, 1, 1)
        self.instrument_name_txtbox.setDisabled(True)

            
                
        # create a row for each of the parameters of this instrument with fields for displaying original and applied
        # values, also field for editing, and buttons for geting and seting a value
        start_y = 80
        row = 1
        column = 0
        
        
        functions_to_show = retrieve_function_list(self.instrument)
                
        for string_call in functions_to_show:
            if callable(eval('self.instrument' + f'.{string_call}')):
                self.function_dic[string_call] = eval('self.instrument' + f'.{string_call}')
                
        
        
                
                
        
        for name, function in self.function_dic.items():
            label = QLabel(name, self)
            self.layout().addWidget(label, row+1, column, 1, 1)

            # create activate button for every inner function
            self.inner_function_btns[name] = QPushButton("Activate" + name, self)
            self.layout().addWidget(self.inner_function_btns[name], row+1, column+ 1, 1, 1)
            #connect the edit button ? Do I need to keep it ? 
            self.inner_function_btns[name].clicked.connect(self.make_activate_function(name))
          
            
            sig = signature(function)
            params = sig.parameters
            
            
            
            if len(params):
                inner_column = column
                for param_name in params.keys():
                    param_label = QLabel(param_name, self)
                    self.layout().addWidget(param_label, row, inner_column + 2, 1, 1)  
                    self.textboxes[name + '_' + param_name]= QLineEdit(self)
                    self.layout().addWidget(self.textboxes[name + '_' + param_name], row +1, inner_column +2 , 1, 1)
                    inner_column += 1
            
                    
            if name not in self.instrument.functions:
                function_doc = QTextEdit(str(function.__doc__),self)    
                self.layout().addWidget(function_doc,row+2,column,1,-1)
            
                        
            start_y += 25
            row += 3
            if row > 12:
                row = 1
                column += 10
        
         
        # if u click this button u get a house and a car on Bahamas, also your partner suddenly becomes the most
        # attractive person in the world, in addition to this you get a Nobel prize for whatever u want ... Easy life
        ok_btn = QPushButton("Close", self)
        self.layout().addWidget(ok_btn, row+1, 6, 1, 1)
        ok_btn.clicked.connect(self.close)

        close_shortcut = QShortcut(QtGui.QKeySequence(Qt.Key_Escape), self)
        close_shortcut.activated.connect(self.close)

    """""""""""""""""""""
    Data manipulation
    """""""""""""""""""""
    
    
    def changeText(self, name):
        """
        

        Parameters
        ----------
        name : Parameter name, used to reference combobox and Qlineedit

        Returns
        -------
        Change the QLineEdit text of a parameter to the value choose in the combobox,
        restraining the user from entering non valid values

        """
        value = str(self.comboboxes[name].currentText())
        
        self.textboxes[name].setText(value)
    
    
    def make_activate_function(self, name):
        """
        Function factory that creates function for each of the activate buttons. Takes in name of the instrument_function
        and passes it to the inner function. Function returns newly created function.

        :param name: name of the instrument_function that is being activated
        :return: function that calls the instrument_function
        """

        def call_function():
            """
            Fetches the args from textbox belonging to the corresponding arg and call the function with those arguments

            If none arguments just call the instrument_function 

            :return: NoneType
            """
            function = self.function_dic[name]
            parameters = []
            
            
            try:
                
                for key,value in self.textboxes.items():
                    
                    if name in key:
                        Param_value = value.text()
                        
                        if is_numeric(Param_value):
                            
                            parameters.append(float(Param_value))
                        else:
                            parameters.append(Param_value)
                
                
                
                function(*parameters)
                
            except:
                try:
                    function()
                except Exception as e:
                    show_error_message("Warning", str(e))
                    
                    
                
                
            
            #else:
             #   self.update_parameters_data()
        
        
        return call_function

    


    """""""""""""""""""""
    Helper functions
    """""""""""""""""""""
    def call_worker(self, func):
        """
        Function factory for instantiating worker objects that run a certain function in a separate thread

        :param func:
        :return:
        """
        def instantiate_worker():
            # creata a new worker, False meaning that it is not a looping worker, it only does its thing once
            worker = Worker(func, False)
            worker.signals.result.connect(print_output)
            worker.signals.finished.connect(thread_complete)
            worker.signals.progress.connect(progress_func)

            self.thread_pool.start(worker)

        return instantiate_worker

    def closeEvent(self, a0: QtGui.QCloseEvent):
        # overriding close method to remove self from list of active windows, obviously if one is closed, one is no
        # longer active, is that obvious only to me ? It should be to everyone right ? Right ?
        self.active.remove(self)

    def toggle_live(self):
        # if the widget is currently in live mode, turn of the live mode and kill all+delete all workers.
        if self.live:
            self.worker.stop_requested = True
            self.go_live_btn.setText("Go live")
            self.worker = None
            for tb in self.textboxes:
                self.textboxes[tb].setDisabled(False)
            self.live = False
        # if the widget is currently in non-live mode, go live mode, create worker, and start it
        else:
            self.go_live_btn.setText("STOP")
            if len(self.parent.actions):
                self.tracked_parameter = self.parent.actions[-1].sweep_values.name
            for tb in self.textboxes:
                self.textboxes[tb].setDisabled(True)
            self.worker = Worker(self.update_parameters_data, True)
            self.thread_pool.start(self.worker)
            self.live = True


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = FunctionWidget({})
    sys.exit(app.exec_())
