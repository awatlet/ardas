#include <Wire.h>
#include <RTClib.h>
#include <EEPROM.h>

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
const byte cp_pin = 12;        // clock for synchronous communication
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
boolean start_flag = true;
unsigned int sampling_rate = 2; // integration time in seconds
Ds1307SqwPinMode modes[] = {SquareWave1HZ, SquareWave4kHz, SquareWave8kHz, SquareWave32kHz};
Ds1307SqwPinMode RTC_freq;

// µDAS interface
String  he, e0, e1, e2, ri, sd, rv, sr, si,ss, zr, parameter, connect_id;
char EOL;
int station, netid, nb_inst;
int echo = 1;
int addr_station = 0;
int addr_netid = 2;
int addr_sampling_rate = 3;
int addr_nb_inst = 5;
String s;

String VERSION = "Version ARDAS 0.6 [2013-2015]";

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

// µDAS interface
void EEPROMWriteOnTwoBytes (int address, int value) {
	byte two = (value & 0xFF);
	byte one = ((value >> 8) & 0xFF);

	EEPROM.write (address, two);
	EEPROM.write (address +1, one);
}

int EEPROMReadTwoBytes (int address) {   // TODO : unsigned int
	int two = EEPROM.read (address);
	int one = EEPROM.read (address + 1);

	return ((two << 0) & 0xFF) + ((one << 8) & 0xFFFF);
	//return ( ((two << 0) & 0xFF) + ((one << 8) & 0xFFF)));
}



void read_config_or_set_default () {
	station = EEPROMReadTwoBytes (addr_station);
	if (station == 0) {
		station = 1;
	}
	netid = EEPROM.read (addr_netid);
	if (netid == 0) {
		netid = 255;
	}
	sampling_rate = EEPROMReadTwoBytes (addr_sampling_rate);
	if (sampling_rate == 0) {
		sampling_rate = 60;
	}
	nb_inst = EEPROM.read (addr_nb_inst);
	if ( nb_inst == 0) {
		nb_inst = 4;
	}
}

void connect () {
    Serial.print ("!HI ");
    Serial.print (station);
    Serial.print (" ");
    Serial.print (netid);
    Serial.print (" ");
    Serial.print (sampling_rate);
    Serial.print (" ");
    Serial.println (nb_inst);
}

void help () {
	Serial.println ("\n\rHELP COMMAND :");
	Serial.println ("#E0 : No Echo");
	Serial.println ("#E1 : Only Data");
	Serial.println ("#E2 : Data + Time");
	Serial.println ("#SD yyyy mm dd hh nn ss : Set Date + Time");
	Serial.println ("#SR iiii : Set Integration Period");
	Serial.println ("#SS ssss : Set Station Number");
	Serial.println ("#SI nnn : Set DAS Number");
	Serial.println ("#RI : Read Info");
	Serial.println ("#RV : Read version");
	Serial.println ("#ZR ssss nnn iiii s : Reconfig");
}

void set_no_echo () {
	Serial.println ("\n\r!E0[Echo disabled]\n\r");
	echo = 0;
}

void set_echo_data () {
	Serial.println ("!E1\n\r");
	echo = 1;
}

void set_echo_data_and_time () {
	Serial.println ("!E2\n\r");
	echo = 2;
}

/*
void set_date_and_time (String s) {
	if (s.length () == 19) {
		String yr, mh, dy, hr, mn, sd;
		yr = s.substring (4, 8);
		mh = s.substring (9, 11);
		dy = s.substring (12, 13);
		hr = s.substring (14, 15);
		mn = s.substring (16, 17);
		sd = s.substring (18, 19);

		setTime(hr.toInt (), mn.toInt (), sd.toInt (), dy.toInt (), mn.toInt (), yr.toInt ());
		Serial.print("!SD");
		Serial.print(" ");
		Serial.print(year());
		Serial.print(" ");
		Serial.print(month());
		Serial.print(" ");
		Serial.print(day());
		Serial.print(" ");
		Serial.print(minute());
		Serial.print(" ");
		Serial.print(second());
		Serial.println();
	}
}

*/

void get_das_info () {
	SerialPrintf("!RI Station: %04d DasNo: %03d Integration: %04d\n\r", station, netid, sampling_rate);
}

void get_version () {
	Serial.println("!RV " + VERSION + "\n\r");
}


