from PyQt5.QtWidgets import QMessageBox, QTreeWidget, QTreeWidgetItem
from PyQt5 import QtGui

import os
import importlib
from qcodes.loops import ActiveLoop
from qcodes.actions import Task
from qcodes.plots.pyqtgraph import QtPlot
from qcodes import Instrument,Parameter,ChannelList
from qcodes.instrument.base import InstrumentBase



class plot_dictionnary():
    
    def __init__(self):
        self._dict_plot = {}
    
    @property
    def dict_plot(self):
        return self._dict_plot
    
    def update_plot(self):
        
        for i in self._dict_plot.values():
            i.update()
        
    def update(self):
        return self.update_plot()
    
    def save(self):
        return self.save_plot()
    
    def save_plot(self):
        for i in self._dict_plot.values():
            i.save()

            
def show_error_message(title, message):
    """
    Function for displaying warnings/errors

    :param title: Title of the displayed watning window
    :param message: Message shown by the displayed watning window
    :return: NoneType
    """
    msg_box = QMessageBox()
    msg_box.setIcon(QMessageBox.Warning)
    msg_box.setWindowIcon(QtGui.QIcon("img/warning_icon.png"))
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    msg_box.setStandardButtons(QMessageBox.Ok)
    msg_box.exec_()

def create_plot_windows(Parameters):
            plot_windows_dict = plot_dictionnary()
            for i in Parameters: 
                plot_windows_dict.dict_plot[i] = QtPlot(window_title = f'{i}')
            return plot_windows_dict  


def get_subfolders(path, instrument_brands_only=False):
    """
    Helper function to find all folders within folder specified by "path"

    :param path: path to folder to scrap subfolders from
    :param instrument_brands_only: if set to True, applies set of rules to filter isntrument brands
            when not set, this function can be used to get all subfolders in a specified folder
    :return: list[] of subfolders from specified path
    """
    if instrument_brands_only:
        return [f.name for f in os.scandir(path) if f.is_dir() and f.name[0] != "_"]
    return [f.name for f in os.scandir(path) if f.is_dir() and f.name[0]]


def get_files_in_folder(path, instrument_drivers_only=False):
    """
    Helper function to find all files within folder specified by path

    :param path: path to folder to scrap files from
    :param instrument_drivers_only: if True, apply set of rules that filter only instrument driver files
    :return: list[] of files from specified path
    """
    if instrument_drivers_only:
        return [f.name for f in os.scandir(path) if f.is_file() and f.name[0].upper() == f.name[0] and f.name[0] != "_"]
    return [f.name for f in os.scandir(path) if f.is_file()]

def get_plot_parameter(loop):
    """
    Recursive function that gets to the innermost action parameter of the loop passed to it, and returns its name
    Used for getting the parameter that is passed to the qcodes QtPlot function

    :param loop: instance of a loop class
    :return: full name of loops action parameter
    """
    action = loop.actions[0]

    if isinstance(action, ActiveLoop):
        return get_plot_parameter(action)
    else:
        return action

def get_plot_parameter_aurel(loop):
    """
    Recursive function that gets to the innermost action parameter of the loop passed to it, and returns its name
    Used for getting the parameter that is passed to the qcodes QtPlot function

    :param loop: instance of a loop class
    :return: full name of loops action parameter
    """
    parameters_list = []
    if isinstance(loop.actions[0], ActiveLoop): 
        return get_plot_parameter_aurel(loop.actions[0])
    
    else: 
        for i in range(len(loop.actions)):
        
            action = loop.actions[i]

        
            if isinstance(action, Task):
                parameters_list = parameters_list
            else:
                parameters_list.append(str(action))
        return parameters_list
        

def is_numeric(value):
    """
    Function that quickly checks if some variable can be casted to float

    :param value: check if this can be casted to float
    :return:
    """
    try:
        float(value)
        return True
    except:
        return False

def is_bool(value):
    """
    Function that quickly checks if some variable can be casted to float

    :param value: check if this can be casted to float
    :return:
    """
    if value == 'True' or 'False':
        return True
    else:
        return False

class ViewTree(QTreeWidget):
    """
    Widget that displays content of a dictionary (including sub dicts, lists, etc.)
    """
    def __init__(self, value):
        super().__init__()
        self.setWindowTitle("Loop details")
        self.setWindowIcon(QtGui.QIcon("img/osciloscope_icon.png"))

        def fill_item(item, value):
            def new_item(parent, text, val=None):
                child = QTreeWidgetItem([text])
                fill_item(child, val)
                parent.addChild(child)
                child.setExpanded(True)
            if value is None:
                return
            elif isinstance(value, dict):
                for key, val in sorted(value.items()):
                    new_item(item, str(key), val)
            elif isinstance(value, (list, tuple)):
                for val in value:
                    text = (str(val) if not isinstance(val, (dict, list, tuple))
                            else '[%s]' % type(val).__name__)
                    new_item(item, text, val)
            else:
                new_item(item, str(value))

        fill_item(self.invisibleRootItem(), value)


def retrieve_function_list(Instrument):
    SetVisabase = {'_all_instruments', 'name', 'snapshot', 'metadata', '__ge__', 'ask', 'find_instrument', '__lt__',
                   '__reduce__', 'set', 'write', 'parent', 'instances', 'full_name', 'functions', '__le__', '_type',
                   'get', 'shared_kwargs', 'submodules', '_name', '__doc__', 'get_idn', '__setattr__', '_terminator',
                   'short_name', '__weakref__', '__subclasshook__', '_address', '_t0', 'device_clear', 'name_parts',
                   '__getattribute__', 'IDN', '_set_visa_timeout', 'add_parameter', 'write_raw', 'record_instance',
                   'print_readable_snapshot', 'close_all', '__getitem__', 'log', 'visa_log', '_get_visa_timeout',
                   'delegate_attr_objects', 'remove_instance', '__getattr__', 'check_error', '__module__',
                   '__getstate__', 'add_function', 'visalib', 'close', 'call', 'timeout', 'root_instrument',
                   'ancestors', '__hash__', '__reduce_ex__', 'delegate_attr_dicts', '__str__', 'add_submodule',
                   '__format__', 'ask_raw', '__gt__', '__slots__', 'visa_handle', '_short_name', 'validate_status',
                   '__eq__', '__annotations__', '__del__', '__repr__', '__abstractmethods__', 'set_terminator',
                   '__sizeof__', 'visabackend', '__new__', '__ne__', '__delattr__', 'omit_delegate_attrs',
                   '__init_subclass__', 'connect_message', 'snapshot_base', 'parameters', '_instances',
                   '__init__', 'exist', 'load_metadata', '_meta_attrs', '__class__', 'is_valid', '__dict__',
                   'set_address', '_abc_impl', '__dir__'}
    
    setall = set(dir(Instrument))
    setp = set(Instrument.parameters)
    setm = set(Instrument.submodules)
    
    set_red = setall -SetVisabase - setp - setm
    set_callables = set([])
    for i in set_red:
        string_call = str(i)
        set_callables.add(string_call)
    
    
    return set_callables


def create_params_to_show(Instrument_instance):
    
        #This function is used on any Instrument_instance of an instrument to create a dict with all the parameters attached
        #to the right Instrument_instance ((Main instrument or submodule)
        
        if isinstance(Instrument_instance, InstrumentBase):
            params_to_show = {}  
            
            
            params_to_show = Instrument_instance.parameters
            return params_to_show
                        
            
            """
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
              """
        else:
            print('Error:Unvalid instrument')
    
def copy_dict_without_IDN(param):
    parameters = dict(param)
    del parameters['IDN']
    return parameters    