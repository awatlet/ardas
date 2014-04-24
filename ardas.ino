#include <Time.h>
#include <EEPROM.h>

String VERSION, e0, e1, e2, ri, sd, rv, sr, si,ss, zr, parameter;
char EOL;
int station, netid, integration_period, nb_inst;
int echo = 1;
  
void read_config_or_set_default () {
	station = EEPROM.read (0);
	if (station == 0) {
		station = 1;
	}
	netid = EEPROM.read (1);
	if (netid == 0) {
		netid = 255;
	}
	integration_period = EEPROM.read (2);
	if (integration_period == 0) {
		integration_period = 60;
	}
	nb_inst = EEPROM.read (3);
	if ( nb_inst == 0) {
		nb_inst = 4;
	}
}

void reconfig (String s) {
	String parameter1, parameter2, parameter3, parameter4;
	parameter1 = s.substring (4, 8);
	parameter2 = s.substring (9, 12);
	parameter3 = s.substring (13, 17);
	parameter4 = s.substring (18, 19);

	station = parameter1.toInt ();
	netid = parameter2.toInt ();
	integration_period = parameter3.toInt ();
	nb_inst = parameter4.toInt ();

	EEPROM.write (0, station);
	EEPROM.write (1, station);
	EEPROM.write (2, station);
	EEPROM.write (3, station);
	delay(100);
	Serial.print ("!ZR ");
	Serial.print (station);
	Serial.print (" ");
	Serial.print (netid);
	Serial.print (" ");
	Serial.print (integration_period);
	Serial.print (" ");
	Serial.println (nb_inst);
}


void setup () {
 	VERSION = String("ARDAS 0.1");
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
	
	Serial.begin (9600);     // opens serial port, sets data rate to 9600 bps
	Serial.flush ();
}

void loop () {
	char c;
	String s;
	String command;
	// send data only when you receive data:
	do {
		if (Serial.available () > 0) {
		// read the incoming byte:
		c = Serial.read ();
		s += c;
		}
	} 
	while (c != EOL);
	//Serial.println(s);   

	command = s.substring (0,3);
	if (command == e0) { // No Echo
		Serial.println ("\n\r!E0[Echo disabled]\n\r");
		echo = 0;
	} 
	else if (command == e1) { 					//  Only Data
		Serial.println ("!E1\n\r");
		echo = 1;
	} 
	else if (command == e2) { 					//  Data + Time
		Serial.println ("!E2\n\r");
		echo = 2;
	} 
	else if (command == ri) { 					//  Read info
		Serial.println("!RI Station: " + String(station) +" DasNo: " + String(netid) + " Integration: " + String(integration_period));
	} 
	else if (command == sd) {  					// SET date
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
	else if (command == rv) {
		Serial.println("!RV " + VERSION);
	}
	else if (command == ss) {                     // SET station number
		if (s.length () == 9) {
			parameter = s.substring (4, 8);
		  	station = parameter.toInt ();
		  	EEPROM.write (0, station);
		  	Serial.print ("!SS ");
		  	Serial.println (station); 	  	   
		} 
		else {
		  	Serial.print ("!SS value error");
	    }
	}  
	else if (command == si) {  					   // SET das netid
		if(s.length () == 8) {
			// TODO: check parameter type
		  	parameter = s.substring (4,7);
		  	netid = parameter.toInt ();
		  	EEPROM.write(1, netid);
		  	Serial.print ("!SI ");
		  	Serial.println (netid);
		} 
		else { 
			Serial.print ("!SI ");
			Serial.println (netid);
		}
	} 
	else if (command == sr) {  					// SET integration period
		if (s.length () == 9) {
			// TODO: check parameter type
			parameter = s.substring (4,8);
			integration_period = parameter.toInt ();
			EEPROM.write (2, integration_period);
		  	Serial.print ("!SR ");
		  	Serial.println (integration_period);
		} 
		else {
		  	Serial.print("!SR ");
		  	Serial.println(integration_period);
		}
	} 
	else if (command == zr) {
		if (s.length () == 20) {
			reconfig (s);
		}
	}
	else {
		Serial.println ("Unknown command\n\r");
	}
}
