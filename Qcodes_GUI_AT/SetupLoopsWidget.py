# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import QApplication, QWidget, QLineEdit, QPushButton, QLabel, QComboBox, QDesktopWidget, QShortcut, \
    QGridLayout, QVBoxLayout, QHBoxLayout, QSizePolicy
from PyQt5.QtCore import Qt

import sys

from Helpers import *
import qcodes as qc
from qcodes.actions import _QcodesBreak
from qcodes.actions import Task
from qcodes.loops import ActiveLoop, Loop
from qcodes.instrument.base import Instrument,InstrumentBase
from qcodes.instrument_drivers.devices import VoltageDivider


class LoopsWidget(QWidget):

    def __init__(self, instruments, dividers, loops, actions, parent=None, loop_name=""):
        """
        Constructor for AddInstrumentWidget window

        :param instruments: Dictionary shared with parent (MainWindow) to be able to add instruments to instruments
        dictionary in the MainWindow
        :param dividers: dictionary shared with main window, contains all dividers created so far
        :param loops: shared with main window, dict of all created loops
        :param actions: list of loops that can be ran in order of creation
        :param parent: specify object that created this widget
        :param loop_name: If passed, opens the window with data field filed by that particular loops data
        """
        super(LoopsWidget, self).__init__()

        self.instruments = instruments
        self.dividers = dividers
        self.loops = loops
        self.actions = actions
        self.parent = parent
        self.parent.loop_started.connect(self.disable_changes)
        self.parent.loop_finished.connect(self.enable_changes)
        self.name = loop_name

        # dictionary contining all loop actions that should be appended to the loop. Format: key : value
        # where: key is a string composed of word action and a number of that action (action1, action2, ...
        #           (this is not that important),
        #        value is a list in format: [instrument, parameter, division] containing reference to an instrument,
        #           and the parameter of that instrument (i might not need both of these) and finally a division value
        self.current_loop_actions_dictionary = {}

        # dict of remove buttons
        self.remove_buttons = {}

        # if loop name has been passed then grab that loop from loops dictionary, create a list to hold loop values, and
        # call a method that gets that data
        if self.name != "":
            self.loop = self.loops[self.name]
            self.loop_values = []
            self.get_loop_data()
            # [lower, upper, steps, delay, sweep, sweep_division, action, action_division]
        self.init_ui()
        self.show()

    """""""""""""""""""""
    User interface
    """""""""""""""""""""
    def init_ui(self):
        """
        Initializes user interface for LoopsWidget class

        :return: NoneType
        """
        # set starting position of window relative to the size of the screen
        _, _, width, height = QDesktopWidget().screenGeometry().getCoords()
        self.width = 400
        self.height = 340
        self.setGeometry(int(0.05*width) + 620, int(0.05*height), self.width, self.height)
        self.setMinimumSize(400, 340)
        if self.name != "":
            self.setWindowTitle("Editing {}".format(self.name))
        else:
            self.setWindowTitle("Setup loops")
        self.setWindowIcon(QtGui.QIcon("img/osciloscope_icon.png"))

        self.grid_layout = QVBoxLayout()
        self.setLayout(self.grid_layout)

        # label above input fields and tooltips to be shown on mouseover
        labels = ["Start", "Swap", "End", "Steps", "Step size", "Delay"]
        tooltips = ["Start from this value",
                    "Change start and stop",
                    "Sweep to this value",
                    "Number of steps to be measured from lower limit to upper limit",
                    "Either this or steps is to be used",
                    "Wait this many seconds between each step"]

        label = QLabel("Parameters")
        self.layout().addWidget(label)
        h_layout_labels = QHBoxLayout()
        for i in range(len(labels)):
            label = QLabel(labels[i])
            h_layout_labels.addWidget(label)
            label.setToolTip(tooltips[i])
        self.layout().addLayout(h_layout_labels)

        h_layout_lineedits = QHBoxLayout()

        # add text boxes for parameters of the loop
        self.textbox_lower_limit = QLineEdit()
        self.textbox_lower_limit.setText("0")
        h_layout_lineedits.addWidget(self.textbox_lower_limit)
        self.switch_btn = QPushButton("<>")
        h_layout_lineedits.addWidget(self.switch_btn)
        self.switch_btn.clicked.connect(self.switch_upper_and_lower)
        self.textbox_upper_limit = QLineEdit()
        self.textbox_upper_limit.setText("0")
        h_layout_lineedits.addWidget(self.textbox_upper_limit)
        
        # number of steps
        self.textbox_num = QLineEdit()
        self.textbox_num.setText("1")
        h_layout_lineedits.addWidget(self.textbox_num)
        
        # can use this insted of number of steps
        self.textbox_step_size = QLineEdit()
        self.textbox_step_size.setText("1")
        h_layout_lineedits.addWidget(self.textbox_step_size)
        
        # this is actualy a delay (NOT STEPS !)
        self.textbox_step = QLineEdit()
        self.textbox_step.setText("0")
        h_layout_lineedits.addWidget(self.textbox_step)
        self.layout().addLayout(h_layout_lineedits)

        # comboboxes for selecting sweep parameter instrument. First you select the instrument that you want to sweep
        # After selecting instrument the other combobox is populated by parameters of that instrument
        label = QLabel("Sweep parameter:")
        self.layout().addWidget(label)
        h_layout_sweep = QHBoxLayout()
        self.sweep_parameter_instrument_cb = QComboBox()
        h_layout_sweep.addWidget(self.sweep_parameter_instrument_cb)
        self.sweep_parameter_instrument_cb.setToolTip("Please select instrument to sweep from")
        
        
        for name, instrument in self.instruments.items():
            display_member = name
            value_member = instrument
            self.sweep_parameter_instrument_cb.addItem(display_member, value_member)
            
        # combobox for selecting module/chan in case of multi chan instrument 
        self.sweep_module_cb = QComboBox()
        h_layout_sweep.addWidget(self.sweep_module_cb)
        self.sweep_module_cb.setToolTip("Please select channel to sweep")
        self.layout().addLayout(h_layout_sweep)
        
        # combobox for selecting parameter
        self.sweep_parameter_cb = QComboBox()
        h_layout_sweep.addWidget(self.sweep_parameter_cb)
        self.sweep_parameter_cb.setToolTip("Please select parameter to sweep")
        self.layout().addLayout(h_layout_sweep)
        
        
        # ####self.update_sweep_instrument_parameters()
        # Add divider to sweep parameter

        div_layout = QVBoxLayout()
        label = QLabel("Divider")
        div_layout.addWidget(label)
        label.setToolTip("Add division/amplification to the instrument being swept")
        self.sweep_parameter_divider = QLineEdit("1")
        self.sweep_parameter_divider.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        div_layout.addWidget(self.sweep_parameter_divider)
        self.sweep_parameter_divider.setDisabled(True)
        h_layout_sweep.addLayout(div_layout)
        self.layout().addLayout(h_layout_sweep)

        self.actions_v_layout = QVBoxLayout()

        label = QLabel("Loop action parameter:")
        self.layout().addWidget(label)
        add_parameter = QPushButton("Add action parameter")
        self.layout().addWidget(add_parameter)
        add_parameter.clicked.connect(self.add_parameter)
        
        # same logic as sweep parameter (see line 110)
        h_layout_action = QHBoxLayout()
        self.action_parameter_instrument_cb = QComboBox(self)
        h_layout_action.addWidget(self.action_parameter_instrument_cb)
        for name, instrument in self.instruments.items():
            display_member = name
            value_member = instrument
            self.action_parameter_instrument_cb.addItem(display_member, value_member)
        
        
        # combobox for selecting module/chan in case of multi chan instrument 
        self.action_module_cb = QComboBox()
        h_layout_action.addWidget(self.action_module_cb)
        
        # combobox for selecting parameter
        self.action_parameter_cb = QComboBox(self)
        h_layout_action.addWidget(self.action_parameter_cb)
        
        
        
        
        # add loops to combobox (loop can also be an action of another loop)
        for name, loop in self.loops.items():
            display_member_string = "[" + name + "]"
            data_member = loop
            self.action_parameter_instrument_cb.addItem(display_member_string, data_member)
            
        # divider for action parameter
        div_layout = QVBoxLayout()
        label = QLabel("Divider", self)
        div_layout.addWidget(label)
        label.setToolTip("Add division/amplification to the instrument")
        self.action_parameter_divider = QLineEdit("1", self)
        self.action_parameter_divider.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        div_layout.addWidget(self.action_parameter_divider)
        self.action_parameter_divider.setDisabled(True)
        h_layout_action.addLayout(div_layout)
        self.actions_v_layout.addLayout(h_layout_action)
        self.layout().addLayout(self.actions_v_layout)
        
        
        # Creates a loop from user input data/// really ???? Or allows to create a loop from user input ????
        action_name = "action" + str(len(self.current_loop_actions_dictionary))
        
        
        self.current_loop_actions_dictionary[action_name] = [self.action_parameter_instrument_cb,
                                                             self.action_parameter_cb,
                                                             self.action_parameter_divider,
                                                             self.action_module_cb]
        
        
        # after adding all combo boxes update displayed data for module and action paramaters
        self.update_action_instrument_modules(action_name)
      
        
        # after adding all combo boxes update displayed data for module and sweep parameters
        self.update_sweep_instrument_modules()
       
        
        
        # Add a button for creating a loop
        if self.name != "":
            text = "Save changes"
        else:
            text = "Create loop"
        self.add_loop_btn = QPushButton(text, self)
        self.layout().addWidget(self.add_loop_btn)
        self.add_loop_btn.setToolTip("Create a loop with chosen parameters")

        # connect actions to buttons and combo boxes after everything has been set up
        self.add_loop_btn.clicked.connect(self.create_loop)
        self.textbox_num.editingFinished.connect(self.update_step_size)
        self.textbox_step_size.editingFinished.connect(self.update_num_of_steps)
        
        
        
        
        
        self.sweep_parameter_instrument_cb.currentIndexChanged.connect(self.update_sweep_instrument_modules)
        
        
        self.sweep_module_cb.activated.connect(self.update_sweep_instrument_parameters)
        
        
        self.action_parameter_instrument_cb.currentIndexChanged.connect(lambda checked, act_name="action0": self.update_action_instrument_modules(act_name))
                
             
        self.action_module_cb.activated.connect(lambda checked, act_name="action0": self.update_action_instrument_parameters(act_name))
            

        
            
            
        self.action_parameter_cb.currentIndexChanged.connect(self.update_divider_value)
        self.sweep_parameter_cb.currentIndexChanged.connect(self.update_divider_value)

        # if the loop name has been passed to the widget, fill the fields with required data (obtained from the loop)
        if self.name != "":
            self.fill_loop_data()

        # shortcuts for certain actions
        close_shortcut = QShortcut(QtGui.QKeySequence(Qt.Key_Escape), self)
        close_shortcut.activated.connect(self.close)

    def add_parameter(self):
        """
        Expand the window to with new elements that will represent new action. After adding elements for a new action
        fill those elements with data (to be able to select the instrument/parameter/division), and add pointers to
        those elements to a dictionary (self.current_loop_actions_dictionary) to be able to access them later

        Division is set by adding a divider to a parameter that is intendet to have it

        :return: NoneType
        """

        horizontal_layout = QHBoxLayout()
        # self.resize(self.width, self.height + 20)
        self.height += 29
        self.resize(self.width, self.height)

        # remove action button
        remove_action_btn = QPushButton("x")
        remove_action_btn.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        active_actions = 0
        for name, action in self.current_loop_actions_dictionary.items():
            if action is not None:
                active_actions += 1
        horizontal_layout.addWidget(remove_action_btn)

        # create combo box for selecting an instrument
        action_parameter_instrument_cb = QComboBox()
        horizontal_layout.addWidget(action_parameter_instrument_cb)
        
        
        # fill instrument combo box with instrument names
        for name, instrument in self.instruments.items():
            display_member = name
            value_member = instrument
            action_parameter_instrument_cb.addItem(display_member, value_member)
        
        

        # add loops to combobox (loop can also be an action of another loop)
        for name, loop in self.loops.items():
            display_member_string = "[" + name + "]"
            data_member = loop
            action_parameter_instrument_cb.addItem(display_member_string, data_member)
        
        # combobox for selecting module
        action_module_cb = QComboBox()
        horizontal_layout.addWidget(action_module_cb)

        # combobox for selecting parameter
        action_parameter_cb = QComboBox()
        horizontal_layout.addWidget(action_parameter_cb)
        # divider for action parameter
        action_parameter_divider = QLineEdit("1")
        action_parameter_divider.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        horizontal_layout.addWidget(action_parameter_divider)
        action_parameter_divider.setDisabled(True)

        # save action with a name: action# where # is number of loops created so far

        index = str(len(self.current_loop_actions_dictionary))
        action_name = "action" + index
        
        
        action_parameter_instrument_cb.currentIndexChanged.connect(lambda checked,
                                                                          act_name=action_name:
                                                                   self.update_action_instrument_modules(act_name))
        
        action_module_cb.activated.connect(lambda checked,
                                                                          act_name=action_name:
                                                                   self.update_action_instrument_parameters(act_name))    
            
            
        remove_action_btn.clicked.connect(lambda checked,
                                                 act_name=action_name:
                                          self.remove_parameter(act_name))

        # add pointers to elements of the window representing newly created action
        self.current_loop_actions_dictionary[action_name] = [action_parameter_instrument_cb,
                                                             action_parameter_cb,
                                                             action_parameter_divider,
                                                             action_module_cb,
                                                             horizontal_layout]
        
        action_parameter_cb.currentIndexChanged.connect(self.update_divider_value)
        self.remove_buttons[action_name] = remove_action_btn

        # update only newly created combo boxes
        self.update_action_instrument_modules(action_name=action_name)
        self.actions_v_layout.addLayout(horizontal_layout)

    def remove_parameter(self, action_name):
        """
        If a parameter needs to be removed from the loop this method gets all elements that are used to represent that
        parameter and removes them from the UI. Repositions other elements and resizes the window.

        :param action_name: a list of elements that will be removed from the UI

        :return: NoneType
        """
        # delete the elements after the control has been returned to the GUI thread
        for element in self.current_loop_actions_dictionary[action_name]:
            element.deleteLater()
        # set that action to None
        self.current_loop_actions_dictionary[action_name] = None
        # remove the button for deleting that action
        self.remove_buttons[action_name].deleteLater()
        self.height -= 29
        self.resize(self.width, self.height)

    """""""""""""""""""""
    Data manipulation
    """""""""""""""""""""
    def create_loop(self):
        """
        Creates a new loop from data input by user. Adds newly created loop to "loops" dictionary in MainWindow.
        Creates action to be executed upon running qcodes and adds it to "actions" list in MainWindow

        :return: NoneType
        """
        if self.name != "":
            self.save_changes()
        else:
            # otherwise create a new loop and save it to the loops dictionary
            # Try to fetch user input data and cast it to floats
            # If it fails, throw an exception
            # Otherwise, create a loop, add it to the shared dict

            # Create a task that checks if loop stop has been request on each measure point of the loop
            task = Task(self.parent.check_stop_request)
            # grab data for creating a loop from elements of the widget
            try:
                lower = float(self.textbox_lower_limit.text())
                upper = float(self.textbox_upper_limit.text())
                num = int(self.textbox_num.text())
                delay = float(self.textbox_step.text())
                sweep_division = float(self.sweep_parameter_divider.text())
            except Exception as e:
                warning_string = "Errm, looks like something went wrong ! \nHINT: Measurement parameters not set. \n"\
                                 + str(e)
                show_error_message("Warning", warning_string)
            else:   
                # Create dividres and add them to a dict of dividers (shared with main window)
                sweep_parameter = self.sweep_parameter_cb.currentData()
                if sweep_division != 1:
                    full_name = str(sweep_parameter)
                    sweep_parameter = VoltageDivider(sweep_parameter, sweep_division)
                    self.dividers[full_name] = sweep_parameter

                # create a list and fill it with actions created by user (dividers if they are attached)
                actions = []
                for i in range(len(self.current_loop_actions_dictionary)):
                    action_array = self.current_loop_actions_dictionary["action" + str(i)]
                    if action_array is not None:
                        action_parameter = action_array[1].currentData()
                        try:
                            division = float(action_array[2].text())
                        except Exception as e:
                            show_error_message("Warning", str(e))
                        else:
                            if division != 1:
                                action_parameter = VoltageDivider(action_parameter, division)
                            actions.append(action_parameter)
                # append a task that checks for loop stop request
                actions.append(task)

                # pass dereferenced list of actions to a loops each method
                if len(self.instruments):
                    lp = Loop(sweep_parameter.sweep(lower, upper, num=num), delay = delay, progress_interval=20).each(*actions)
                else:
                    show_error_message("Warning", "U can't make a loop without instruments !")
                    return
                name = "loop" + str(len(self.parent.shown_loops)+1)
                self.loops[name] = lp
                self.actions.append(lp)
                self.parent.update_loops_preview()

                """# if a loop name has been passed to this widget then overwrite that loop in the loops dictionary
            if self.name != "":
                name = self.name
                self.loops[name] = lp
                self.actions.append(lp)
                self.parent.update_loops_preview(edit=name)
            # otherwise create a new loop and save it to the loops dictionary
            else:"""

                # self.close()

    def save_changes(self):
        name = self.name

        if name in self.loops:
            # Create a task that checks if loop stop has been request on each measure point of the loop
            task = Task(self.parent.check_stop_request)
            # grab data for creating a loop from elements of the widget
            try:
                lower = float(self.textbox_lower_limit.text())
                upper = float(self.textbox_upper_limit.text())
                num = float(self.textbox_num.text())
                delay = float(self.textbox_step.text())
                sweep_division = float(self.sweep_parameter_divider.text())
            except Exception as e:
                warning_string = "Errm, looks like something went wrong ! \nHINT: Measurement parameters not set. \n" \
                                 + str(e)
                show_error_message("Warning", warning_string)
            else:
                # Create dividres and add them to a dict of dividers (shared with main window)
                sweep_parameter = self.sweep_parameter_cb.currentData()
                if sweep_division != 1:
                    full_name = str(sweep_parameter)
                    sweep_parameter = VoltageDivider(sweep_parameter, sweep_division)
                    self.dividers[full_name] = sweep_parameter
                # create a list and fill it with actions created by user (dividers if they are attached)
                actions = []
                for i in range(len(self.current_loop_actions_dictionary)):
                    action_array = self.current_loop_actions_dictionary["action" + str(i)]
                    if action_array is not None:
                        action_parameter = action_array[1].currentData()
                        try:
                            division = float(action_array[2].text())
                        except Exception as e:
                            show_error_message("Warning", str(e))
                        else:
                            if division != 1:
                                action_parameter = VoltageDivider(action_parameter, division)
                            actions.append(action_parameter)
                # append a task that checks for loop stop request
                actions.append(task)

                self.loops[name].sweep_values = sweep_parameter.sweep(lower, upper, num=num)
                self.loops[name].delay = delay
                self.loops[name].actions = list(actions)

            self.parent.update_loops_preview(edit=name)
        else:
            show_error_message("Warning", "The loop does not exist. \nNew loop will be created")
            self.name = ""
            self.create_loop()
            self.close()

    
        
    def update_sweep_instrument_modules(self):
        """
        Replaces data in parameters combo box. Fetch all modules of an instrument selected in a instrument combo box
        and display them as options in module combo box

        :return: NoneType
        """
        # upon selecting one of the instruments from the combo box update the other combo box with the modules that
        # this particular instrument has. Meaning only modules of this instrument will now be selectable from this
        # combobox
        if len(self.instruments):
            
            
            self.sweep_module_cb.clear()
            self.sweep_parameter_cb.clear()
            instrument = self.sweep_parameter_instrument_cb.currentData()
            #instrument_name = self.sweep_parameter_instrument_cb.currentText()
            
            if len(instrument.submodules):
                if len(instrument.parameters):
                    display_member_string = instrument.name
                    data_member = instrument
                    self.sweep_module_cb.addItem(display_member_string, data_member)
                
                    for module in instrument.submodules.keys():
                        
                        if isinstance(instrument.submodules[module], InstrumentBase):
                            display_member_string = module
                            data_member = instrument.submodules[module]
                                
                            
                            self.sweep_module_cb.addItem(display_member_string, data_member)
              
                else:
                    for module in instrument.submodules.keys():
                    
                        if isinstance(instrument.submodules[module], InstrumentBase):
                            display_member_string = module
                            data_member = instrument.submodules[module]
                                
                            
                            self.sweep_module_cb.addItem(display_member_string, data_member)
               
            else:
                
                display_member_string = instrument.name
                data_member = instrument
                self.sweep_module_cb.addItem(display_member_string, data_member)
            
                
            self.update_sweep_instrument_parameters()
            
            
    def update_sweep_instrument_parameters(self):
        """
        Replaces data in parameters combo box. Fetch all parameters of an instrument selected in a instrument combo box
        and display them as options in parameters combo box
        
        Try adding the use of a validator test to keep only "sweepable" parameters
        
        
        :return: NoneType
        """
        # upon selecting one of the instruments from the combo box update the other combo box with the parameters that
        # this particular instrument has. Meaning only parameters of this instrument will now be selectable from this
        # combobox
        if len(self.instruments):
            self.sweep_parameter_cb.clear()
            
            instrument = self.sweep_parameter_instrument_cb.currentData()
            module = self.sweep_module_cb.currentData()
            
            if instrument == module:
                for parameter in instrument.parameters:
                    # i guess i dont need to show IDN parameter
                    #if isinstance(instrument.parameters[parameter].vals,qc.utils.validators.Numbers):
                    
                    if parameter != "IDN" and str(instrument.parameters[parameter]) not in self.dividers:
                        display_member_string = parameter
                        data_member = instrument.parameters[parameter]
                        self.sweep_parameter_cb.addItem(display_member_string, data_member)
                    if str(instrument.parameters[parameter]) in self.dividers:
                        name = str(instrument.parameters[parameter])
                        display_member_string = self.dividers[name].name
                        data_member = instrument.parameters[parameter]
                        self.sweep_parameter_cb.addItem(display_member_string, data_member)
        
            else:
                module_name = self.sweep_module_cb.currentText()
                
                
                for parameter in instrument.submodules[module_name].parameters:
                    # i guess i dont need to show IDN parameter
                    #if isinstance(instrument.parameters[parameter].vals,qc.utils.validators.Numbers):
                        
                    if parameter != "IDN" and str(instrument.submodules[module_name].parameters[parameter]) not in self.dividers:
                        display_member_string = parameter
                        data_member = instrument.submodules[module_name].parameters[parameter]
                        self.sweep_parameter_cb.addItem(display_member_string, data_member)
                    
                    if str(instrument.submodules[module_name].parameters[parameter]) in self.dividers:
                        name = str(instrument.submodules[module_name].parameters[parameter])
                        display_member_string = self.dividers[name].name
                        data_member = instrument.submodules[module_name].parameters[parameter]
                        self.sweep_parameter_cb.addItem(display_member_string, data_member)
                
        self.update_divider_value()
    
    def update_action_instrument_modules(self, action_name=None):
        """
        Replaces data in parameters combo box. Fetch all parameters of an instrument selected in a instrument combo box
        and display them as options in parameters combo box

        :return: NoneType
        """
        # Upon selecting one of possible instruments, update the parameter combo box to only display parameters that
        # belong to this instrument meaning only those parameters will now be selectable
        if (len(self.instruments)) and (action_name is None):
            for name, action_array in self.current_loop_actions_dictionary.items():
                # action_array looks like [instrument_cb, parameter_cb, divider_textbox], therefor,
                # action_array[1].clear removes all elements currently in the parameters_combobox (parameter_cb) and module_cb
                action_array[1].clear()
                action_array[3].clear()
                action = action_array[0].currentData()
                
                # if action is loop, then just show loop name, loop has no parameters so for module also show loop name
                if isinstance(action, ActiveLoop):
                    # action_array[0] grabs instrument (or in this case -> loop)
                    display_member_string = action_array[0].currentText()
                    data_member = action_array[0].currentData()
                    # since its a loop, it doesnt have parameters, therefor, just display loop name as module
                    
                    action_array[3].addItem(display_member_string, data_member)
                else:
                    # if it's not a loop, then its an instrument
                    if len(action.submodules):
                        if len(action.parameters):
                           display_member_string = action.name
                           data_member = action
                           action_array[3].addItem(display_member_string, data_member)
                           
                        for module in action.submodules:
                            # if the instrument has channels, add each channel in the combobox,
                            # only add modules that are defined as possible parameters holders aka InstrumentBase
                            
                            if isinstance(action.submodules[module], InstrumentBase):
                                display_member_string = module
                                data_member = action.submodules[module]
                                    
                                
                                action_array[3].addItem(display_member_string, data_member)
                        
                    else:
                        #if instrument doesn't have any channels also show for module_cb the instrument 
                        display_member_string = action_array[0].currentText()
                        data_member = action_array[0].currentData()
                        action_array[3].addItem(display_member_string, data_member)
                      
            self.update_action_instrument_parameters(action_name=None)
        
            
        
        
        # This block will get executed only if this function is called from method self.add_parameter/ WRONG, it will call as soon as the combobox has been initiated
        elif (len(self.instruments)) and (action_name is not None):
            action_array = self.current_loop_actions_dictionary[action_name]
            action_array[3].clear()
            action_array[1].clear()
            action = action_array[0].currentData()
            if not isinstance(action, ActiveLoop) and isinstance(action, Instrument):
                
                if len(action.submodules):
                    if len(action.parameters):
                           display_member_string = action.name
                           data_member = action
                           action_array[3].addItem(display_member_string, data_member)
                    
                    for module in action.submodules:
                        # if the instrument has channels, add each channel in the combobox,
                        # only add modules that are defined as possible parameters holders aka InstrumentBase
                        
                        if isinstance(action.submodules[module], InstrumentBase):
                            display_member_string = module
                            data_member = action.submodules[module]
                                
                            
                            action_array[3].addItem(display_member_string, data_member)
                        #if instrument doesn't have any channels also show for module_cb the instrument 
                        
                else:
                    display_member_string = action_array[0].currentText()
                    data_member = action_array[0].currentData()
                    action_array[3].addItem(display_member_string, data_member)
                    
                
            else:
                display_member_string = action_array[0].currentText()
                data_member = self.loops[display_member_string[1:-1]]
                action_array[3].addItem(display_member_string, data_member)

            self.update_action_instrument_parameters(action_name=action_name)
        
        
    def update_action_instrument_parameters(self, action_name=None):
        """
        Replaces data in parameters combo box. Fetch all parameters of an instrument selected in a instrument combo box
        and display them as options in parameters combo box

        :return: NoneType
        """
        # Upon selecting one of possible instruments, update the parameter combo box to only display parameters that
        # belong to this instrument meaning only those parameters will now be selectable
        if (len(self.instruments)) and (action_name is None):
            for name, action_array in self.current_loop_actions_dictionary.items():
                # action_array looks like [instrument_cb, parameter_cb, divider_textbox], therefor,
                # action_array[1].clear removes all elements currently in the parameters_combobox (parameter_cb)
                action_array[1].clear()
                action = action_array[0].currentData()
                module = action_array[3].currentData()
                # if action is loop, then just show loop name, loop has no parameters so for params also show loop name
                if isinstance(action, ActiveLoop):
                    # action_array[0] grabs instrument (or in this case -> loop)
                    display_member_string = action_array[0].currentText()
                    data_member = action_array[0].currentData()
                    # since its a loop, it doesnt have parameters, therefor, just display loop name as parameter
                    action_array[1].addItem(display_member_string, data_member)
                else:
                    # if it's not a loop, then its an instrument
                    if len(action.submodules):
                        module_name = action_array[3].currentText()
                
                        
                        for parameter in action.submodules[module_name].parameters:
                            # i guess i dont need to show IDN parameter
                            if parameter != "IDN" and str(action.submodules[module_name].parameters[parameter]) not in self.dividers:
                                display_member_string = parameter
                                data_member = action.submodules[module_name].parameters[parameter]
                                action_array[1].addItem(display_member_string, data_member)
                            if str(action.submodules[module_name].parameters[parameter]) in self.dividers:
                                name = str(action.submodules[module_name].parameters[parameter])
                                display_member_string = self.dividers[name].name
                                data_member = action.submodules[module_name].parameters[parameter]
                                action_array[1].addItem(display_member_string, data_member)
                                
                    
                    else:
                       
                    # if it is a mono channel instrument, then give back all the parameters 
                        for parameter in action.parameters:
                            # i don't need to show IDN, otherwise display parameter name, and save reference to parameter
                            # as a data member of the combo box row (also show basic data only if divider was not attached
                            # to this parameter
                            if parameter != "IDN" and str(action.parameters[parameter]) not in self.dividers:
                                display_member_string = parameter
                                data_member = action.parameters[parameter]
                                action_array[1].addItem(display_member_string, data_member)
                            # if divider has been added to this parameter then show values of the divider
                            if str(action.parameters[parameter]) in self.dividers:
                                param_name = str(action.parameters[parameter])
                                display_member_string = self.dividers[param_name].name
                                data_member = action.parameters[parameter]
                                action_array[1].addItem(display_member_string, data_member)
                        self.update_divider_value()
                    
         
            
        # This block will get executed only if this function is called from method self.add_parameter
        elif (len(self.instruments)) and (action_name is not None):
            action_array = self.current_loop_actions_dictionary[action_name]
            action_array[1].clear()
            action = action_array[0].currentData()
            module = action_array[3].currentData()
            
            if isinstance(action, ActiveLoop):
                    # action_array[0] grabs instrument (or in this case -> loop)
                    display_member_string = action_array[0].currentText()
                    data_member = action_array[0].currentData()
                    # since its a loop, it doesnt have parameters, therefor, just display loop name as parameter
                    action_array[1].addItem(display_member_string, data_member)
            else:
                # if it's not a loop, then its an instrument
                if action == module:
                # if it is a mono channel instrument, then give back all the parameters 
                    for parameter in action.parameters:
                        # i don't need to show IDN, otherwise display parameter name, and save reference to parameter
                        # as a data member of the combo box row (also show basic data only if divider was not attached
                        # to this parameter
                        if parameter != "IDN" and str(action.parameters[parameter]) not in self.dividers:
                            display_member_string = parameter
                            data_member = action.parameters[parameter]
                            action_array[1].addItem(display_member_string, data_member)
                        # if divider has been added to this parameter then show values of the divider
                        if str(action.parameters[parameter]) in self.dividers:
                            param_name = str(action.parameters[parameter])
                            display_member_string = self.dividers[param_name].name
                            data_member = action.parameters[parameter]
                            action_array[1].addItem(display_member_string, data_member)
                    self.update_divider_value()
                else:
                    module_name = action_array[3].currentText()
            
                    
                    for parameter in action.submodules[module_name].parameters:
                        # i guess i dont need to show IDN parameter
                        if parameter != "IDN" and str(action.submodules[module_name].parameters[parameter]) not in self.dividers:
                            display_member_string = parameter
                            data_member = action.submodules[module_name].parameters[parameter]
                            action_array[1].addItem(display_member_string, data_member)
                        if str(action.submodules[module_name].parameters[parameter]) in self.dividers:
                            name = str(action.submodules[module_name].parameters[parameter])
                            display_member_string = self.dividers[name].name
                            data_member = action.submodules[module_name].parameters[parameter]
                            action_array[1].addItem(display_member_string, data_member) 
                
                
                
    
    def fill_loop_data(self):
        """
        If this window is created with a loop passed to it then get all data from the loop and fill the fields in
        the window with that data. Enables editing previously created loops.

        :return: NoneType
        """

        # set textboxes to show extracted values
        self.textbox_lower_limit.setText(str(self.loop_values[0]))
        self.textbox_upper_limit.setText(str(self.loop_values[1]))
        self.textbox_num.setText(str(self.loop_values[2]))
        self.textbox_step.setText(str(self.loop_values[3]))

        # add all actions that are not the first one or a Task, since the first one is added by default, and we don't
        # want to display a Task in list of actions
        for index, action in enumerate(self.loop.actions):
            if index != 0 and (not isinstance(action, Task)):
                self.add_parameter()

        # if action is a loop, display it as a loop
        # else display selected instrument and parameter
        actions = self.loop.actions
        for index, action in enumerate(actions):
            # action can be a loop, then just show loop name
            if str(action) in self.dividers:
                action = self.dividers[str(action)]

            if isinstance(action, ActiveLoop):
                action_parameter_instrument_name = action
                action_name = "action"+str(index)
                action_array = self.current_loop_actions_dictionary[action_name]
                instrument_index = action_array[0].findData(
                    action_parameter_instrument_name
                )
                action_array[0].setCurrentIndex(instrument_index)
            # if action is a voltage divider then get the parameter that this divider is attached to and also show
            # correct division that has been applied to this divider
            elif isinstance(action, VoltageDivider):
                action_parameter_instrument_name = action.v1._instrument.name
                action_name = "action" + str(index)
                action_array = self.current_loop_actions_dictionary[action_name]
                instrument_index = action_array[0].findText(
                    action_parameter_instrument_name
                )
                action_array[0].setCurrentIndex(instrument_index)
                action_parameter_full_name = str(action.v1)
                try:
                    if action_parameter_full_name in self.dividers:
                        action_parameter_name = self.dividers[action_parameter_full_name].name
                    else:
                        raise Exception(action_parameter_full_name)
                except Exception as e:
                    show_error_message("Warning", str(e) +
                                       "\nMost likely you deleted the divider that was used by this loop")
                else:
                    parameter_index = action_array[1].findText(action_parameter_name)
                    action_array[1].setCurrentIndex(parameter_index)
                    action_array[2].setText(str(action.division_value))
            # if its a regular parameter then find if there was a division applied to it and display that insted of 1
            else:
                if not isinstance(action, Task) and action is not None:
                    action_parameter_instrument_name = action._instrument.name
                    action_name = "action" + str(index)
                    action_array = self.current_loop_actions_dictionary[action_name]
                    instrument_index = action_array[0].findText(action_parameter_instrument_name)
                    action_array[0].setCurrentIndex(instrument_index)
                    action_parameter_name = action.name
                    parameter_index = action_array[1].findText(action_parameter_name)
                    action_array[1].setCurrentIndex(parameter_index)

        # do the same thing for sweep parameter
        sweep = self.loop.sweep_values.parameter
        if str(sweep) in self.dividers:
            sweep = self.dividers[str(sweep)]
        if isinstance(sweep, VoltageDivider):
            sweep_parameter_instrument_name = sweep._instrument.name
            index = self.sweep_parameter_instrument_cb.findText(sweep_parameter_instrument_name)
            self.sweep_parameter_instrument_cb.setCurrentIndex(index)
            sweep_parameter_full_name = str(sweep.v1)
            try:
                if sweep_parameter_full_name in self.dividers:
                    sweep_parameter_name = self.dividers[sweep_parameter_full_name].name
                else:
                    raise Exception(sweep_parameter_full_name)
            except Exception as e:
                show_error_message("Warning", str(e) +
                                   "\nMost likely you deleted the divider that was used by this loop")
            else:
                index = self.sweep_parameter_cb.findText(sweep_parameter_name)
                self.sweep_parameter_cb.setCurrentIndex(index)
                self.sweep_parameter_divider.setText(str(sweep.division_value))
        else:
            sweep_parameter_instrument_name = self.loop.sweep_values.parameter._instrument.name
            index = self.sweep_parameter_instrument_cb.findText(sweep_parameter_instrument_name)
            self.sweep_parameter_instrument_cb.setCurrentIndex(index)
            sweep_parameter_name = self.loop.sweep_values.parameter.name
            index = self.sweep_parameter_cb.findText(sweep_parameter_name)
            self.sweep_parameter_cb.setCurrentIndex(index)

    def update_step_size(self):
        """
        Updates the step size if number of steps in changed

        :return: NoneType
        """
        try:
            steps = float(self.textbox_num.text())
            lower = float(self.textbox_lower_limit.text())
            upper = float(self.textbox_upper_limit.text())
        except Exception as e:
            show_error_message("Warning", str(e))
        else:
            if steps != 0:
                if steps > 1:
                    step_size = (upper - lower) / (steps - 1)
                    self.textbox_step_size.setText(str(round(step_size, 3)))
                else:
                    step_size = (upper - lower)
                    self.textbox_step_size.setText(str(round(step_size, 3)))
            else:
                show_error_message("HELLO !", "U cannot have zero steps, come on man, u went to school for 20 years")

    def update_num_of_steps(self):
        """
        Updates number of steps if value of step size is changed

        :return: NoneType
        """
        try:
            step_size = float(self.textbox_step_size.text())
            lower = float(self.textbox_lower_limit.text())
            upper = float(self.textbox_upper_limit.text())
        except Exception as e:
            show_error_message("Warning", str(e))
        else:
            if step_size != 0:
                steps = abs(int(((upper - lower) / step_size) + 1))
                self.textbox_num.setText(str(steps))
            else:
                show_error_message("Warning", "Haha, let's see what other funny things i can find ... ")

    def update_divider_value(self):
        """
        After selecting a parameter, if that parameter is a voltage divider then show current division applied to that
        divider.

        If SetupLoopsWidget is opened to edit existing loop, show division that were set when the loop was created,
        otherwise, show 1 as division value.

        :return: NoneType
        """
        # get currently selected parameter
        sweep_parameter = self.sweep_parameter_cb.currentData()
        # if that param has an attribute full_name that means that the param is a VoltageDivider
        if hasattr(sweep_parameter, "full_name"):
            sweep_parameter_name = sweep_parameter.full_name
        else:
            # just to make sure that its not found in dividers dictionary
            sweep_parameter_name = ""
        sweep_display_name = self.sweep_parameter_cb.currentText()

        # if it's a VoltageDivider set the text on it's division text box to the value of it's division
        if (sweep_parameter_name in self.dividers) and (sweep_display_name == self.dividers[sweep_parameter_name].name):
            sweep_division = self.dividers[sweep_parameter_name].division_value
            self.sweep_parameter_divider.setText(str(sweep_division))
        # I think i don't need this anymore since the change in what is displayed and what not
        elif (self.name != "") and (str(self.loop_values[4]) == sweep_parameter_name):
            sweep_division = self.loop_values[5]
            self.sweep_parameter_divider.setText(str(sweep_division))
        # if divider is not attached set division to be 1
        else:
            sweep_division = 1
            self.sweep_parameter_divider.setText(str(sweep_division))

        # iterate through all actions of this loop and update the values for them (just like the above block of code)
        for name, action_array in self.current_loop_actions_dictionary.items():
            # deleting items set that item in dict to None, this is way we have to check that its not None
            if action_array is not None:
                action_parameter = action_array[1].currentData()
                if hasattr(action_parameter, "full_name"):
                    action_parameter_name = action_parameter.full_name
                else:
                    action_parameter_name = ""
                action_display_name = action_array[1].currentText()

                if (action_parameter_name in self.dividers) and (action_display_name == self.dividers[action_parameter_name].name):
                    action_division = self.dividers[action_parameter_name].division_value
                    action_array[2].setText(str(action_division))
                elif (self.name != "") and (str(self.loop_values[6]) == action_parameter_name):
                    action_division = self.loop_values[7]
                    action_array[2].setText(str(action_division))
                else:
                    action_division = 1
                    action_array[2].setText(str(action_division))

    def get_loop_data(self):
        """
        Gets all data required to set up the same loop. That includes lower and upper values of sweep, number of steps
        and delay. Additionaly grabs the first action of the loop (only one that has to exists)

        :return:
        """

        # fetch all data required to completely fill in this widgets
        lower = self.loop.sweep_values[0]
        upper = self.loop.sweep_values[-1]
        number_of_steps = len(self.loop.sweep_values)
        loop_delay = self.loop.delay

        # save the fetched data for easier extraction
        self.loop_values.append(lower)
        self.loop_values.append(upper)
        self.loop_values.append(number_of_steps)
        self.loop_values.append(loop_delay)

        sweep = self.loop.sweep_values.parameter
        if str(sweep) in self.dividers:
            name = str(sweep)
            sweep = self.dividers[name]
        action = self.loop.actions[0]
        if str(action) in self.dividers:
            name = str(action)
            action = self.dividers[name]

        # add sweep param to the loop data
        self.loop_values.append(sweep)
        # if sweep param has divider attached to it, overwrite sweep param in loop data with the VoltageDivider
        if isinstance(sweep, VoltageDivider):
            self.loop_values[-1] = sweep.v1.full_name
            self.loop_values.append(sweep.division_value)
        else:
            self.loop_values.append(1)

        # add action param to loop data dictionary (only the first action)
        self.loop_values.append(action)
        # if the first action has voltage divider attached to it, overwrite the data with the VoltageDivider
        if isinstance(action, VoltageDivider):
            self.loop_values[-1] = action.v1.full_name
            self.loop_values.append(action.division_value)
        else:
            self.loop_values.append(1)

    def switch_upper_and_lower(self):
        lower = self.textbox_upper_limit.text()
        upper = self.textbox_lower_limit.text()

        self.textbox_lower_limit.setText(lower)
        self.textbox_upper_limit.setText(upper)

    def disable_changes(self):
        self.add_loop_btn.setDisabled(True)
        self.add_loop_btn.setText("Disabled: Loop running")

    def enable_changes(self):
        self.add_loop_btn.setDisabled(False)
        self.add_loop_btn.setText("Save Changes")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = LoopsWidget([])
    sys.exit(app.exec_())
