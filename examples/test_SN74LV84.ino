int gal_pin = 14;                // select byte 1
int gau_pin = 15;                // select byte 2
int gbl_pin = 16;
int gbu_pin = 17;
int rclk_pin = 13;               // simulate clock to save into counter register

byte bit_value;
unsigned long current_count = 0;
byte byte_value = 0;


void setup() {
  Serial.begin(57600);
  pinMode(gal_pin, OUTPUT);
  pinMode(gau_pin, OUTPUT);
  pinMode(gbl_pin, OUTPUT);
  pinMode(gbu_pin, OUTPUT);
  
  pinMode(rclk_pin, OUTPUT);
  
}

void loop() {
  current_count = 0;
  // read bytes
  digitalWrite(rclk_pin, HIGH);
  for(byte i=4;i>=1;i--){
      byte_value = read_byte(i);
      
      current_count += byte_value * pow(2,8 *(i-1));
    }
  Serial.print(" . ");
  Serial.println(current_count);
  digitalWrite(rclk_pin, LOW);
  delay(1000);
  
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
    byte_count = 0;
    for(int i=9;i>=2;i--){
        bit_value = digitalRead(i);
        byte_count += bit_value << (i-2);
        Serial.print(bit_value);
    }
    Serial.print("|");
    digitalWrite(gal_pin, HIGH);
    digitalWrite(gau_pin, HIGH);
    digitalWrite(gbl_pin, HIGH);
    digitalWrite(gbu_pin, HIGH);
   
    delayMicroseconds(1);
    return byte_count;
}
