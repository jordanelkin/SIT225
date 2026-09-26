"""
    Requirement: arduino_iot_cloud
    Install: pip install arduino-iot-cloud

    @Ahsan Habib
    School of IT, Deakin University, Australia.
"""

import sys
import traceback
import random
from arduino_iot_cloud import ArduinoCloudClient
import asyncio

# Callback function on temperature change event.
# 
def on_temperature_changed(client, value):
    print(f"New temperature: {value}")


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

    # Register with 'temperature' cloud variable
    # and listen on its value changes in 'on_temperature_changed'
    # callback function.
    # 
    client.register(
        "temperature", value=None, 
        on_write=on_temperature_changed)

    # start cloud client
    client.start()


if __name__ == "__main__":
    try:
        main()  # main function which runs in an internal infinite loop
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_tb(exc_type, file=print)
