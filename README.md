# arDAS
The arDAS project is an attempt to emulate a **nanoDAS** with an Arduino.

Features :
* Based on [Arduino] (http://arduino.cc/)
* Simulates a nanoDAS

 
### Ardas pin configurations

#### RTC
Pin 5 of RTC(SDA) to pin 18(A4) of Arduino for I2C  
Pin 6 of RTC(SCL) to pin 19(A5) of Arduino for I2C  
Pin 7 of RTC to pin 2 of Arduino for interrupt 0  

#### Shift register 74HC595 serial to parallel
Pin 12 of shift register to pin 15 of Arduino (STCP)    
Pin 11 of shift register to pin 16 of Arduino (SHCP)    
Pin 14 of shift register to pin 14 of Arduino (DS)    

#### Counter
Pin 7 of counter to pin 5 of Arduino (RCLK) to save to registers  

#### Shift register 74HC165 parallel to serial
Pin 1 of shift register to pin 8 of Arduino (PL)     // latch pin  
Pin 2 of shift register to pin 6 of Arduino (CP)    // clock for synchronous communcation  
Pin 9 of shift register to pin 7 of Arduino (Q7)    // serial output  
Pin 15 of shift register to pin 9 of Arduino (CE)  // activation cp clock  

#### MAX232
Pin 11 of MAX232 to pin 1 of Arduino (Tx)  
Pin 12 of MAX232 to pin 0 of Arduino (Rx)  
Pin 9 of Max232 to pin 3 of Arduino (RTS)

## Sync the fork

List the current configured remote repository for your fork.  
```
$ git remote -v
```

Specify a new remote upstream repository that will be synced with the fork.  
```
$ git remote add upstream https://github.com/UMONS-GFA/ardas.git
```

Fetch the branches and their respective commits from the upstream repository. Commits to master will be stored in a local branch, upstream/master.  
```
$ git fetch upstream
```

Merge the changes from upstream/master into your local master branch. This brings your fork's master branch into sync with the upstream repository, without losing your local changes.  
```
$ git merge upstream/master
```
 

