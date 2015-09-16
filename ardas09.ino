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
#include <SPI.h>
#include <avr/wdt.h>

#define PULSE_WIDTH_USEC 5
#define READ_COUNTER_REGISTER_FREQ 2 // CHECK : should be 1 if freq is 1 Hz
#define CLOCK_FREQ 4096
#define VERSION "Version ARDAS 0.9b [2013-2015]"
#define EOL '\r'
#define ADDR_STATION 0
#define ADDR_NETID 2
#define ADDR_SAMPLING_RATE 3
#define ADDR_NB_INST 5
#define ADDR_I1 7
#define ADDR_I2 9
#define ADDR_I3 11
#define ADDR_I4 13

#define DATA_FILE "data.raw"

File data_file;

const uint16_t COUNTS_BETWEEN_READINGS = CLOCK_FREQ / READ_COUNTER_REGISTER_FREQ;
const uint8_t NUMBER_OF_COUNTERS = 2; // 32 bits counters
const uint8_t NUMBER_OF_CHANNELS_PER_COUNTER = 2; // 1 : 32 bits channels - 2: 16 bits channels
const uint8_t NUMBER_OF_CHANNELS = NUMBER_OF_COUNTERS * NUMBER_OF_CHANNELS_PER_COUNTER;
const uint8_t BYTES_PER_CHANNEL = 4 / NUMBER_OF_CHANNELS_PER_COUNTER;

boolean DEBUG = false; // true;
boolean quiet = true; //
uint8_t freq = CLOCK_FREQ;

RTC_DS1307 RTC;

// Pins
/* RTC */
// Don't forget to connect I2C pins A4 and A5 (5 and 6 of RTC)
// rtc_pulse on pin 2 for interrupt 0
/* SN74LV8054 */
const uint8_t rclk_pin = 5;       // set selected byte to output
/* 74HC165N */
const uint8_t pl_pin = 8;         // latch pin
const uint8_t cp_pin = 6;         // clock for synchronous communication
const uint8_t q7_pin = 7;         // serial output
const uint8_t ce_pin = 9;         // activation cp clock
/* 74HC595N */
const uint8_t stcp_pin = 15;       // pin connected to ST_CP of 74HC595
const uint8_t shcp_pin = 16;       // pin connected to SH_CP of 74HC595
const uint8_t ds_pin = 14;         // pin connected to DS of 74HC595
/* SD card */
const uint8_t ss_pin = 10;         // pin reserved for SD card output
const uint8_t cs_pin = 4;      // CS pin for SD card (4 on Ethernet shield)

//others
volatile uint16_t pulse_counter = 0;
volatile boolean read_counter_register = false;
uint32_t channel[NUMBER_OF_CHANNELS];
uint32_t c1=0;
uint32_t counter_overflow;
uint32_t previous_count[NUMBER_OF_CHANNELS];
uint32_t current_count[NUMBER_OF_CHANNELS];
uint8_t b[NUMBER_OF_COUNTERS]; // incoming bytes
uint8_t B[4]; // for reading uint32_t on SD card and reversing bit order
uint8_t cn = 0;
uint16_t n = 0;
boolean start_flag = true;
uint16_t sampling_rate = 2; // integration time in seconds
Ds1307SqwPinMode modes[] = {SquareWave1HZ, SquareWave4kHz, SquareWave8kHz, SquareWave32kHz};
Ds1307SqwPinMode RTC_freq;

// µDAS interface
uint8_t netid, nb_inst;
uint16_t station;
uint16_t inst[NUMBER_OF_CHANNELS];
uint8_t echo = 0;
boolean download_flag = false;
uint32_t p; // current position in the data_file
uint8_t record[30];

String s;

void rtc_interrupt()
{
    // after each integration period
    if (pulse_counter % COUNTS_BETWEEN_READINGS == 0){
        digitalWrite(rclk_pin, HIGH);
        digitalWrite(rclk_pin, LOW);

        read_counter_register = true;

    }
    pulse_counter ++;

}

//void(* reset) (void) = 0;//declare reset function at address 0
/* alternative possibly better one using the watchdog...
check ram usage...
#include <avr/wdt.h>
*/
void software_reset()
{
    wdt_enable(WDTO_15MS);
    while(1)
    {
    }
}

void SerialPrintf(char *format,...)
{
    char buff[80];
    va_list args;
    va_start (args,format);
    vsnprintf(buff,sizeof(buff),format,args);
    va_end (args);
    buff[sizeof(buff)/sizeof(buff[0])-1]='\0';
    Serial.print(buff);
}

