#include <Wire.h>
#include <RTClib.h>

#define CLOCK_FREQ 4096

int freq = CLOCK_FREQ;

RTC_DS1307 RTC;

// Pins
/* RTC */
// Don't forget to connect I2C pins A4 and A5 (5 and 6 of RTC)
const byte rtc_pulse_pin = 2;

Ds1307SqwPinMode modes[] = {SquareWave1HZ, SquareWave4kHz, SquareWave8kHz, SquareWave32kHz};
Ds1307SqwPinMode RTC_freq;

void SerialPrintf(char *format,...)
{
    char buff[128];
    va_list args;
    va_start (args,format);
    vsnprintf(buff,sizeof(buff),format,args);
    va_end (args);
    buff[sizeof(buff)/sizeof(buff[0])-1]='\0';
    Serial.print(buff);
}

void setup()
{
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
    if (!RTC.isrunning()){
        Serial.println("RTC is not running");
        // following line sets the RTC to the date & time this sketch was compiled
        RTC.adjust(DateTime(F(__DATE__), F(__TIME__)));
    }


    RTC.writeSqwPinMode(RTC_freq);
}

void loop(){
    DateTime nowt = RTC.now();
    DateTime tic = nowt.unixtime() - uint32_t(2.0/2.0);
    //DateTime tic = RTC.now();
    Serial.println(tic.unixtime());
    SerialPrintf("*%4d %02d %02d %02d %02d %02d ",nowt.year(),nowt.month(),nowt.day(),tic.hour(),nowt.minute(),nowt.second());
    SerialPrintf("*%4d %02d %02d %02d %02d %02d ",tic.year(),tic.month(),tic.day(),tic.hour(),tic.minute(),tic.second());
    Serial.println("");
    delay(1000);
}