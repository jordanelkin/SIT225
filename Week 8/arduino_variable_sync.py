import sys
import traceback
import random
from arduino_iot_cloud import ArduinoCloudClient
import asyncio
from datetime import datetime
import time

accel_x, accel_y,accel_z = 0.0,0.0,0.0

rec_accel_x = False
rec_accel_y = False
rec_accel_z = False


# Callback function on change events.

def on_x_changed(client, value):
    global accel_x
    accel_x = value
    global rec_accel_x
    accel_x_csv = open("accel_x.csv",'a+')
    print(f"New x value: {value}")
    accel_x_csv.write(f"{datetime.now().strftime("%H:%M:%S")},{value}\n")
    accel_x_csv.close()
    rec_accel_x = True
    save_combined()

def on_y_changed(client,value):
    global accel_y
    accel_y = value
    global rec_accel_y
    accel_y_csv = open("accel_y.csv",'a+')
    print(f"New y value: {value}")
    accel_y_csv.write(f"{datetime.now().strftime("%H:%M:%S")},{value}\n")
    accel_y_csv.close()
    rec_accel_y = True
    save_combined()

def on_z_changed(client,value):
     global accel_z
     global rec_accel_z
     accel_z = value
     accel_z_csv = open("accel_z.csv",'a+')
     print(f"New z value: {value}")
     accel_z_csv.write(f"{datetime.now().strftime("%H:%M:%S")},{value}\n")
     accel_z_csv.close()
     rec_accel_z = True
     save_combined()


def save_combined():
    global rec_accel_x, rec_accel_y, rec_accel_z
    if rec_accel_x and rec_accel_y and rec_accel_z:
        acceleration_combined = open("combined.csv",'a+')
        acceleration_combined.write(f"{datetime.now().strftime("%H:%M:%S")},{accel_x},{accel_y},{accel_z}\n")
        acceleration_combined.close()
        rec_accel_x = False
        rec_accel_y = False
        rec_accel_z = False
    else:
        return

def main():

    DEVICE_ID = ""
    SECRET_KEY = ""

    fp = open("key.txt","r")


    keys = []

    for line in fp:
        keys.append(line)

    DEVICE_ID = keys[0].strip('\n')
    SECRET_KEY = keys[1].strip('\n')

    print(keys)


    print("main() function")

    # Instantiate Arduino cloud client
    client = ArduinoCloudClient(
        device_id=DEVICE_ID, username=DEVICE_ID, password=SECRET_KEY
    )

## callback function registrations
    client.register(
        "accel_x", value=None,
        on_write=on_x_changed)

    client.register(
        "accel_y", value=None,
        on_write=on_y_changed)

    client.register(
        "accel_z", value=None,
        on_write=on_z_changed)

    # start cloud client
    client.start()


if __name__ == "__main__":
    try:
        main()  # main function which runs in an internal infinite loop
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_tb(exc_type, file=print)