void read_shift_regs()
{
    uint32_t bitVal;  // check type

    digitalWrite(ce_pin, HIGH);
    digitalWrite(pl_pin, LOW);
    delayMicroseconds(PULSE_WIDTH_USEC);
    digitalWrite(pl_pin, HIGH);
    digitalWrite(ce_pin, LOW);
    for(int j = 0; j < NUMBER_OF_COUNTERS; j++){
        b[j] = 0;
        for(int i = 0; i < 8; i++)
        {
            bitVal = (uint32_t) digitalRead(q7_pin);
            b[j] |= (bitVal << (7 - i));
            digitalWrite(cp_pin, HIGH);
            delayMicroseconds(PULSE_WIDTH_USEC);
            digitalWrite(cp_pin, LOW);
        }
    }
}

void read_bytes(uint8_t byte_number) {
    uint8_t val;

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
    delayMicroseconds(PULSE_WIDTH_USEC);
    read_shift_regs();
    delayMicroseconds(PULSE_WIDTH_USEC);
}

void digitalSerialWrite(uint8_t Val)
{
    digitalWrite(stcp_pin, LOW);
    shiftOut(ds_pin, shcp_pin, MSBFIRST, Val);
    digitalWrite(stcp_pin, HIGH);
}

// µDAS interface
void EEPROMWriteOnTwoBytes(uint8_t address, uint8_t value) {
    uint8_t two = (value & 0xFF);
    uint8_t one = ((value >> 8) & 0xFF);

    EEPROM.write(address, two);
    EEPROM.write(address +1, one);
}

uint16_t EEPROMReadTwoBytes (uint8_t address) {
    uint8_t two = EEPROM.read (address);
    uint8_t one = EEPROM.read (address + 1);

    return ((two << 0) & 0xFF) + ((one << 8) & 0xFFFF);
}

// Get SRAM usage
int freeRam() {
    extern int __heap_start, * __brkval;
    int v;
    return (int) &v - (__brkval == 0 ? (int) &__heap_start:(int) __brkval);
}

void read_config_or_set_default() {
    station = EEPROMReadTwoBytes(ADDR_STATION);
    if (station == 0) {
        station = 1;
    }
    netid = EEPROM.read(ADDR_NETID);
    if (netid == 0) {
        netid = 255;
    }
    sampling_rate = EEPROMReadTwoBytes(ADDR_SAMPLING_RATE);
    if (sampling_rate == 0) {
        sampling_rate = 60;
    }
    nb_inst = EEPROM.read(ADDR_NB_INST);
    if ( nb_inst == 0) {
        nb_inst = NUMBER_OF_CHANNELS;
    }
}

void get_info(){
    Serial.print(F(" Station: "));
    SerialPrintf("%04d", station);
    Serial.print(F(" DasNo: "));
    SerialPrintf("%03d", netid);
    Serial.print(F(" Integration: "));
    SerialPrintf("%04d", sampling_rate);
    Serial.print(F("\n\r"));
}

void connect() {
    Serial.print(F("!HI "));
    SerialPrintf("%04d %03d %04d %1d %04d %04d %04d %04d 0 133256 ", station, netid, sampling_rate, nb_inst, inst[0], inst[1], inst[2], inst[3]); // TODO implement nb_inst!=4 + memory usage
    Serial.print(F("\n\r\n\r"));
    echo = 2;
}

void help() {
    Serial.print(F("\n\rHELP COMMAND :\n\r\n\r"));
    Serial.print(F("#E0 : No Echo\n\r\n\r"));
    Serial.print(F("#E1 : Only Data\n\r\n\r"));
    Serial.print(F("#E2 : Data + Time\n\r\n\r"));
    Serial.print(F("#SD yyyy mm dd hh nn ss : Set Date + Time\n\r\n\r"));
    Serial.print(F("#SR iiii : Set Integration Period\n\r\n\r"));
    Serial.print(F("#SI nnn : Set uDAS Number\n\r\n\r"));
    Serial.print(F("#SS ssss : Set Station Number\n\r\n\r"));
    Serial.print(F("#RI : Read Info\n\r\n\r"));
    Serial.print(F("#RL : Read Last Data\n\r\n\r")); // TODO : implement this
    Serial.print(F("#RM : Read Memory Status\n\r\n\r")); // TODO : implement this
    Serial.print(F("#RV : Read version\n\r\n\r")); // NOTE : not present on uDAS v3.05
    Serial.print(F("#ZR ssss nnn iiii s 1111 2222 3333 4444 XX: Reconfig\n\r\n\r"));
    Serial.print(F("#XB : Full Download\n\r\n\r"));
    Serial.print(F("#XP yyyy mm dd hh nn ss yyyy mm dd hh nn ss : Partial Download\n\r\n\r")); // NOTE : implement this
    Serial.print(F("#XN : Next Download\n\r\n\r")); // NOTE : implement this
    Serial.print(F("#WB : Write line in workbook\n\r\n\r")); // NOTE : implement this
    Serial.print(F("#RW : Read workbook\n\r\n\r")); // NOTE : implement this
    Serial.print(F("#?? : This text\n\r\n\r")); // NOTE : implement this 
    Serial.print(F("Enter your command : "));
}

