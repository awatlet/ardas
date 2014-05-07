#include <EEPROM.h>
//#include <Time.h>
#include <SD.h>

String VERSION, he, e0, e1, e2, ri, sd, rv, sr, si,ss, zr, parameter, connect_id;
char EOL;
int station, netid, integration_period, nb_inst;
int echo = 1;
int addr_station = 0;
int addr_netid = 2;
int addr_integration_period = 3;
int addr_nb_inst = 5;
File myFile;

void EEPROMWriteOnTwoBytes (int address, int value) {
	byte two = (value & 0xFF);
	byte one = ((value >> 8) & 0xFF);
	
	EEPROM.write (address, two);
	EEPROM.write (address +1, one);
}

int EEPROMReadTwoBytes (int address) {
	int two = EEPROM.read (address);
	int one = EEPROM.read (address + 1);

	return ((two << 0) & 0xFF) + ((one << 8) & 0xFFFF);
	//return ( ((two << 0) & 0xFF) + ((one << 8) & 0xFFF)));
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
	integration_period = EEPROMReadTwoBytes (addr_integration_period);
	if (integration_period == 0) {
		integration_period = 60;
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
    Serial.print (integration_period);
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
	Serial.println ("#SS : Set Station Number");
	Serial.println ("#SI nnn : Set DAS Number");
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
	Serial.println("!RI Station: " + String(station) +" DasNo: " + 
	String(netid) + " Integration: " + String(integration_period));
}

void get_version () {
	Serial.println("!RV " + VERSION);
}


void set_station_id (String s) {
	if (s.length () == 9) {
			parameter = s.substring (4, 8);
		  	station = parameter.toInt ();
		  	EEPROMWriteOnTwoBytes (addr_station, station);
		  	Serial.print ("!SS ");
		  	Serial.println (station); 	  	   
		} 
	else {
		  	Serial.print ("!SS value error");
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
			Serial.println (netid);
	}
}

void set_integration_period (String s) {
	if (s.length () == 9) {
			// TODO: check parameter type
			parameter = s.substring (4,8);
			integration_period = parameter.toInt ();
			EEPROMWriteOnTwoBytes (addr_integration_period, integration_period);
		  	Serial.print ("!SR ");
		  	Serial.println (integration_period);
		} 
	else {
		  	Serial.print("!SR ");
		  	Serial.println(integration_period);
	}
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
		integration_period = parameter3.toInt ();
		nb_inst = parameter4.toInt ();

		EEPROMWriteOnTwoBytes(addr_station, station);
		EEPROM.write (addr_netid, netid);
		EEPROMWriteOnTwoBytes (addr_integration_period, integration_period);
		EEPROM.write (addr_nb_inst, nb_inst);
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
}


void setup () {
 	VERSION = String("Version ARDAS 0.1 [2013-2014]");

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


	Serial.begin (9600);     // opens serial port, sets data rate to 9600 bps
	Serial.flush ();

        // Serial.print("Initializing SD card...");
        // pinMode(10, OUTPUT);
        
        // if (!SD.begin(4)) {
        //         Serial.println("initialization failed!");
        //          return;
        //  }
        // Serial.println("initialization done.");
        
        // myFile = SD.open("test.txt", FILE_WRITE);
        
        // if (myFile) {
        //         Serial.print("Writing to test.txt...");
        //         myFile.println("testing 1, 2, 3.");
	       //  // close the file:
        //         myFile.close();
        //         Serial.println("done.");
        // } else {
        // // if the file didn't open, print an error:
        //         Serial.println("error opening test.txt");
        // }
        
        // // re-open the file for reading:
        // myFile = SD.open("test.txt");
        // if (myFile) {
        //         Serial.println("test.txt:");
    
        //         // read from the file until there's nothing else in it:
        //         while (myFile.available()) {
    	   //              Serial.write(myFile.read());
        //         }
        //         // close the file:
        //         myFile.close();
        // } else {
  	     //    // if the file didn't open, print an error:
        //         Serial.println("error opening test.txt");
        // }
}

void loop () {
	char c;
	String s;
	String command, first_character;
	// send data only when you receive data:
	do {
		if (Serial.available () > 0) {
		// read the incoming bytes
			c = Serial.read ();
			s += c;
		}
	} 
	while (c != EOL);
	//Serial.println(s);   

    // say hi
    first_character = s.substring (0,1);
    if( first_character == "-") {
        if (s.substring (0,4)) {
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
            set_integration_period (s);
        }
        else if (command == zr) {
            reconfig (s);
        }
        else {
            Serial.println ("Unknown command\n\r");
        }
    }


}
