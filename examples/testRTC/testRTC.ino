// SQW/OUT signal functions using a DS1307 RTC connected via I2C and Wire lib.
// 2012-11-14 idreammicro.com http://opensource.org/licenses/mit-license.php

#include <Wire.h>
#include <RTClib.h>

RTC_DS1307 RTC;
Ds1307SqwPinMode modes[] = {SquareWave1HZ, SquareWave4kHz, SquareWave8kHz, SquareWave32kHz};
Ds1307SqwPinMode RTC_freq;

int freq = 8192;

void setup () {
    Serial.begin(57600);
    Wire.begin();
    switch(freq){
        case 1:
            RTC_freq = modes[0];
            break;
        case 4096:
            RTC_freq = modes[1];
            break;
        case 8192:
            RTC_freq = modes[2];
            break;
        case 32768:
            RTC_freq = modes[3];
            break;
        default:
            freq = 4096;
            RTC_freq = modes[1];
    }
    RTC.begin();
    // Synchronise clock to make sure it's running
    RTC.adjust(DateTime(__DATE__, __TIME__));
    // Set SQW/Out signal frequency to 8192 Hz.
    RTC.writeSqwPinMode(RTC_freq);
}

void loop () {
    // Nothing to do.
}