void set_no_echo() {
    Serial.println(F("\n\r!E0 [Echo disabled]\n\r"));
    echo = 0;
}

void set_echo_data() {
    Serial.println(F("!E1\n\r"));
    echo = 1;
}

void set_echo_data_and_time() {
    Serial.println(F("!E2\n\r"));
    echo = 2;
}

void set_date_and_time(String s) {
    uint16_t yr;
    uint8_t mh, dy, hr, mn, sc;

    if (s.length() == 24) {
        yr = (uint16_t) s.substring(4, 8).toInt();
        mh = (uint8_t) s.substring(9, 11).toInt();
        dy = (uint8_t) s.substring(12, 14).toInt();
        hr = (uint8_t) s.substring(15, 17).toInt();
        mn = (uint8_t) s.substring(18, 20).toInt();
        sc = (uint8_t) s.substring(21, 23).toInt();
        RTC.adjust(DateTime(yr, mh, dy, hr, mn, sc));
        RTC.writeSqwPinMode(RTC_freq);
        Serial.print(F("!SD "));
        SerialPrintf("%04d %02d %02d %02d %02d %02d", yr, mh, dy, hr, mn, sc);
        Serial.print(F("\n\r"));
    }
    else {
        Serial.print(F("!SD value error\n\r"));
    }
}

void get_das_info() {
    Serial.print(F("!RI"));
    get_info();
}

void get_version() {
    Serial.print(F("!RV "));
    Serial.print(VERSION);
    Serial.print(F("\n\r"));
}


void set_station_id(String s) {
    if (s.length() == 9) {
        station = (uint16_t) s.substring(4, 8).toInt();
        EEPROMWriteOnTwoBytes(ADDR_STATION, station);
        Serial.print(F("! SS "));
        SerialPrintf("%04d", station);
        Serial.print(F("\n\r"));
    }
    else {
        Serial.print(F("!SS value error\n\r"));
    }
}

void set_das_netid(String s) {
    if(s.length() == 8) {
        netid = (uint8_t) s.substring(4,7).toInt();
        EEPROM.write(ADDR_NETID, netid);
    }
    Serial.print(F("!SI "));
    SerialPrintf("%03d",netid);
    Serial.print(F("\n\r"));
}

void set_sampling_rate(String s) {
    if (s.length() == 9) {
        // TODO: check parameter type
        sampling_rate = (uint16_t) s.substring(4,8).toInt(); // TODO unsigned int
        EEPROMWriteOnTwoBytes(ADDR_SAMPLING_RATE, sampling_rate);
        start_flag = true;
    }
    Serial.print(F("!SR "));
    SerialPrintf("%04d", sampling_rate);
    Serial.print(F("\n\r"));
}

