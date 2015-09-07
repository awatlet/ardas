## Dual EIA-232 driver receiver

Each receiver converts TIA/EIA-232-F inputs (RS232) to 5-V TTL/CMOS levels (Arduino Tx, Rx)  

0V to 5.5V Vcc operation  

###  Pin configurations

![](https://github.com/UMONS-GFA/ardas/blob/master/doc/MAX232N/max232_pin_configurations.jpg)

IN: Enter in the MAX232  
OUT: Out of the MAX232  

R: data received by the Arduino  
T: data received by the Arduino  

Pin 1 - **C1+**  
Pin 2 - **Vs+**  
Pin 3 - **C1-**  
Pin 4 - **C2+**  
Pin 5 - **C2-**  
Pin 6 - **Vs-**  
Pin 7 - **T2 OUT**  
Pin 8 - **R2 IN**  
Pin 9 - **R2 OUT**  
Pin 10 - **T2 IN**  
Pin 11 - **T1 IN** : data from Arduino, Tx, pin 1 (TTL)  
Pin 12 - **R1 OUT** : data to Arduino Rx, pin 0 (TTL)  
Pin 13 - **R1 IN** : data from  the PC, RxD, pin 3 on female RS232 connector (TIA/EIA-232-F)  
Pin 14 - **T1 OUT** : data to PC, TxD,  pin 2 on female RS232 connector (TIA/EIA-232-F)  
Pin 15 - **GND**  
Pin 16 - **Vcc**  

### How to use it with an Arduino

![](https://github.com/UMONS-GFA/ardas/blob/master/doc/MAX232N/MAX232_with_arduino.jpg)

Use 4 capacitors of 1uF and 1 capacitor of 0.1 uF


