/***
    Copyright (C) 2013-2015 UMONS

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>

***/

#include <Wire.h>
#include <RTClib.h>
#include <EEPROM.h>
#include <SD.h>

#define PULSE_WIDTH_USEC 5
#define READ_COUNTER_REGISTER_FREQ 2 // should be 1 if freq is 1 Hz
#define CLOCK_FREQ 8192
#define VERSION "Version ARDAS 0.7 [2013-2015]"
#define EOL '\r'
#define ADDR_STATION 0
#define ADDR_NETID 2
#define ADDR_SAMPLING_RATE 3
#define ADDR_NB_INST 5
#define DATA_FILE "data.bin"
const uint8_t x00 = 0;
const uint8_t xFD = 253;
const uint8_t xFE = 254;
const uint8_t xFF = 255;

File data_file;

const int COUNTS_BETWEEN_READINGS = CLOCK_FREQ / READ_COUNTER_REGISTER_FREQ;
const int NUMBER_OF_COUNTERS = 2; // 32 bits counters
const int DATA_WIDTH = NUMBER_OF_COUNTERS * 8; // number of bits returned by daisy-chained SN74HC165N for a call to readbyte
const int NUMBER_OF_CHANNELS_PER_COUNTER = 2; // 1 : 32 bits channels - 2: 16 bits channels
const int NUMBER_OF_CHANNELS = NUMBER_OF_COUNTERS * NUMBER_OF_CHANNELS_PER_COUNTER;
const int BYTES_PER_CHANNEL = 4 / NUMBER_OF_CHANNELS_PER_COUNTER;

boolean DEBUG = false; // true;
boolean download = false;
int freq = CLOCK_FREQ;

RTC_DS1307 RTC;

// Pins
/* RTC */
// Don't forget to connect I2C pins A4 and A5 (5 and 6 of RTC)
const byte rtc_pulse_pin = 2;  // pin for interrupt 0
/* SN74LV8054 */
const byte rclk_pin = 5;      // set selected byte to output
/* 74HC165N */
const byte pl_pin = 8;         // latch pin
const byte cp_pin = 6;        // clock for synchronous communication
const byte q7_pin = 7;        // serial output
const byte ce_pin = 9;         // activation cp clock
/* 74HC595N */
const byte stcp_pin = 15;       // pin connected to ST_CP of 74HC595
const byte shcp_pin = 16;       // pin connected to SH_CP of 74HC595
const byte ds_pin = 14;         // pin connected to DS of 74HC595
/* SD card */
const byte ss_pin = 10;        // pin reserved for SD card output

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
boolean start_flag = true;
unsigned int sampling_rate = 2; // integration time in seconds
Ds1307SqwPinMode modes[] = {SquareWave1HZ, SquareWave4kHz, SquareWave8kHz, SquareWave32kHz};
Ds1307SqwPinMode RTC_freq;

// µDAS interface
int station, netid, nb_inst;
int echo = 1;

String s;

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
      Serial.print(F("Counter(s) byte selection input :"));
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

// µDAS interface
void EEPROMWriteOnTwoBytes(int address, int value) {
	byte two = (value & 0xFF);
	byte one = ((value >> 8) & 0xFF);

	EEPROM.write(address, two);
	EEPROM.write(address +1, one);
}

int EEPROMReadTwoBytes (int address) {   // TODO : unsigned int
	int two = EEPROM.read (address);
	int one = EEPROM.read (address + 1);

	return ((two << 0) & 0xFF) + ((one << 8) & 0xFFFF);
	//return ( ((two << 0) & 0xFF) + ((one << 8) & 0xFFF)));
}

// Get SRAM usage
int freeRam () {
  extern int __heap_start, * __brkval;
  int v;
  return (int) &v - (__brkval == 0 ? (int) &__heap_start:(int) __brkval);
}

void read_config_or_set_default () {
  station = EEPROMReadTwoBytes (ADDR_STATION);
  if (station == 0) {
    station = 1;
  }
  netid = EEPROM.read (ADDR_NETID);
  if (netid == 0) {
    netid = 255;
  }
  sampling_rate = EEPROMReadTwoBytes (ADDR_SAMPLING_RATE);
  if (sampling_rate == 0) {
    sampling_rate = 60;
  }
  nb_inst = EEPROM.read (ADDR_NB_INST);
  if ( nb_inst == 0) {
    nb_inst = 4;
  }
}