void reconfig(String s){ // NOTE : hard coded for 4 instruments
    if (s.length() == 40) {
        station = (uint16_t) s.substring(4, 8).toInt();
        netid = (uint8_t) s.substring(9, 12).toInt();
        sampling_rate = (uint16_t) s.substring(13, 17).toInt();
        nb_inst = (uint8_t) s.substring(18, 19).toInt();
        inst[0] = (uint16_t) s.substring(20,24).toInt();
        inst[1] = (uint16_t) s.substring(25,29).toInt();
        inst[2] = (uint16_t) s.substring(30,34).toInt();
        inst[3] = (uint16_t) s.substring(35,39).toInt();
        

        EEPROMWriteOnTwoBytes(ADDR_STATION, station);
        EEPROM.write(ADDR_NETID, netid);
        EEPROMWriteOnTwoBytes(ADDR_SAMPLING_RATE, sampling_rate);
        EEPROM.write(ADDR_NB_INST, nb_inst);
        EEPROMWriteOnTwoBytes(ADDR_I1, inst[0]);
        EEPROM.write(ADDR_I1, inst[0]);
        EEPROMWriteOnTwoBytes(ADDR_I2, inst[1]);
        EEPROM.write(ADDR_I2, inst[1]);
        EEPROMWriteOnTwoBytes(ADDR_I3, inst[2]);
        EEPROM.write(ADDR_I3, inst[2]);
        EEPROMWriteOnTwoBytes(ADDR_I4, inst[3]);
        EEPROM.write(ADDR_I4, inst[3]);
        delay(100);
        Serial.print(F("!ZR"));
        get_info();
        start_flag = true;
    }
    else{
        Serial.print(F("!ZR value error\n\r"));
    }
}

void interrupt_download(){
    Serial.print(F("!XS\n\r"));
    download_flag = false;
}

void write_data_header(uint32_t t){
    record[0]=(uint8_t) (sampling_rate >> 8) & 0xFF;
    record[1]=(uint8_t) sampling_rate & 0xFF;
    record[2]=(uint8_t) (t >> 24) & 0xFF;
    record[3]=(uint8_t) (t >> 16) & 0xFF;
    record[4]=(uint8_t) (t >> 8) & 0xFF;
    record[5]=(uint8_t) t & 0xFF;
    for (int i=1;i<=nb_inst;i++){
        record[4+2*i]=(uint8_t) (station >> 8) & 0xFF;
        record[4+2*i+1]=(uint8_t) station & 0xFF;
    }
}

void download_record(){
    uint32_t temp;

    data_file.seek(p);
    if (p+6+6*nb_inst < data_file.size()) {
        B[0] = (uint8_t) data_file.read();
        B[1] = (uint8_t)data_file.read();
        if ((B[0] == 0x00) && B[1] == 0x00) { // restart after power interruption or reset
            Serial.write(0xFF);
            Serial.write(0xFF);
            for (int i=0;i<4;i++){
                B[i] = (uint8_t) data_file.read();
            }
            for (int i=0;i<4;i++){
                Serial.write(B[i]);
            }
            for (int i=0;i<3*nb_inst-6;i++){
                Serial.write(0x00);
            }
            p+=6+6*nb_inst;
        }
        else {
            p+=6+2*nb_inst;
            data_file.seek(p);
            for (int j=0; j<nb_inst; j++){
                temp = 0UL; // BEWARE OF THE TYPE UL OTHERWISE BITWISE OPERATIONS WILL FAIL
                for (int i=0;i<4;i++){
                    B[i] = (uint8_t) data_file.read();
                    temp += (uint32_t) B[i] << (8*(3-i));  // counters are stored in SD card as big endian uint32
                }
                temp = temp >> 1; // in nanoDAS, stored uint8_t values in counters are half the counted values !
                for (int i=3;i>=0;i--){
                    B[i] = (uint8_t) temp % 256;
                    temp = temp >> 8;
                }
                for (int i=1;i<4;i++){
                    Serial.write(B[i]); // Write 3 bytes per channel in little endian
                }
            }
            p+=4*nb_inst;
        }
    }
    else if (p+6+6*nb_inst == data_file.size()){
        for (int i=0;i<3*nb_inst; i++){
            Serial.write(0xFE);
        }
        download_flag = false;
    }
    else {
        Serial.print(F("incorrect file size ! "));
        Serial.println(data_file.size());
        Serial.println(p);
    }
}

void full_download(){

    echo=0;
    download_flag = true;
    for (int i=0;i<3*nb_inst; i++)
        Serial.write(0xFD);
    p=0;
}

/***
SETUP
***/

