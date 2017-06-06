unsigned int frequency = 1;       // Hz
unsigned long t;
boolean microsec;

void setup() {
  // initialize digital pin 13 as an output.
  pinMode(13, OUTPUT);
  if(frequency>2000){
      t = 500000/frequency;
      microsec = true;
  }
  else{
      t = 500/frequency;
      microsec = false;
  }
}


void loop() {
  digitalWrite(13, HIGH);   
  
  if(microsec)
     delayMicroseconds(t);
  else
     delay(t);
  digitalWrite(13, LOW);    
  if(microsec)
     delayMicroseconds(t);
  else
     delay(t);
              
}