void get_info(){
  SerialPrintf(" Station: %04d DasNo: %03d Integration: %04d\n\r", station, netid, sampling_rate);
}

void connect () {
  Serial.print(F("!HI"));
  get_info();
}

void help () {
  Serial.println(F("\n\rHELP COMMAND :"));
  Serial.println(F("#E0 : No Echo"));
  Serial.println(F("#E1 : Only Data"));
  Serial.println(F("#E2 : Data + Time"));
  Serial.println(F("#SD yyyy mm dd hh nn ss : Set Date + Time"));
  Serial.println(F("#SR iiii : Set Integration Period"));
  Serial.println(F("#SS ssss : Set Station Number"));
  Serial.println(F("#SI nnn : Set DAS Number"));
  Serial.println(F("#RI : Read Info"));
  Serial.println(F("#RV : Read version"));
  Serial.println(F("#ZR ssss nnn iiii s : Reconfig"));
}

void set_no_echo () {
  Serial.println(F("\n\r!E0[Echo disabled]\n\r"));
  echo = 0;
}

void set_echo_data () {
  Serial.println(F("!E1\n\r"));
  echo = 1;
}

void set_echo_data_and_time () {
  Serial.println(F("!E2\n\r"));
  echo = 2;
}

void set_date_and_time (String s) {
  int yr, mh, dy, hr, mn, sc;

  if (s.length() == 24) {
    yr = s.substring(4, 8).toInt();
    mh = s.substring(9, 11).toInt();
    dy = s.substring(12, 14).toInt();
    hr = s.substring(15, 17).toInt();
    mn = s.substring(18, 20).toInt();
    sc = s.substring(21, 23).toInt();
    RTC.adjust(DateTime(yr, mh, dy, hr, mn, sc));
    RTC.writeSqwPinMode(RTC_freq);
    SerialPrintf("!SD %04d %02d %02d %02d %02d %02d\n\r", yr, mh, dy, hr, mn, sc);
  }
  else {
    Serial.print(F("!SD value error\n\r"));
  }
}

void get_das_info () {
  Serial.print(F("!RI"));
  get_info();
}

void get_version () {
  Serial.print(F("!RV "));
  Serial.print(VERSION);
  Serial.println(F("\n\r"));
}


void set_station_id (String s) {
  if (s.length() == 9) {
    station = s.substring(4, 8).toInt();
    EEPROMWriteOnTwoBytes(ADDR_STATION, station);
    SerialPrintf ("!SS %04d\n\r", station);
  }
  else {
    Serial.print(F("!SS value error\n\r"));
  }
}

void set_das_netid (String s) {
  if(s.length() == 8) {
    netid = s.substring(4,7).toInt();
    EEPROM.write(ADDR_NETID, netid);
  }
  SerialPrintf("!SI %03d\n\r",netid);
}

void set_sampling_rate (String s) {
  if (s.length() == 9) {
    // TODO: check parameter type
    sampling_rate = s.substring(4,8).toInt(); // TODO unsigned int
    EEPROMWriteOnTwoBytes(ADDR_SAMPLING_RATE, sampling_rate);
    start_flag = true;
   }
   SerialPrintf("!SR %04d\n\r", sampling_rate);
}

void reconfig (String s) {
  if (s.length() == 20) {
    station = s.substring(4, 8).toInt();
    netid = s.substring(9, 12).toInt();
    sampling_rate = s.substring(13, 17).toInt();
    nb_inst = s.substring(18, 19).toInt();

    EEPROMWriteOnTwoBytes(ADDR_STATION, station);
    EEPROM.write(ADDR_NETID, netid);
    EEPROMWriteOnTwoBytes(ADDR_SAMPLING_RATE, sampling_rate);
    EEPROM.write(ADDR_NB_INST, nb_inst);
    delay(100);
    Serial.print(F("!ZR"));
    get_info();
    start_flag = true;
  }
  else{
    Serial.print(F("!ZR value error\n\r"));
  }
}

/***
SETUP
***/