void setup()
{
    int free_ram;
    Serial.begin(9600);
    Serial.flush();
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
    //RTC.adjust(DateTime(F(__DATE__), F(__TIME__))); // Do not leave this uncommented otherwise clock time while be resetted to time of last upload each time reset button is pressed
    RTC.writeSqwPinMode(RTC_freq);

    for (int8_t i=0; i<NUMBER_OF_CHANNELS; i++){
        channel[i] = 0UL;
        previous_count[i] = 0UL;
        current_count[i] = 0UL;
    }

    switch(NUMBER_OF_CHANNELS_PER_COUNTER){ // fix this switch : it always uses default check type of NUMBER_OF_CHANNELS_PER_COUNTER
        case 1:
            counter_overflow = 2147483648UL;
        case 2:
            counter_overflow = 65536UL;
        default :
            counter_overflow = 65536UL;
    }

    pinMode(rclk_pin, OUTPUT);
    pinMode(pl_pin, OUTPUT);
    pinMode(ce_pin, OUTPUT);
    pinMode(cp_pin, OUTPUT);
    pinMode(q7_pin, INPUT);
    pinMode(stcp_pin, OUTPUT);
    pinMode(shcp_pin, OUTPUT);
    pinMode(ds_pin, OUTPUT);
    pinMode(ss_pin, OUTPUT);


    uint8_t init = 0;
    for (int i=0; i<NUMBER_OF_COUNTERS; i++){
        init = init << 4;
        init+=7;
    }
    digitalSerialWrite(init);
    digitalWrite(rclk_pin, LOW);

    digitalWrite(cp_pin, LOW);
    digitalWrite(pl_pin, HIGH);
    read_shift_regs();

    digitalWrite(stcp_pin, LOW);
    shiftOut(ds_pin, shcp_pin, MSBFIRST, 0);
    digitalWrite(stcp_pin, HIGH);

    // µDAS interface
    read_config_or_set_default();
    //connect_id = String("-") + String(netid);

    Serial.println(F("Initializing SD card ..."));
    if (!SD.begin(cs_pin)) {
        Serial.println(F("Initialisation failed !"));
        return;
    }
    Serial.println(F("Initialization done !"));
    SD.remove(DATA_FILE); // TODO :  remove this line
    data_file = SD.open(DATA_FILE, FILE_WRITE);
    DateTime tic = RTC.now();
    uint32_t t = tic.unixtime();
    t = t + uint32_t(1.5*sampling_rate); // skip first value
    for(uint8_t i=0;i<2;i++){
        record[i]=(uint8_t) 0x00;
    }
    record[2]=(uint8_t) (t >> 24) & 0xFF;
    record[3]=(uint8_t) (t >> 16) & 0xFF;
    record[4]=(uint8_t) (t >> 8) & 0xFF;
    record[5]=(uint8_t) t & 0xFF;
    for(int i=6;i<30;i++){
        record[i]=(uint8_t) 0x00;
    }
    data_file.write(record,30);
    data_file.flush();
    free_ram = freeRam();
    Serial.println(free_ram);

    attachInterrupt(0, rtc_interrupt, RISING);
}

/***
LOOP
***/

