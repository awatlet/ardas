#include <Wire.h>
#include <RTClib.h>

RTC_DS1307 RTC;

boolean DEBUG = false;

// Don't forget to connect I2C pins A4 and A5 (5 and 6 of RTC)

/* RTC */
int rtc_pulse_pin = 2;  
// counter
int gal_pin = 14;                // select byte 1
int gau_pin = 15;                // select byte 2
int gbl_pin = 16;                // select byte 3
int gbu_pin = 17;                // select byte 4
int rclk_pin = 13;               // set selected byte to output
// shift register
int pl_pin = 4;                // latch pin
int cp_pin = 3;                // clock for synchronous communcation
int q7_pin = 12;                // serial output
int ce_pin = 11;                // activation cp clock

//others
volatile unsigned int pulse_counter = 0;
volatile boolean read_counter_register = 0;
float channel1 = 0;
unsigned long previous_count = 0;
unsigned long current_count = 0;
unsigned long current_count2 = 0;
byte counter_register = 0;
byte byte_value = 0;
unsigned int sampling_rate = 2;



void setup()
{
  Serial.begin(57600);
   Wire.begin();
   RTC.begin();
   RTC.adjust(DateTime(__DATE__, __TIME__));
   
   RTC.setSqwOutSignal(RTC_DS1307::Frequency_1Hz);
  
  pinMode(gal_pin, OUTPUT);
  pinMode(gau_pin, OUTPUT);
  pinMode(gbl_pin, OUTPUT);
  pinMode(gbu_pin, OUTPUT);
  pinMode(rclk_pin, OUTPUT);
  pinMode(pl_pin, OUTPUT);
  pinMode(cp_pin, OUTPUT);
  pinMode(ce_pin, OUTPUT);
  
  digitalWrite(gal_pin, LOW);
  digitalWrite(gau_pin, LOW);
  digitalWrite(gbl_pin, LOW);
  digitalWrite(gbu_pin, LOW);
  digitalWrite(rclk_pin, LOW);
  digitalWrite(pl_pin, HIGH);
  digitalWrite(cp_pin, LOW);
  digitalWrite(ce_pin, HIGH);

  attachInterrupt(0, rtc_interrupt, RISING);
  
}

void loop()
{
  if(read_counter_register){
    if(DEBUG)
        Serial.println("BEGINS...");
    // read time on RTC
    previous_count  =  current_count;
    current_count = 0;
    if(DEBUG){
        Serial.print("Previous count: ");
        Serial.println(previous_count);
        Serial.print("Current count ");
        Serial.println(current_count);
    }
  
    // read bytes
    for(byte i=4;i>=1;i--){
 
      byte_value = read_byte(i);
      if(DEBUG){
          Serial.print(" | ");
          Serial.print(byte_value);
          Serial.print(" | ");
      }
      //current_count2 += byte_value << (8*(i-1));
      current_count += byte_value * pow(2,8 *(i-1));
    }
    if(DEBUG)
        Serial.println(" . ");
    if (current_count != 0 && previous_count != 0){
      
      if(current_count >= previous_count)
          channel1 = float(current_count - previous_count)/sampling_rate;
  //    else if (current_count == 0)
  //        Serial.println("current count equals 0");
      else{
          Serial.print("$");
          channel1 = float((2147483648 - previous_count) + current_count) / sampling_rate;
          //channel1 = float((65536- previous_count) + current_count) / (2 * sampling_rate);

    }
  //    Serial.print("Current count : ");
      if(DEBUG){
      Serial.print("New current count: ");
      Serial.println(current_count);
      //Serial.println(current_count2);
      Serial.print(" : ");
      
      }
      Serial.print(channel1);
      Serial.println("Hz");
      read_counter_register = 0;
      
    }
    if(DEBUG){
        Serial.println("ENDS");
    }
  }
  
  //Serial.println(pulse_counter);
 
  
}

void rtc_interrupt()
{
  // each two seconds
  if (pulse_counter % 2 == 0){
     digitalWrite(rclk_pin, HIGH);
     digitalWrite(rclk_pin, LOW);
     
     read_counter_register = 1;
       
     }
  pulse_counter ++;
          
}

byte read_byte(byte byte_number) {
    byte byte_count;
    boolean gal_level;
    boolean gau_level;
    boolean gbl_level;
    boolean gbu_level;
    unsigned int wait_time = 50;


    switch(byte_number){
        case 1: 
            gal_level = LOW;
            gau_level = HIGH;
            gbl_level = HIGH;
            gbu_level = HIGH;
            break;
        case 2: 
            gal_level = HIGH;
            gau_level = LOW;
            gbl_level = HIGH;
            gbu_level = HIGH;
            break;
         case 3: 
            gal_level = HIGH;
            gau_level = HIGH;
            gbl_level = LOW;
            gbu_level = HIGH;
            break;
          case 4: 
            gal_level = HIGH;
            gau_level = HIGH;
            gbl_level = HIGH;
            gbu_level = LOW;
            break;   
    }
    digitalWrite(gal_pin, gal_level);
    digitalWrite(gau_pin, gau_level);
    digitalWrite(gbl_pin, gbl_level);
    digitalWrite(gbu_pin, gbu_level);
    delayMicroseconds(wait_time);
    digitalWrite(pl_pin, LOW);
    delayMicroseconds(wait_time);
    digitalWrite(pl_pin, HIGH);
    delayMicroseconds(wait_time);
    digitalWrite(ce_pin, LOW);
    byte_count = 0;
    for(int i=7;i>=0;i--){
       digitalWrite(cp_pin, LOW);
       counter_register = digitalRead(q7_pin);
       if(DEBUG){
           Serial.print(" ");
           Serial.print(counter_register);
       }
       byte_count += counter_register << i;
       delayMicroseconds(wait_time);
       digitalWrite(cp_pin, HIGH);
       delayMicroseconds(wait_time);
    }
    digitalWrite(ce_pin, HIGH);
    digitalWrite(gal_pin, HIGH);
    digitalWrite(gau_pin, HIGH);
    digitalWrite(gbl_pin, HIGH);
    digitalWrite(gbu_pin, HIGH);
    delayMicroseconds(1);
    return byte_count;
}
