# arDAS
The arDAS project is an attempt to emulate a **nanoDAS** with an Arduino.

Features :
* Based on [Arduino] (http://arduino.cc/)
* Simulates a nanoDAS
* 

 
### Ardas pin configurations



#### RTC
Pin 5 of RTC(SDA) to pin 4 of Arduino for I2C  
Pin 6 of RTC(SCL) to pin 5 of Arduino for I2C  
Pin 7 of RTC to pin 2 of Arduino for interrupt 0  

#### Counter
Pin 3 of counter to pin 14 of Arduino (GAL)  
Pin 4 of counter to pin 15 of Arduino (GAU)  
Pin 5 of counter to pin 16 of Arduino (GBL)  
Pin 6 of counter to pin 17 of Arduino (GBU)  
Pin 7 of counter to pin 13 of Arduino (RCLK) to save to registers  

#### Shift register
Pin 1 of shift register to pin 4 of Arduino (PL)     // latch pin  
Pin 2 of shift register to pin 3 of Arduino (CP)    // clock for synchronous communcation  
Pin 9 of shift register to pin 12 of Arduino (Q7)    // serial output  
Pin 15 of shift register to pin 11 of Arduino (CE)  // activation cp clock  