void setup()
{
  int free_ram;
  Serial.begin(9600);
  Serial.flush ();
  Wire.begin();
  if (DEBUG)
    Serial.print(F("Setup"));
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
         Serial.print(F("Warning : invalid frequency. Reset to default !"));
  }
  RTC.begin();
  RTC.adjust(DateTime(F(__DATE__), F(__TIME__)));
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
        Serial.print(F("Error : invalid number of channels! "));
        Serial.println(NUMBER_OF_CHANNELS_PER_COUNTER);
  }
  if (DEBUG)
    Serial.print(F("."));

  pinMode(rclk_pin, OUTPUT);
  pinMode(pl_pin, OUTPUT);
  pinMode(ce_pin, OUTPUT);
  pinMode(cp_pin, OUTPUT);
  pinMode(q7_pin, INPUT);
  pinMode(stcp_pin, OUTPUT);
  pinMode(shcp_pin, OUTPUT);
  pinMode(ds_pin, OUTPUT);
  pinMode(ss_pin, OUTPUT);

  Serial.println(F("Initializing SD card ..."));
  if (!SD.begin(4)) {
    Serial.println(F("Initialisation failed !"));
    return;
  }
  Serial.println(F("Initialization done !"));
  SD.remove(DATA_FILE); // TODO :  remove this line
  data_file = SD.open(DATA_FILE,FILE_WRITE);
  data_file.write(xFF);
  data_file.write(xFF);
  DateTime tic = RTC.now();
  uint32_t t = tic.unixtime();
  data_file.write((byte *) &t,4);
  for (int i=0; i<6; i++)
     data_file.write((byte) 0,1);
  data_file.flush();
  int init = 0;
  for (int i=0; i<NUMBER_OF_COUNTERS; i++){
    init = init << 4;
    init+=7;
  }
  digitalSerialWrite(init);
  digitalWrite(rclk_pin, LOW);
  if (DEBUG)
    Serial.print(F("."));

  digitalWrite(cp_pin, LOW);
  digitalWrite(pl_pin, HIGH);
  read_shift_regs();
  if (DEBUG)
    Serial.print(F("."));

  digitalWrite(stcp_pin, LOW);
  shiftOut(ds_pin, shcp_pin, MSBFIRST, 0);
  digitalWrite(stcp_pin, HIGH);

  attachInterrupt(0, rtc_interrupt, RISING);

  // µDAS interface
  read_config_or_set_default ();
  //connect_id = String("-") + String(netid);

  if (DEBUG)
    Serial.println(F("complete."));
  free_ram = freeRam();
  Serial.print(free_ram);
}

/***
LOOP
***/