void set_station_id (String s) {
	if (s.length () == 9) {
			parameter = s.substring (4, 8);
		  	station = parameter.toInt ();
		  	EEPROMWriteOnTwoBytes (addr_station, station);
		  	SerialPrintf ("!SS %04d\n\r", station);
		  	// Serial.println (station + "\n\r");
		}
	else {
		  	Serial.print ("!SS value error\n\r");
	}
}

void set_das_netid (String s) {
	if(s.length () == 8) {
			// TODO: check parameter type
		  	parameter = s.substring (4,7);
		  	netid = parameter.toInt ();
		  	EEPROM.write(addr_netid, netid);
		  	Serial.print ("!SI ");
		  	Serial.println (netid);
		}
	else {
			Serial.print ("!SI ");
			Serial.println (netid + "\n\r");
	}
}

void set_sampling_rate (String s) {
  if (s.length () == 9) {
    // TODO: check parameter type
    parameter = s.substring (4,8);
    sampling_rate = parameter.toInt (); // TODO unsigned int 
    EEPROMWriteOnTwoBytes (addr_sampling_rate, sampling_rate);
   }
   SerialPrintf("!SR %04d\n\r", sampling_rate);
}

void reconfig (String s) {
	if (s.length () == 20) {
		String parameter1, parameter2, parameter3, parameter4;
		parameter1 = s.substring (4, 8);
		parameter2 = s.substring (9, 12);
		parameter3 = s.substring (13, 17);
		parameter4 = s.substring (18, 19);

		station = parameter1.toInt ();
		netid = parameter2.toInt ();
		sampling_rate = parameter3.toInt ();
		nb_inst = parameter4.toInt ();

		EEPROMWriteOnTwoBytes(addr_station, station);
		EEPROM.write (addr_netid, netid);
		EEPROMWriteOnTwoBytes (addr_sampling_rate, sampling_rate);
		EEPROM.write (addr_nb_inst, nb_inst);
		delay(100);
		Serial.print ("!ZR ");
		Serial.print (station);
		Serial.print (" ");
		Serial.print (netid);
		Serial.print (" ");
		Serial.print (sampling_rate);
		Serial.print (" ");
		Serial.println (nb_inst);
	}
}

void setup()
{
  Serial.begin(9600);
  Serial.flush ();
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
  RTC.adjust(DateTime(F(__DATE__), F(__TIME__)));
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

  // µDAS interface
  he = String ("#HE");
  e0 = String ("#E0");
  e1 = String ("#E1");
  e2 = String ("#E2");
  ri = String ("#RI");
  sd = String ("#SD");
  rv = String ("#RV");
  sr = String ("#SR");
  si = String ("#SI");
  ss = String ("#SS");
  zr = String ("#ZR");
  EOL = '\r';
  read_config_or_set_default ();
  connect_id = String("-") + String(netid);

  if (DEBUG)
    Serial.println("complete.");
}

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
    first_character = s.substring (0,1);
    if( first_character == "-") {
      String s_netid = s.substring(1,4);
      int recv_netid = s_netid.toInt();
      if (recv_netid == netid) {
        connect ();
      }
    }
    else {
      command = s.substring (0,3);
      if (command == he) {
        help ();
      }
      else if (command == e0) {
        set_no_echo ();
      }
      else if (command == e1) {
        set_echo_data ();
      }
      else if (command == e2) {
        set_echo_data_and_time ();
      }
      else if (command == ri) {
        get_das_info ();
      }
      else if (command == sd) {
        //set_date_and_time (s);
      }
      else if (command == rv) {
        get_version ();
      }
      else if (command == ss) {
        set_station_id (s);
      }
      else if (command == si) {
        set_das_netid (s);
      }
      else if (command == sr) {
        set_sampling_rate (s);
      }
      else if (command == zr) {
        reconfig (s);
      }
      else {
        Serial.println ("Unknown command\n\r");
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
      if (echo != 0)
        SerialPrintf("*%4d %02d %02d %02d %02d %02d ",tic.year(),tic.month(),tic.day(),tic.hour(),tic.minute(),tic.second());
    }
    else if ((echo == 2) && ((n % READ_COUNTER_REGISTER_FREQ) == 0 )) {
      DateTime tic = RTC.now();
        SerialPrintf("*%4d %02d %02d %02d %02d %02d ",tic.year(),tic.month(),tic.day(),tic.hour(),tic.minute(),tic.second());
        Serial.println("");
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
          if (!start_flag){
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
              Serial.print("started counting...");
          }
          if (echo != 0)
            Serial.println("");
        }
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