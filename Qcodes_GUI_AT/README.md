# qcodesGUI
GUI for setting up experiments with qcodes


Running GUI:

This short tutorial assumes that you have Anaconda3 installed as well as working qcodes environment

- Open Anaconda prompt
- Change directory to a directory where you cloned this repo
- write command: activate qcodes
- write command: python qcodesMainWindow.py

Everton WL:

1- sweep using bilt 100V - we could not select the channel of the bilt that goes to 110V

2- driver for lakeshore such that we can use the wait for temperature - that is implemented only in one strange lakeshore

3- I don't know how to implement, but it would be great to have an autosensitivite for the lock-in sr830