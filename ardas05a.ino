#include <Wire.h>
#include <RTClib.h>

#define PULSE_WIDTH_USEC 5
#define READ_COUNTER_REGISTER_FREQ 2 // should be 1 if freq is 1 Hz
#define CLOCK_FREQ 8192

const int COUNTS_BETWEEN_READINGS = CLOCK_FREQ / READ_COUNTER_REGISTER_FREQ; 
const int NUMBER_OF_COUNTERS = 2; // 32 bits counters
const int DATA_WIDTH = NUMBER_OF_COUNTERS * 8; // number of bits returned by daisy-chained SN74HC165N for a call to readbyte 
const int NUMBER_OF_CHANNELS_PER_COUNTER = 2; // 1 : 32 bits channels - 2: 16 bits channels 
const int NUMBER_OF_CHANNELS = NUMBER_OF_COUNTERS * NUMBER_OF_CHANNELS_PER_COUNTER;
const int BYTES_PER_CHANNEL = 4 / NUMBER_OF_CHANNELS_PER_COUNTER;

boolean DEBUG = false; // true;
int freq = CLOCK_FREQ;

RTC_DS1307 RTC;

// Pins 
/* RTC */
// Don't forget to connect I2C pins A4 and A5 (5 and 6 of RTC)
const byte rtc_pulse_pin = 2;  
const byte rclk_pin = 13;      // set selected byte to output
/* 74HC165N */
const byte pl_pin = 8;         // latch pin
const byte cp_pin = 12;        // clock for synchronous communcation
const byte q7_pin = 11;        // serial output
const byte ce_pin = 9;         // activation cp clock
/* 74HC595N */
const byte stcp_pin = 3;       // pin connected to ST_CP of 74HC595
const byte shcp_pin = 4;       // pin connected to SH_CP of 74HC595
const byte ds_pin = 5;         // pin connected to DS of 74HC595

//others
volatile unsigned int pulse_counter = 0;
volatile boolean read_counter_register = 0;
float channel[NUMBER_OF_CHANNELS];
unsigned long c1=0;
unsigned long counter_overflow;
unsigned long previous_count[NUMBER_OF_CHANNELS];
unsigned long current_count[NUMBER_OF_CHANNELS];
byte b[NUMBER_OF_COUNTERS]; // incoming bytes
byte cn = 0;
int n = 0;
unsigned int sampling_rate = 2; // integration time in seconds 
Ds1307SqwPinMode modes[] = {SquareWave1HZ, SquareWave4kHz, SquareWave8kHz, SquareWave32kHz};
Ds1307SqwPinMode RTC_freq;

void rtc_interrupt()
{
  // after each integration period
  if (pulse_counter % COUNTS_BETWEEN_READINGS == 0){  
     digitalWrite(rclk_pin, HIGH);
     digitalWrite(rclk_pin, LOW);
     
     read_counter_register = 1;
       
     }
  pulse_counter ++;
          
}

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

void read_shift_regs()
{
    unsigned long bitVal;  // check type

    digitalWrite(ce_pin, HIGH);
    digitalWrite(pl_pin, LOW);
    delayMicroseconds(PULSE_WIDTH_USEC);
    digitalWrite(pl_pin, HIGH);
    digitalWrite(ce_pin, LOW);
    for(int j = 0; j < NUMBER_OF_COUNTERS; j++){
      b[j] = 0;
      for(int i = 0; i < 8; i++)
      {
        bitVal = digitalRead(q7_pin);
        b[j] |= (bitVal << (7 - i));
        digitalWrite(cp_pin, HIGH);
        delayMicroseconds(PULSE_WIDTH_USEC);
        digitalWrite(cp_pin, LOW);
      }
    }
}

void read_bytes(byte byte_number) {
    byte val;

    switch(byte_number){
      case 0: 
        val = 119;
        break;
      case 1: 
        val = 187;
        break;
      case 2: 
        val = 221;
        break;
      case 3: 
        val = 238;
        break;   
    }
    digitalSerialWrite(val);
    if (DEBUG){
      Serial.println("");
      Serial.print("Counter(s) byte selection input :");
      Serial.println(val);
    }
    delayMicroseconds(PULSE_WIDTH_USEC);
    read_shift_regs();
    delayMicroseconds(PULSE_WIDTH_USEC);
}

void digitalSerialWrite(byte Val) 
{
    digitalWrite(stcp_pin, LOW);
    shiftOut(ds_pin, shcp_pin, MSBFIRST, Val);   
    digitalWrite(stcp_pin, HIGH);
}


