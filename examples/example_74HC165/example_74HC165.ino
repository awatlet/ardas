/* 74HC165 */
int pl_pin = 8;  // Connects to Parallel load pin the 165
int ce_pin = 9;  // Connects to Clock Enable pin the 165
int q7_pin = 11; // Connects to the Q7 pin the 165
int cp_pin = 12; // Connects to the Clock pin the 165



unsigned int read_shift_register(){
  
  long  bitVal;
  int bytesVal = 0;
  
  digitalWrite(ce_pin, HIGH);
  digitalWrite(pl_pin, LOW);
  delayMicroseconds(1000);
  digitalWrite(pl_pin, HIGH);
  digitalWrite(ce_pin, LOW);
  
  for(int i =0; i < 8; i++){
    bitVal  = digitalRead(q7_pin);
    bytesVal |= (bitVal << ((8-1) - i));
    digitalWrite(cp_pin, HIGH);
    delayMicroseconds(1000);
    digitalWrite(cp_pin, LOW);
  }
  
  return(bytesVal);
}


void setup()
{
    Serial.begin(57600);

    /* Initialize our digital pins...
    */
    pinMode(pl_pin, OUTPUT);
    pinMode(ce_pin, OUTPUT);
    pinMode(cp_pin, OUTPUT);
    pinMode(q7_pin, INPUT);

    digitalWrite(cp_pin, LOW);
    digitalWrite(pl_pin, HIGH);

}

void loop()
{
   
    unsigned int pinValues = read_shift_register();
    Serial.println(pinValues);

    delay(1000);
}

