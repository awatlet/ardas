#include <Time.h>

String E0, E1, E2, RI, SD;
char EOL;
int station, netid, integration_period, echo;

void setup() {
  E0 = String("#E0");
  E1 = String("#E1");
  E2 = String("#E2");
  RI = String("#RI");
  SD = String("#SD");
  EOL = '\r';
  station = 1;
  netid = 255;
  integration_period = 60;
  echo = 1;
  Serial.begin(9600);     // opens serial port, sets data rate to 9600 bps
  Serial.flush();
}

void loop() {
  char c;
  String s;
  String command;
  // send data only when you receive data:
  do {
    if (Serial.available() > 0) {
      // read the incoming byte:
      c = Serial.read();
      s += c;
    }
  } 
  while(c != EOL);
  //Serial.println(s);   

  command = s.substring(0,3);
  if(command == E0){ // No Echo
    Serial.println("\n\r!E0[Echo disabled]\n\r");
    echo = 0;
  }
  else if(command == E1){ //  Only Data
    Serial.println("!E1\n\r");
    echo = 1;
  }
  else if(command == E2){ //  Data + Time
    Serial.println("!E2\n\r");
    echo = 2;
  }
  else if(command == RI){ //  Data + Time

    Serial.println("!RI Station:" + String(station) +" DasNo:" + String(netid) + "Integration:" + String(integration_period));
  }
  else if(command == SD){
    //setTime(1396944974.452954);
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
  else{
    Serial.println("Unknown command\n\r");
  }

}







