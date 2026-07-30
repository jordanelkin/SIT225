import serial
from datetime import datetime
import time

BAUD_RATE = 9600

s = serial.Serial('/dev/ttyACM0', BAUD_RATE, timeout=5)

data_file = open("sensor_data.csv","w")

sensor_data = dict() #main sensor data store

#initial time information for determining how long data has been collected for
start_time = time.time()

#main loop for collecting data from the arduino over serial.
while True:
    current_time = time.time()

    if(abs(start_time - current_time) >= 30 * 60):
        break

    data = s.readline()
    data = data.decode('utf-8').strip("\r\n")
    time_now = datetime.now().strftime("%H:%M:%S")

    if(data.__contains__("Luminousity")):
        print(f'Current Luminousity:')
        print(f'{datetime.now()},{data}')
        if "Luminousity" in sensor_data.keys():
            sensor_data['Luminousity'] += [f"{time_now},{data}"]
        else:
            sensor_data['Luminousity'] = [f"{time_now},{data}"]

    if(data.__contains__("DHT11")):
        print(f'Current humidty and temperature readings:')
        print(f'{datetime.now()},{data}')
        if "DHT11" in sensor_data.keys():
            sensor_data['DHT11'] += [f"{time_now},{data}"]
        else:
            sensor_data['DHT11'] = [f"{time_now},{data}"]

    if(data.__contains__("PIR")):
        print(f'PIR Sensor:')
        print(f'{datetime.now()},{data}')
        if "PIR" in sensor_data.keys():
            sensor_data['PIR'] += [f"{time_now},{data}"]
        else:
            sensor_data['PIR'] = [f"{time_now},{data}"]

#Writes data to the csv file in the specified csv format

data_file.write(f'DateTime,Sensor,value_1,value_2\n') # Headings

for key,value in sensor_data.items():
    for inner_value in value:
        data_file.write(f"{inner_value}\n")
data_file.close()

