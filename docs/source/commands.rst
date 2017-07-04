Low level commands
==================

Raspardas uses a set of commands to communicate with the ardas.
It is possible to forward such commands through raspardas using a telnet connection using port 10001 or a direct
serial connection to the ardas is also possible but not recommended. Indeed, some of those commands are intercepted by
raspardas and processed before being forwarded to the ardas while other are only known to raspardas and have no effect
when sent directly to an ardas.

Note : Every data sequence send by an ardas is followed by \n\r (LFCR)
However each command end line sent to ardas must be \r (CR)

* -nnn : Call Das with netID nnn
* -999 : Call all Das

* #HE : Help
* #CF :
* #DG : Toggle ardas debug mode
* #E0 : No Echo
* #E1 : Only Data
* #E2 : Data + Time
* #ND : Set naïve data mode
* #RD : Set raspardas data mode
* #RC : Toggle between raw data and calibrated data
* #SD yyyy mm dd hh nn ss : Set Date
* #SR iiii : Set Integration Period
* #SI nnn : Set Das netID
* #SS ssss : Set Station Number
* #RI : Read Info
* #RV : Read version
* #ZR station netId integrationPeriod nbInst sensor1 ... code (Ex: #ZR 1111 222 3333 4 0001 0002 0003 0004 31): Reconfig
* #KL : Stop (Kill) raspardas and closes files

Some commands are no longer supported and will be removed in a future version:

* #ZF : erase memory and set default configuration
* #XB : Full Download
* #XP : yyyy mm dd hh ss yyyy mm dd hh nn ss : Partial Download
* #XS : Stop download