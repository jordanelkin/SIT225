/*SIT225-1P Sketch by Jordan Elkin*/

#include <DHT.h>

//Constants that are used 
#define PHOTOCELL_PIN A0
#define DHT11_PIN 12
#define DHT_TYPE DHT11
#define BAUD_RATE 9600
#define PIR_PIN 5
#define START_DELAY 120000 //set to 2 minutes as per the PIR spec sheet
#define SAMPLING_DELAY_RATE 30000

/*
  Specifies the photoresistor object, and supporting methods and variables that are required.
  A class was used so that the values would be encapsulated within the object and to make 
  setup easier by calling the required functions at object creation time and in the one place
  */ 
class PIR{
  public:
  PIR(int pin_number, int sampling_rate){
    this->set_pin_number(pin_number);
    this->set_sampling_rate(sampling_rate);
    arduino::pinMode(this->get_pin_number(),INPUT);
  }
  char* get_status(){return this->status;}
  
/*
    read method gets the value from the  PIR sensor, determines the status 
    and returns the value 
*/
  char* read(){
    int pin_reading = digitalRead(this->get_pin_number());
    this->set_status(pin_reading);
    return this->get_status();
  }
  bool set_sampling_rate(int sampling_rate){
    if (sampling_rate > 0){
      this->sampling_rate = sampling_rate;
      return true;
      }
    return false;
  }
  bool set_status(int status){
      if(status == LOW){
        this->status = "No Motion Detected";
      }else{
        this->status = "Motion Detected";
      }
    }
  int get_pin_number(void) {return this->pin_number;}
  void set_pin_number(int pin_number){this->pin_number = pin_number;}
  
  private:
  char* status;
  int pin_number;
  int sampling_rate;
};

/*Specifies the photoresistor object, and supporting methods and variables that are required.
  A class was used so that the values would be encapsulated within the object and to make 
  setup easier by calling the required functions at object creation time and in the one place
*/
class Photoresistor{
  public:
    Photoresistor(int pin_number, int sampling_rate){
      this->set_pin_number(pin_number);
      arduino::pinMode(this->get_pin_number(),INPUT);
      this->set_sampling_rate(sampling_rate);
      }
    bool set_pin_number(int pin_number){this->pin_number = pin_number; return true;}
    int get_pin_number(void){return this->pin_number;}
    
    int get_luminousity(void){return this->luminousity_value;}
    void set_luminousity(int luminousity_value){this->luminousity_value = luminousity_value;}
    
    int get_sampling_rate(void){return this->sampling_rate;}
    bool set_sampling_rate(int sampling_rate){
    if (sampling_rate > 0){
      this->sampling_rate = sampling_rate;
      return true;
      }
    return false;
  }
  /*read method gets the value/s from the  photoresistor, sets the new value for the luminousity 
    and returns this value*/
  int read(){
        int pin_reading = analogRead(this->get_pin_number());
        this->set_luminousity(pin_reading);
        return this->get_luminousity();
        }

  private:
    int pin_number;
    int luminousity_value;
    int sampling_rate;
};

/*variables and objects that are required for the lifetime of the program*/
DHT dht(DHT11_PIN,DHT_TYPE);
float relative_humidity;
float temperature;
int rates[] = {10,20,30};
bool startup;
Photoresistor* resistor;
PIR* pir;


void setup() {
  resistor = new Photoresistor(PHOTOCELL_PIN,10);
  pir = new PIR(PIR_PIN,10);
  Serial.begin(BAUD_RATE);
  dht.begin(); // intialises the dht object
  startup = true;
}

//main loop which conducts the reading of the sensors and sends the data over the serial port to be
// collected by the endpoint
void loop() {
  if(startup){
    delay(15);// delay for serial connection
    Serial.println("Setup in progress please wait approx 2 mins");
    startup = false;
    delay(START_DELAY);
  }
  int luminousity = resistor->read();
  Serial.println(String("Luminousity") + "," + String(luminousity));
  relative_humidity = dht.readHumidity();
  temperature = dht.readTemperature();
  Serial.println(String("DHT11") +"," + String(relative_humidity) +","+ String(temperature));
  char* status = pir->read();

  Serial.println(String("PIR") + "," + String(status));
  delay(SAMPLING_DELAY_RATE);

}