void loop(){
    char c;
    String command, first_character;

    // send data only when you receive data:
    int i=0;
    do {
        if (Serial.available() > 0) {
            // read the incoming bytes
            c = Serial.read();
            s += c;
        }
        i+=1;
    }
    while ((c != EOL) && (!read_counter_register));

    if (c == EOL){
        // say hi
        first_character = s.substring(0,1);
        if( first_character == "-") {
            String s_netid = s.substring(1,4);
            uint16_t recv_netid = (uint16_t) s_netid.toInt();
            if (recv_netid == (uint16_t) netid) {
                connect ();
                quiet = false;
            }
            else if ((uint16_t) recv_netid == (uint16_t) 999) {
              Serial.print(F("\n\r\n\rHey! I'm ArdDAS "));
              SerialPrintf("%03d", netid);
              Serial.print(F("\n\r\n\r"));
            }
            else{
                quiet = true;
                echo=0;
            }
        }
        else if (first_character == "#") {
            command = s.substring(1,3);
            if ((!download_flag) && (!quiet)){
                if (command == "HE") {
                    help();
                }
                else if (command == "E0") {
                    set_no_echo();
                }
                else if (command == "E1") {
                    set_echo_data();
                }
                else if (command == "E2") {
                    set_echo_data_and_time();
                }
                else if (command == "RI") {
                    get_das_info();
                }
                else if (command == "SD") {
                    set_date_and_time(s);
                }
                else if (command == "RV") {
                    get_version();
                }
                else if (command == "SS") {
                    set_station_id(s);
                }
                else if (command == "SI") {
                    set_das_netid(s);
                }
                else if (command == "SR") {
                    set_sampling_rate(s);
                }
                else if (command == "ZR") {
                    reconfig(s);
                }
                else if (command == "ZF") { // TODO : Full ZF implementation to be done...
                    if (data_file){
                        data_file.close();
                        SD.remove(DATA_FILE);
                    }
                    software_reset();
                }
                else if (command == "XB") {
                    full_download();
                }
                else if (command == "XS") {
                }
                else if (command == "EL") {
                    data_file.flush();
                    data_file.close();
                    Serial.print(F("Logging ended : you can safely remove the SD card... \n\r"));
                }
                else if (command == "DG") {
                    DEBUG = !DEBUG;
                    if (DEBUG)
                        Serial.print(F("Debug mode ON\n\r"));
                    else
                        Serial.print(F("Debug mode OFF\n\r"));
                }
                else {
                    Serial.print(F("\n\r!ERROR : Unknown Command\n\r\n\r"));
                }
            }
            if (command == "XS") {
                interrupt_download();
            }
        }
        s = "";
    }

    if(read_counter_register){
        n += 1;
        if (n % (READ_COUNTER_REGISTER_FREQ*sampling_rate) == 0) {
            //DateTime now = RTC.now();
            DateTime tic = RTC.now().unixtime() - uint32_t(sampling_rate/2.0); // read time on RTC and substract half of the integration period
            if (!start_flag){
                if (echo != 0){
                    Serial.print(F("*"));
                    SerialPrintf("%4d %02d %02d %02d %02d %02d",tic.year(),tic.month(),tic.day(),tic.hour(),tic.minute(),tic.second());
                    Serial.print(F(" "));
                }
                if (data_file) {
                    uint32_t t = tic.unixtime();
                    write_data_header(t);
                }
            }
        }
        else if ((echo == 2) && ((n % READ_COUNTER_REGISTER_FREQ) == 0 )) {
            DateTime tic = RTC.now();
            Serial.print(F("!"));
            SerialPrintf("%4d %02d %02d %02d %02d %02d",tic.year(),tic.month(),tic.day(),tic.hour(),tic.minute(),tic.second());
            Serial.print(F(" \n\r\n\r"));
        }
        for(cn=0; cn < NUMBER_OF_CHANNELS; cn++){
            previous_count[cn]  =  current_count[cn];
            current_count[cn] = 0;
        }
        // read bytes corresponding to each of the 4 bytes for each counter ([byte 0 of Counter 0, byte 0 of counter 1] than [byte 1 of Counter 0, byte 1 of counter 1] ...)
        for(int i=3;i>=0;i--){
            read_bytes(i);
            uint8_t k = i / BYTES_PER_CHANNEL; // which channel relative to each counter
            uint8_t l = i % BYTES_PER_CHANNEL; // which byte of the channel
            for (int j=0; j<NUMBER_OF_COUNTERS; j++){
                cn=NUMBER_OF_CHANNELS_PER_COUNTER*j+k;
                current_count[cn] += (uint32_t)b[j] << (8 * l);
            }
        }
        for (cn=0;cn<NUMBER_OF_CHANNELS;cn++){
            if(current_count[cn] >= previous_count[cn]){
                c1 = current_count[cn] - previous_count[cn];
            }
            else{
                c1 = (counter_overflow - previous_count[cn]) + current_count[cn];
            }
            channel[cn] += c1;
            if (n % (READ_COUNTER_REGISTER_FREQ*sampling_rate) == 0) {
                if (!start_flag){
                    uint32_t x = channel[cn];
                    if (data_file){
                        int u = 6+2*nb_inst+cn*4;
                        record[u]=(uint8_t) (x >> 24) & 0xFF;
                        record[u+1]=(uint8_t) (x >> 16) & 0xFF;
                        record[u+2]=(uint8_t) (x >> 8) & 0xFF;
                        record[u+3]=(uint8_t) x & 0xFF;
                    }
                    float xf = channel[cn]/(1.0*sampling_rate);
                    uint32_t dc = floor(xf);
                    uint16_t fc = floor((xf-(float)dc)*10000.0);
                    if (echo != 0){
                        SerialPrintf("%06lu.%04d",dc,fc);
                        Serial.print(F(" "));
                    }
                }
                channel[cn]=0UL;
                if (cn==NUMBER_OF_CHANNELS-1)
                {
                    if (start_flag)
                    {
                        start_flag = false;
                    }
                    else {
                        if (data_file){
                            data_file.seek(data_file.size());
                            data_file.write(record,30);
                            data_file.flush();
                        }
                    }
                    if (echo != 0){
                        Serial.print(F("\n\r\n\r"));
                    }
                }
                n=0;
            }
        }
        read_counter_register = false;
    }
    if (download_flag){
        download_record();
    }
}