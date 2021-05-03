# Qcodes_GUI_Aurel

 Qcodes GUI adaptation of https://github.com/kNalj/qcodesGUI

Start installing Qcodes: https://qcodes.github.io/Qcodes/index.html

Install all contribution modules (can be handy but specially the drivers) => pip install qcodes_contrib_drivers (make sure to copy paste the drivers in the Instrument_drivers file of qcodes library or modify the code to retrieve them elsewhere trough their path in l.308 of qcodesMainwindow.py). Not mandatory anymore but always helpfull. 

Install Keysight SD1 : https://www.keysight.com/us/en/lib/software-detail/instrument-firmware-software/sd1-3x-software-3120392.html

Might need to install pyqtgraph : pip install pyqtgraph

Create a py file InstrumentData with a a dictionary instrument_data in the same folder than the other modules. This file is made to pre register connection information for an instrument. For instance {'Keythley 20000':'GPIB::0::INSTR'}. Although you can keep an empty dictionnary, especially if you wanna use multiple devices of the same kind. 

Launch qCodesMainWindow.py
