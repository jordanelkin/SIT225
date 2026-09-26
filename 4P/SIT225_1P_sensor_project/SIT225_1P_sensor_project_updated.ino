/* SIT225-1P Sketch by Jordan Elkin
   Updated for Task 4 protocol execution.

   Serial output format:
   DATA,humidity,temperature,pir,light

   PIR is monitored continuously between 5-second observations. If motion is
   detected at any point during the interval, PIR is recorded as 1.
*/

#include <DHT.h>

// Hardware constants
#define PHOTOCELL_PIN A0
#define DHT11_PIN 12
#define DHT_TYPE DHT11
#define BAUD_RATE 9600
#define PIR_PIN 5

// PIR warm-up and sampling settings
#define START_DELAY 120000UL       // 2 minute PIR warm-up
#define SAMPLE_INTERVAL 5000UL     // one combined observation every 5 seconds
#define PIR_POLL_INTERVAL 50UL     // check PIR frequently so brief motion is not missed

class PIR {
  public:
    PIR(int pin_number, int sampling_rate) {
      this->set_pin_number(pin_number);
      this->set_sampling_rate(sampling_rate);
      pinMode(this->get_pin_number(), INPUT);
    }

    bool motion_detected() {
      return digitalRead(this->get_pin_number()) == HIGH;
    }

    bool set_sampling_rate(int sampling_rate) {
      if (sampling_rate > 0) {
        this->sampling_rate = sampling_rate;
        return true;
      }
      return false;
    }

    int get_pin_number() { return this->pin_number; }
    void set_pin_number(int pin_number) { this->pin_number = pin_number; }

  private:
    int pin_number;
    int sampling_rate;
};

class Photoresistor {
  public:
    Photoresistor(int pin_number, int sampling_rate) {
      this->set_pin_number(pin_number);
      pinMode(this->get_pin_number(), INPUT);
      this->set_sampling_rate(sampling_rate);
    }

    bool set_pin_number(int pin_number) {
      this->pin_number = pin_number;
      return true;
    }

    int get_pin_number() { return this->pin_number; }

    int get_luminosity() { return this->luminosity_value; }
    void set_luminosity(int luminosity_value) {
      this->luminosity_value = luminosity_value;
    }

    int get_sampling_rate() { return this->sampling_rate; }

    bool set_sampling_rate(int sampling_rate) {
      if (sampling_rate > 0) {
        this->sampling_rate = sampling_rate;
        return true;
      }
      return false;
    }

    int read() {
      int pin_reading = analogRead(this->get_pin_number());
      this->set_luminosity(pin_reading);
      return this->get_luminosity();
    }

  private:
    int pin_number;
    int luminosity_value;
    int sampling_rate;
};

DHT dht(DHT11_PIN, DHT_TYPE);
Photoresistor* resistor;
PIR* pir;

bool startup = true;
bool motion_seen = false;
unsigned long last_sample_time = 0;
unsigned long last_pir_poll = 0;

void setup() {
  resistor = new Photoresistor(PHOTOCELL_PIN, SAMPLE_INTERVAL);
  pir = new PIR(PIR_PIN, PIR_POLL_INTERVAL);

  Serial.begin(BAUD_RATE);
  dht.begin();
}

void loop() {
  if (startup) {
    delay(15);
    Serial.println("STATUS,PIR warm-up started");
    delay(START_DELAY);
    Serial.println("STATUS,READY");

    startup = false;
    last_sample_time = millis() - SAMPLE_INTERVAL; // allow first observation immediately
    last_pir_poll = millis();
  }

  unsigned long current_time = millis();

  // Poll PIR frequently and remember any motion until the next combined sample.
  if (current_time - last_pir_poll >= PIR_POLL_INTERVAL) {
    if (pir->motion_detected()) {
      motion_seen = true;
    }
    last_pir_poll = current_time;
  }

  // Send one synchronized observation every 5 seconds.
  if (current_time - last_sample_time >= SAMPLE_INTERVAL) {
    float relative_humidity = dht.readHumidity();
    float temperature = dht.readTemperature();
    int luminosity = resistor->read();
    int pir_value = motion_seen ? 1 : 0;

    Serial.print("DATA,");
    Serial.print(relative_humidity);
    Serial.print(",");
    Serial.print(temperature);
    Serial.print(",");
    Serial.print(pir_value);
    Serial.print(",");
    Serial.println(luminosity);

    motion_seen = false;
    last_sample_time = current_time;
  }
}
