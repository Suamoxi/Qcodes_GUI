"""
qcodes/instrument/base.py -> line 263
There u can find a set function for setting paramater defined by "name" to a value defined by "value"
"""

from PyQt5.QtWidgets import QApplication, QWidget, QLineEdit, QPushButton, QLabel, QShortcut, QDesktopWidget, \
    QRadioButton, QButtonGroup, QGroupBox, QHBoxLayout, QGridLayout, QVBoxLayout, QSizePolicy, QComboBox
from PyQt5.QtCore import Qt, pyqtSlot

import sys
import qcodes
from qcodes import Parameter,ChannelList,Instrument
from Helpers import *
from AddNewParameterWidget import AddNewParameterWidget
from ThreadWorker import Worker, progress_func, print_output, thread_complete
from EditInstrumentParametersWidget import EditInstrumentParameterWidget

from qcodes.instrument.base import InstrumentBase

import numpy as np

class EditInstrumentWidget(QWidget):

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
        super(EditInstrumentWidget, self).__init__()
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
            self.instrument = self.instruments[instrument_name].__dict__['submodules'][submodule_name]
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
        self.inner_parameter_btns = {}
        
        #Test to include the possibility of using functions and in the case of multi channels instruments a correct display
        #of all the parameters 
        
        self.modules = self.instrument.__dict__['submodules']
        self.functions = self.instrument.__dict__['functions']
        
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
            
            self.setWindowTitle("Edit " + self.instrument_name.upper() + " instrument")
        else: 
           self.setWindowTitle("Edit " + self.instrument_name.upper() + " instrument" + "_channel_" + self.submodule_name) 
        self.setWindowIcon(QtGui.QIcon("img/osciloscope_icon.png"))

        self.grid_layout = QGridLayout()
        self.setLayout(self.grid_layout)

        # show the name of the instrument that is being edited
        label = QLabel("Name:")
        self.layout().addWidget(label, 0, 0, 1, 1)
        self.instrument_name_txtbox = QLineEdit(self.instrument_name)
        self.layout().addWidget(self.instrument_name_txtbox, 0, 1, 1, 1)
        self.instrument_name_txtbox.setDisabled(True)

        # button to start live updating of the parameters of this instrument
        self.go_live_btn = QPushButton("Go live", self)
        self.go_live_btn.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.layout().addWidget(self.go_live_btn, 0, 5, 2, 2)
        self.go_live_btn.clicked.connect(self.toggle_live)

        label = QLabel("Original", self)
        self.layout().addWidget(label, 2, 3, 1, 1)
        label = QLabel("Applied", self)
        self.layout().addWidget(label, 2, 4, 1, 1)


        
            
                
        # create a row for each of the parameters of this instrument with fields for displaying original and applied
        # values, also field for editing, and buttons for geting and seting a value
        start_y = 80
        row = 3
        column = 0
        
        
        #params_to_show = create_params_to_show(self.instrument)
        params_to_show = self.instrument.parameters
        for name, parameter in params_to_show.items():
            label = QLabel(name, self)
            self.layout().addWidget(label, row, column, 1, 1)

            # create edit button for every inner parameter
            self.inner_parameter_btns[name] = QPushButton("Edit " + name, self)
            self.layout().addWidget(self.inner_parameter_btns[name], row, column+ 1, 1, 1)
            self.inner_parameter_btns[name].clicked.connect(self.make_edit_parameter(name))
            
            
            val = 0
                    
            if parameter.gettable ==  True:
                
                if parameter.settable == True:
                     
                    if isinstance(parameter.vals,qcodes.utils.validators.Validator):
                         try:
                             val = parameter.get_latest() 
                             
                         except Exception as e:
                             
                             show_error_message("Warning", str(e))
                             
                             
                         if isinstance(parameter.vals,qcodes.utils.validators.Enum):
                             self.comboboxes[name] = QComboBox(self)
                             self.layout().addWidget(self.comboboxes[name],row,column+ 2, 1, 1)
                             for i in parameter.vals._valid_values:
                                 j = str(i)
                                 self.comboboxes[name].addItem(j,i)
                                 
                             
                             self.textboxes[name] = QLineEdit(str(val), self)
                             self.layout().addWidget(self.textboxes[name], row,column+ 4, 1, 1)   
                             self.textboxes[name].setDisabled(True)
                             
                             
                             self.textboxes_real_values[name] = QLineEdit(str(val), self)
                             self.layout().addWidget(self.textboxes_real_values[name], row, column+3, 1, 1)
                             self.textboxes_real_values[name].setDisabled(True)
                             
                             self.comboboxes[name].currentIndexChanged.connect(lambda checked, parameter_name=name: self.changeText(parameter_name))
                             
                         elif isinstance(parameter.vals,qcodes.utils.validators.Bool):
                             self.comboboxes[name] = QComboBox(self)
                             self.layout().addWidget(self.comboboxes[name],row,column+ 2, 1, 1)
                             for i in parameter.vals._valid_values:
                                 j = str(i)
                                 self.comboboxes[name].addItem(j,i)
                                 
                             
                             self.textboxes[name] = QLineEdit(str(val), self)
                             self.layout().addWidget(self.textboxes[name], row,column+ 4, 1, 1)   
                             self.textboxes[name].setDisabled(True)
                             
                             
                             self.textboxes_real_values[name] = QLineEdit(str(val), self)
                             self.layout().addWidget(self.textboxes_real_values[name], row, column+3, 1, 1)
                             self.textboxes_real_values[name].setDisabled(True)
                             
                             self.comboboxes[name].currentIndexChanged.connect(lambda checked, parameter_name=name: self.changeText(parameter_name))
                            
                         else:    
                            
                    
                            # display values that are currently set to that instruments inner parameter
                            self.textboxes_real_values[name] = QLineEdit(str(val), self)
                            self.layout().addWidget(self.textboxes_real_values[name], row,column+ 3, 1, 1)
                            self.textboxes_real_values[name].setDisabled(True)
            
                        # if that parameter has divider attached to it, display additional text box
                            if str(parameter) in self.dividers:
                                self.textboxes_divided_values[name] = QLineEdit(str(np.format_float_scientific(self.dividers[str(parameter)].get_raw(), 3)),
                                                                                self)
                                self.layout().addWidget(self.textboxes_divided_values[name], row,column+ 2, 1, 1)
                                self.textboxes_divided_values[name].setDisabled(True)
                     
                            else:
                                self.textboxes[name] = QLineEdit(str(val), self)
                                self.layout().addWidget(self.textboxes[name], row, column+4, 1, 1)
                     
                    #If the parameter has no validator set, ask the user to modify the driver to update a validator
                    # Even if the driver isn't modified allows to try to get a value
                    # Show messages link to the Visa errors that might occur, mostly for Curr/Volt sources, 
                    # Don't block everything if this kind of errors pop up 
                    
                    
                    
                    else:
                         show_error_message("Warning", f"Modify the instrument driver and add the right validator for the parameter {name}")
                         try:
                             
                             val = self.instrument.parameters[name].get_latest()
                             self.textboxes[name] = QLineEdit(str(val), self)
                             self.layout().addWidget(self.textboxes[name], row,column+ 4, 1, 1)
                             
                             
                         except Exception as e:
                             show_error_message("Warning", str(e))
            
            
                
            # show set button if that parameter is settable
            if hasattr(parameter, "set"):
                set_value_btn = QPushButton("Set", self)
                self.layout().addWidget(set_value_btn, row, column+5, 1, 1)
                set_value_btn.clicked.connect(self.make_set_parameter(name))
           
            # show get button if that parameter is gettable
            if hasattr(parameter, "get"):
                get_value_btn = QPushButton("Get", self)
                self.layout().addWidget(get_value_btn, row, column+6, 1, 1)
                get_value_btn.clicked.connect(lambda checked, parameter_name=name: self.update_parameters_data(parameter_name))
            
            
            start_y += 25
            row += 1
            
            if row > 20:
                row_1 = row
                row = 3
                column += 7
                
        row = 21
        
        add_new_parameter_btn = QPushButton("Add parameter", self)
        add_new_parameter_btn.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.layout().addWidget(add_new_parameter_btn, row, 0, 2, 2)
        add_new_parameter_btn.clicked.connect(self.add_new_parameter)
        
        
        """
        # U can read right ?
        set_all_to_zero_btn = QPushButton("All zeroes", self)
        self.layout().addWidget(set_all_to_zero_btn, row, 6, 1, 1)
        set_all_to_zero_btn.clicked.connect(self.call_worker(self.set_all_to_zero))
        """
        # Sets all to values currently displayed in the text boxes that are editable
        set_all_btn = QPushButton("SET ALL", self)
        set_all_btn.hide()
        self.layout().addWidget(set_all_btn, row, 5, 1, 1)
        
        # set_all_btn.clicked.connect(self.call_worker(self.set_all))
        set_all_btn.clicked.connect(self.set_all)

        # gets all parameters and updates the displayed values
        get_all_btn = QPushButton("GET ALL", self)
        self.layout().addWidget(get_all_btn, row+1, 5, 1, 1)

        get_all_btn.clicked.connect(self.call_worker(self.update_parameters_data))

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
    
    
    def make_set_parameter(self, parameter_name):
        """
        Function factory that creates function for each of the set buttons. Takes in name of the instrument parameter
        and passes it to the inner function. Function returns newly created function.

        :param parameter_name: name of the parameter that is being set
        :return: function that sets the parameter
        """

        def set_parameter():
            """
            Fetches the data from textbox belonging to the parameter (data set by user) and sets the parameter value
            to that data.

            Added handling with dividers attached (add detailed explanation)

            :return: NoneType
            """
            # full name is composed of the instrument name and parameter name (Example: IVVI_dac1)
            full_name = str(self.instrument.parameters[parameter_name])
            parameter = self.instrument.parameters[parameter_name]
            value = self.textboxes[parameter_name].text()
            
            try:
                set_value = value
    
                if is_numeric(set_value):
                    if hasattr(parameter, "set"):
                        worker = Worker(lambda: self.instrument.set(parameter.name, float(set_value)), False)
                        worker.signals.finished.connect(lambda: self.update_parameters_data(parameter_name))
                        self.thread_pool.start(worker)
                    else:
                        show_error_message("Warning", "Parameter {} does not have a set function".format(full_name))
                        
                elif is_bool(set_value):
                    if hasattr(parameter, "set"):
                        worker = Worker(lambda: self.instrument.set(parameter.name, eval(set_value)), False)
                        worker.signals.finished.connect(lambda: self.update_parameters_data(parameter_name))
                        self.thread_pool.start(worker)
                    else:
                        show_error_message("Warning", "Parameter {} does not have a set function".format(full_name))
                else:
                    if hasattr(parameter, "set"):
                        worker = Worker(lambda: self.instrument.set(parameter.name, set_value), False)
                        worker.signals.finished.connect(lambda: self.update_parameters_data(parameter_name))
                        self.thread_pool.start(worker)
                
            except Exception as e:
                show_error_message("Warning", str(e))
            
            #else:
             #   self.update_parameters_data()
        
        
        return set_parameter

    def make_edit_parameter(self, parameter):
        """
        Function factory for creating functions that open new window for editing parameters of an instrument

        :param parameter: name of the parameter to be edited
        :return: reference to a function "edit_instrument"
        """
        def edit_parameter():
            self.edit_instrument_parameters = EditInstrumentParameterWidget(self.instruments, self.instrument,
                                                                            parameter, self.dividers, parent=self)
            self.edit_instrument_parameters.show()

        return edit_parameter

    def make_set_polarity(self, group_id, dacs):

        def set_polarity():
            mapping = {0: "NEG", 1: "BIP", 2: "POS"}
            polarity = mapping[self.group[group_id].checkedId()]
            self.instrument.set_pol_dacrack(polarity, dacs)
            self.dac_polarities[group_id].setText(polarity)

        return set_polarity
    
    
    
    
    def update_parameters_data(self, name=None):
        """
        Updates values of all parameters after a change has been made. Implements data validation (has to be number)
        Also used to "Get all", well, cause it gets all ... :/

        If name is passed update only value of that single parameter

        :param name: if this parameter is set to something(string) get the value of only that single parameter
        :return: NoneType
        """
        if name is not None:
            full_name = str(self.instrument.parameters[name])
            
            
            
            if full_name in self.dividers:
                self.textboxes[name].setText(str(np.format_float_scientific(self.instrument.parameters[name].get_latest() / self.dividers[full_name].division_value, 3)))
                      
            else:
                if is_numeric(self.instrument.parameters[name].get_latest()):
                    self.textboxes[name].setText(str(np.format_float_scientific(self.instrument.parameters[name].get_latest(), 3)))
                
                    

                else:
                     self.textboxes[name].setText(str(self.instrument.parameters[name].get_latest()))
                
                
               
            if is_numeric(self.instrument.parameters[name].get_latest()):
                self.textboxes_real_values[name].setText(str(np.format_float_scientific(self.instrument.parameters[name].get_latest(), 3)))
            
            else:
           
                self.textboxes_real_values[name].setText(str(self.instrument.parameters[name].get_latest()))
                
                
        else:
            for name, textbox in self.textboxes.items():
                full_name = str(self.instrument.parameters[name])
                if full_name in self.dividers:
                    textbox.setText(str(np.format_float_scientific(self.instrument.parameters[name].get_latest() / self.dividers[full_name].division_value, 3)))
                else:
                    """
                    if is_numeric(self.instrument.parameters[name].get_latest()):
                        textbox.setText(str(np.format_float_scientific(float(self.instrument.parameters[name].get_latest()), 3)))
                    else:
                    """
                    textbox.setText(str(self.instrument.parameters[name].get_latest()))
                    
                   
            for name, textbox in self.textboxes_real_values.items():
               
                if is_numeric(self.instrument.parameters[name].get_latest()):
                    textbox.setText(str(np.format_float_scientific(float(self.instrument.parameters[name].get_latest()), 3)))
                else:
                    if is_numeric(self.instrument.parameters[name].get_latest()):
                        textbox.setText(str(np.format_float_scientific(float(self.instrument.parameters[name].get_latest()), 3)))
                    else:
                
                        textbox.setText(str(self.instrument.parameters[name].get_latest()))
              
            self.update_divided_values()

    def single_update(self):

        # used to live update only a single parameter that is being swept by the currently running loop
        if self.tracked_parameter is not None:
            self.update_parameters_data(self.tracked_parameter)

    def update_divided_values(self):
        for name, textbox in self.textboxes_divided_values.items():
            # get values from the divider
            param = self.instrument.parameters[name]
            divider = self.dividers[str(param)]
            textbox.setText(str(np.format_float_scientific(param.get_latest()/divider.division_value, 3)))

    def set_all_to_zero(self):
        """
        Set value of all numeric type parameters to be zero

        :return: NoneType
        """
        # some instruments already have this method implemented, so why bother, on the other hand, some instruments
        # dont have it so i have to implement it anyway, wow, im so smart
        if hasattr(self.instrument, "set_dacs_zero"):
            self.instrument.set_dacs_zero()
        else:
            for name, parameter in self.instrument.parameters.items():
                if is_numeric(self.instrument.parameters[name].get()):
                    if name[0:3] == "dac" and len(name) == (4 or 5):
                        self.instrument.set(name, 0)
                    else:
                        if hasattr(parameter, "set"):
                            self.instrument.set(name, 0)

        self.hard_update_parameters_data()

    def set_all(self):
        """
        Sets and updates displayed values for all parameters at the same time (if multiple parameters were edited)

        :return: NoneType
        """
        for name, parameter in self.instrument.parameters.items():
            if hasattr(self.instrument.parameters[name], "set"):
                if name in self.textboxes:
                    full_name = str(self.instrument.parameters[name])
                    value = self.textboxes[name].text()
                    try:
                        is_valid = False
                        if hasattr(parameter.vals, "validtypes"):
                            for data_type in parameter.vals.validtypes:
                                try:
                                    set_value = data_type(value)
                                except:
                                    continue
                                else:
                                    is_valid = True
                                    break
                        elif hasattr(parameter.vals, "_valid_values"):
                            data_types = list(set([type(value) for value in parameter.vals._valid_values]))
                            for data_type in data_types:
                                try:
                                    set_value = data_type(value)
                                except:
                                    continue
                                else:
                                    is_valid = True
                                    break
                        else:
                            is_valid = True
                            set_value = value

                        if is_valid:
                            if hasattr(parameter, "set"):
                                self.instrument.set(parameter.name, set_value)
                            else:
                                show_error_message("Warning", "Parameter {} does not have a set function".format(full_name))
                        else:
                            show_error_message("Warning",
                                               "Value [ {} ] is not in the list of allowed values for parameter [ {} ]".
                                               format(value, full_name))
                    except Exception as e:
                        show_error_message("Warning", str(e))
        self.update_parameters_data()

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

    @pyqtSlot()
    def add_new_parameter(self):
        self.add_new_param_widget = AddNewParameterWidget(self.instrument, self.instruments, self.dividers, parent=self)
        self.add_new_param_widget.show()

    def reinit_dacs(self):

        if self.instrument.reinitialize_dacs() == [82, 73, 97, 68]:
            print("reinitialized")
        else:
            show_error_message("Warning", "Oops something went wrong.")

    def hard_update_parameters_data(self):
        for name, textbox in self.textboxes.items():
            full_name = str(self.instrument.parameters[name])
            if full_name in self.dividers:
                value = np.format_float_scientific(self.instrument.parameters[name].get_raw(), 3)
                divided_value = np.format_float_scientific(self.dividers[full_name].get(), 3)
                self.textboxes_divided_values[name].setText(str(divided_value))
            else:
                if is_numeric(self.instrument.parameters[name].get()):
                    value = np.format_float_scientific(float(self.instrument.parameters[name].get_latest()), 3)
                else:
                    value = self.instrument.parameters[name].get_latest()
            self.textboxes[name].setText(str(value))
            self.textboxes_real_values[name].setText(str(value))
    """
    def create_params_to_show(Instrument_instance):
        if isinstance(Instrument_instance, InstrumentBase):
            params_to_show= {}    
            Submodules = Instrument_instance.__dict__['submodules']
            Functions = Instrument_instance.__dict__['functions']
            if Submodules == {}:
                params_to_show = Instrument_instance.parameters
                return params_to_show
            else:
                            
                for i,j in Submodules.items():
                            
                            if isinstance(j,ChannelList):
                                A = 0
                            else: 
                                
                                #name_submodule = nameof(i)
                                #A = f'{instrument_name}'+f'.{i}.parameters'
                                dic_submodule_parameters = getattr(Instrument_instance,i).parameters
                                for parameter in dic_submodule_parameters.keys():
                                    if isinstance(dic_submodule_parameters[parameter], Parameter):
                                        params_to_show[i+ '.' + parameter] =  dic_submodule_parameters[parameter]
                return params_to_show
              
        else:
            print('Error:Unvalid instrument')
    """

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = EditInstrumentWidget({})
    sys.exit(app.exec_())