void setup()
{
  Serial.begin(57600);
  Wire.begin();
  if (DEBUG)
    Serial.print("Setup");
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
       if (DEBUG)
         Serial.print("Warning : invalid frequency. Reset to default !");
  } 
  RTC.begin();
  RTC.adjust(DateTime(__DATE__, __TIME__));
  //RTC.setSqwOutSignal(RTC_freq);
  RTC.writeSqwPinMode(RTC_freq); 
  
  for (int i=0; i<NUMBER_OF_CHANNELS; i++){
    channel[i] = 0;
    previous_count[i] = 0;
    current_count[i] = 0;
  }
 
  switch(NUMBER_OF_CHANNELS_PER_COUNTER){ // fix this switch : it always uses default check type of NUMBER_OF_CHANNELS_PER_COUNTER
    case 1:
      counter_overflow = 2147483648;
    case 2:
      counter_overflow = 65536;
    default :
      counter_overflow = 65536;
      if (DEBUG)
        Serial.print("Error : invalid number of channels! ");
        Serial.println(NUMBER_OF_CHANNELS_PER_COUNTER);
  }
 if (DEBUG)
  Serial.print(".");  

  pinMode(rclk_pin, OUTPUT);
  pinMode(pl_pin, OUTPUT);
  pinMode(ce_pin, OUTPUT);
  pinMode(cp_pin, OUTPUT);
  pinMode(q7_pin, INPUT);
  pinMode(stcp_pin, OUTPUT);
  pinMode(shcp_pin, OUTPUT);
  pinMode(ds_pin, OUTPUT);
  
  int init = 0;
  for (int i=0; i<NUMBER_OF_COUNTERS; i++){
    init = init << 4;
    init+=7;
  }
  digitalSerialWrite(init);
  digitalWrite(rclk_pin, LOW);
  if (DEBUG)
    Serial.print(".");  
  
  digitalWrite(cp_pin, LOW);
  digitalWrite(pl_pin, HIGH);
  read_shift_regs();
  if (DEBUG)
    Serial.print(".");  
  
  digitalWrite(stcp_pin, LOW);
  shiftOut(ds_pin, shcp_pin, MSBFIRST, 0);
  digitalWrite(stcp_pin, HIGH);

  attachInterrupt(0, rtc_interrupt, RISING);
  if (DEBUG)
    Serial.println("complete.");  
}

void loop(){
  if(read_counter_register){
    // TODO : read time on RTC and substract half of the integration period
    n += 1;
    if (n % (READ_COUNTER_REGISTER_FREQ*sampling_rate) == 0) {
          DateTime now = RTC.now();
          DateTime tic = now.unixtime() - sampling_rate/2.0;
          SerialPrintf("*%4d %02d %02d %02d %02d %02d ",tic.year(),tic.month(),tic.day(),tic.hour(),tic.minute(),tic.second());
    }
    if(DEBUG){
      Serial.println("BEGINS...");
    }  
    for(cn=0; cn < NUMBER_OF_CHANNELS; cn++){
      if(DEBUG){
        Serial.print("Channel ");
        Serial.println(cn);
      }  
      previous_count[cn]  =  current_count[cn];
      current_count[cn] = 0;
      if(DEBUG){
        Serial.print("Previous count: ");
        Serial.println(previous_count[cn]);
      }
    }
    // read bytes corresponding to each of the 4 bytes for each counter ([byte 0 of Counter 0, byte 0 of counter 1] than [byte 1 of Counter 0, byte 1 of counter 1] ...)
    for(int i=3;i>=0;i--){
      read_bytes(i);
      if(DEBUG){
        Serial.println("");
        Serial.print("byte ");
        Serial.print(i);
        Serial.print(" : ");
        for (int j=0;j<NUMBER_OF_COUNTERS;j++){
          Serial.print(b[j]);
          Serial.print(" | ");
        }
      }
      int k = i / BYTES_PER_CHANNEL; // which channel relative to each counter
      int l = i % BYTES_PER_CHANNEL; // which byte of the channel
      for (int j=0; j<NUMBER_OF_COUNTERS; j++){
        cn=NUMBER_OF_CHANNELS_PER_COUNTER*j+k;
        current_count[cn] += (unsigned long)b[j] << (8 * l);
        if(DEBUG){
          Serial.println("");
          Serial.print("byte :");
          Serial.print(i);
          Serial.print(" | channel :");
          Serial.print(cn);
          Serial.print(" | channel relative to counter :");
          Serial.print(k);
          Serial.print(" | channel byte :");
          Serial.print(l);
          Serial.print(" : ");
          Serial.print(b[j]);
          Serial.print(" | value :");
          Serial.print((unsigned long)b[j] << (8 * l));
        }
      }
    }
    for (cn=0;cn<NUMBER_OF_CHANNELS;cn++){
      if(DEBUG)
        Serial.println(" . ");
      if(current_count[cn] >= previous_count[cn]){
        c1 = current_count[cn] - previous_count[cn];
      }
      else{
        if (DEBUG)
          Serial.print("$");
        c1 = (counter_overflow - previous_count[cn]) + current_count[cn];
      }
      if(DEBUG){
        Serial.print("Current count: ");
        Serial.println(current_count[cn]);
        Serial.print(" : ");
        Serial.print("c1 : ");
        Serial.println(c1);
      }
      channel[cn] += c1;
      if (n % (READ_COUNTER_REGISTER_FREQ*sampling_rate) == 0) {
        if (DEBUG){
          Serial.print("Frequency on channel ");
          Serial.print(cn);
          Serial.print(": ");
          Serial.print(channel[cn]/sampling_rate);
          Serial.println("Hz");
        }
        else {
          channel[cn]=channel[cn]/sampling_rate;
          unsigned long dc = floor(channel[cn]);
          unsigned int fc = floor((channel[cn]-dc)*10000); 
          SerialPrintf("%06lu.%04d ",dc,fc);
        }
        channel[cn]=0;
        if (cn==NUMBER_OF_CHANNELS-1)
          Serial.println("");
          n=0;  
      }
      else{
        if (DEBUG)
          Serial.println(c1);
      }
    } 
  if(DEBUG)
    Serial.println("ENDS");
  read_counter_register = 0;
  }
}