void loop(){
  char c;
  String command, first_character;


  // send data only when you receive data:
  do {
    if (Serial.available () > 0) {
      // read the incoming bytes
      c = Serial.read ();
      s += c;
    }
  }
  while ((c != EOL) && (!read_counter_register));

  if (c == EOL){
    // say hi
    first_character = s.substring(0,1);
    if( first_character == "-") {
      String s_netid = s.substring(1,4);
      int recv_netid = s_netid.toInt();
      if (recv_netid == netid) {
        connect ();
      }
    }
    else {
      command = s.substring(0,3);
      if (command == "#HE") {
        help ();
      }
      else if (command == "#E0") {
        set_no_echo ();
      }
      else if (command == "#E1") {
        set_echo_data ();
      }
      else if (command == "#E2") {
        set_echo_data_and_time ();
      }
      else if (command == "#RI") {
        get_das_info ();
      }
      else if (command == "#SD") {
        set_date_and_time (s);
      }
      else if (command == "#RV") {
        get_version ();
      }
      else if (command == "#SS") {
        set_station_id (s);
      }
      else if (command == "#SI") {
        set_das_netid (s);
      }
      else if (command == "#SR") {
        set_sampling_rate (s);
      }
      else if (command == "#ZR") {
        reconfig (s);
      }
      else if (command == "#DG") {
        DEBUG = !DEBUG;
        if (DEBUG)
          Serial.print(F("Debug mode on ! \n\r"));
        else
          Serial.print(F("Debug mode off ! \n\r"));
      }
      else {
        if (DEBUG)
          Serial.print(F("Unknown command :"));
          Serial.print(command);
          Serial.println(F("\n\r"));
        Serial.println(F("Unknown command\n\r"));
      }
    }
    s = "";
  }

  if(read_counter_register){
    // TODO : read time on RTC and substract half of the integration period
    n += 1;
    if (n % (READ_COUNTER_REGISTER_FREQ*sampling_rate) == 0) {
      DateTime now = RTC.now();
      DateTime tic = now.unixtime() - uint32_t(sampling_rate/2.0);
      if (!start_flag){
        if (echo != 0)
          SerialPrintf("*%4d %02d %02d %02d %02d %02d ",tic.year(),tic.month(),tic.day(),tic.hour(),tic.minute(),tic.second());
        if (data_file) {
          uint32_t t = tic.unixtime();
          data_file.write((byte *) &t,4);
        }
      }
    }
    else if ((echo == 2) && ((n % READ_COUNTER_REGISTER_FREQ) == 0 )) {
      DateTime tic = RTC.now();
        SerialPrintf("*%4d %02d %02d %02d %02d %02d ",tic.year(),tic.month(),tic.day(),tic.hour(),tic.minute(),tic.second());
        Serial.println("");
    }
    if(DEBUG){
      Serial.println(F("BEGINS..."));
    }
    for(cn=0; cn < NUMBER_OF_CHANNELS; cn++){
      if(DEBUG){
        Serial.print(F("Channel "));
        Serial.println(cn);
      }
      previous_count[cn]  =  current_count[cn];
      current_count[cn] = 0;
      if(DEBUG){
        Serial.print(F("Previous count: "));
        Serial.println(previous_count[cn]);
      }
    }
    // read bytes corresponding to each of the 4 bytes for each counter ([byte 0 of Counter 0, byte 0 of counter 1] than [byte 1 of Counter 0, byte 1 of counter 1] ...)
    for(int i=3;i>=0;i--){
      read_bytes(i);
      if(DEBUG){
        Serial.println("");
        Serial.print(F("byte "));
        Serial.print(i);
        Serial.print(" : ");
        for (int j=0;j<NUMBER_OF_COUNTERS;j++){
          Serial.print(b[j]);
          Serial.print(F(" | "));
        }
      }
      int k = i / BYTES_PER_CHANNEL; // which channel relative to each counter
      int l = i % BYTES_PER_CHANNEL; // which byte of the channel
      for (int j=0; j<NUMBER_OF_COUNTERS; j++){
        cn=NUMBER_OF_CHANNELS_PER_COUNTER*j+k;
        current_count[cn] += (unsigned long)b[j] << (8 * l);
        if(DEBUG){
          Serial.println("");
          Serial.print(F("byte :"));
          Serial.print(i);
          Serial.print(F(" | channel :"));
          Serial.print(cn);
          Serial.print(F(" | channel relative to counter :"));
          Serial.print(k);
          Serial.print(F(" | channel byte :"));
          Serial.print(l);
          Serial.print(F(" : "));
          Serial.print(b[j]);
          Serial.print(F(" | value :"));
          Serial.print((unsigned long)b[j] << (8 * l));
        }
      }
    }
    for (cn=0;cn<NUMBER_OF_CHANNELS;cn++){
      if(DEBUG)
        Serial.println(F(" . "));
      if(current_count[cn] >= previous_count[cn]){
        c1 = current_count[cn] - previous_count[cn];
      }
      else{
        if (DEBUG)
          Serial.print(F("$"));
        c1 = (counter_overflow - previous_count[cn]) + current_count[cn];
      }
      if(DEBUG){
        Serial.print(F("Current count: "));
        Serial.println(current_count[cn]);
        Serial.print(F(" : "));
        Serial.print(F("c1 : "));
        Serial.println(c1);
      }
      channel[cn] += c1;
      if (n % (READ_COUNTER_REGISTER_FREQ*sampling_rate) == 0) {
        if (DEBUG){
          Serial.print(F("Frequency on channel "));
          Serial.print(cn);
          Serial.print(F(": "));
          Serial.print(channel[cn]/sampling_rate);
          Serial.println(F("Hz"));
        }
        else {
          if (!start_flag){
            if (data_file){
              uint32_t x = (uint32_t) channel[cn];
              data_file.write((byte *) &x,4);
            }
            channel[cn]=channel[cn]/sampling_rate;
            unsigned long dc = floor(channel[cn]);
            unsigned int fc = floor((channel[cn]-dc)*10000);
            if (echo != 0)
              SerialPrintf("%06lu.%04d ",dc,fc);
          }
        }
        channel[cn]=0;
        if (cn==NUMBER_OF_CHANNELS-1)
        {
          if (start_flag)
          {
            start_flag = false;
            if (DEBUG)
              Serial.print(F("started counting..."));
          }
          else if (data_file)
            data_file.flush();
          if (echo != 0)
            Serial.println(F(""));
        }
        n=0;
      }
      else{
        if (DEBUG)
          Serial.println(c1);
      }
    }
  if(DEBUG)
    Serial.println(F("ENDS"));
  read_counter_register = 0;
  }
}