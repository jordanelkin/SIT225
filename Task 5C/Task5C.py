import sys
import traceback
import random
from arduino_iot_cloud import ArduinoCloudClient
import asyncio
from datetime import datetime

import os
import pandas as pd
from dash import Dash, html, dash_table, dcc, callback, Output, Input,ctx,State
import plotly.express as px
import threading
import types


#class to handle handle and store data from accelerometers
#Capable of writing either all data or parts to a csv file
class Accelerometer:
    def __init__(self,write_combined=False,write_combined_file_path=None):
        self.y_value = 0.0
        self.x_value = 0.0
        self.z_value = 0.0
        self.write_combined = write_combined
        self.write_combined_file_path = write_combined_file_path

        self.received_y_value = False
        self.received_x_value = False
        self.received_z_value = False

    def get_x_value(self):
        return self.x_value

    def set_x_value(self,x):
        self.x_value = x
        self.received_x_value = True

        if self.write_combined:
            self.save_combined()

    def get_y_value(self):
        return self.y_value

    def set_y_value(self,y):
        self.y_value = y
        self.received_y_value = True

        if self.write_combined:
            self.save_combined()

    def get_z_value(self):
        return self.z_value

    def set_z_value(self,z):
        self.z_value = z
        self.received_z_value = True

        if self.write_combined:
            self.save_combined()

    def save_value(self,path,value,time,value_name):
        if os.path.isfile(path):
            with open(path,'a+') as file:
                file.write(f'{time},{value}\n')
        else:
            with open(path,'w') as file:
                file.write(f'TimeStamp,{value_name}\n')
                file.write(f'{time},{value}\n')


    def save_combined(self):
        if not os.path.isfile(self.write_combined_file_path):
            with open(self.write_combined_file_path,'w') as file:
                file.write(f"TimeStamp, X Value, Y Value, Z Value\n")

        if self.received_x_value and self.received_y_value and self.received_z_value:
            with open(self.write_combined_file_path,'a+') as file:
                file.write(f"{datetime.now().isoformat()},{self.x_value},{self.y_value},{self.z_value}\n")

            self.received_x_value = False
            self.received_y_value = False
            self.received_z_value = False

    def draw(self):
        pass


class ArdinoCloud:
    def __init__(self,device_id,key):
        self.device_id = device_id
        self.key = key
        self.arduino_client = None
        self.callback_functions = dict()

    def get_device_id(self):
        return self.device_id

    def get_key(self):
        return self.key

    def setup_client(self):
        self.arduino_client = ArduinoCloudClient(device_id=self.device_id,username=self.device_id ,password=self.key)
        print(self.arduino_client)

    def register_callbacks(self, variable_names = []):
        i = 0
        for function in self.callback_functions:
            print(f'Registered: {function} for {variable_names[i]} variable')
            self.arduino_client.register(variable_names[i], value=None,on_write=self.callback_functions[function])
            i += 1

    def add_callback_function(self, func_ptr):
        if func_ptr.__name__ not in self.callback_functions.keys():
            self.callback_functions[func_ptr.__name__] = func_ptr
        else:
            print("Error Function Already added")

    def remove_callback_function(self):
        if name in self.callback_functions.keys():
            del self.callback_functions[name]
        else:
            print("Error no such function")

    def get_callback_functions(self):
        return self.callback_functions

    def run_client(self):
       self.arduino_client.start()

global  accelerometer_data
accelerometer_data = Accelerometer(write_combined=True,write_combined_file_path='combined.csv')


# Callback functions for on change events.
def on_x_changed(client, value):
    print(f"New x value: {value}")
    accelerometer_data.set_x_value(value)
    accelerometer_data.save_value('accel_x.csv',accelerometer_data.get_x_value(),datetime.now().isoformat(),'X Value')

def on_y_changed(client,value):
    print(f"New y value: {value}")
    accelerometer_data.set_y_value(value)
    accelerometer_data.save_value('accel_y.csv',accelerometer_data.get_y_value(),datetime.now().isoformat(),'Y Value')

def on_z_changed(client,value):
     print(f"New z value: {value}")
     accelerometer_data.set_z_value(value)
     accelerometer_data.save_value('accel_z.csv',accelerometer_data.get_z_value(),datetime.now().isoformat(),'Z Value')


def draw_accelerometer_data():
    app = Dash()

    # Initial load
    df = pd.read_csv('combined.csv')

    app.layout = [
        html.Div(children='My First App with Data, Graph, and Controls'),
        html.Hr(),

        dcc.RadioItems(
            options=[' X Value', ' Y Value', ' Z Value'],
            inline=True,
            value=' X Value',
            id='controls-and-radio-item'
        ),

        html.Button(
            'Refresh',
            id='refresh',
            n_clicks=0
        ),

        # Stores the currently loaded CSV data
        dcc.Store(
            id='accelerometer-data',
            data=df.to_dict('records')
        ),

        dcc.Graph(
            id='controls-and-graph'
        ),

        dash_table.DataTable(
            id='accelerometer-table',
            data=df.to_dict('records'),
            page_size=6
        ),
        dcc.Interval(
        id='auto-refresh',
        interval=10000,  # milliseconds
        n_intervals=0
)
    ]

    # Only reload the CSV when Refresh is clicked
    @callback(
        Output('accelerometer-data', 'data'),
        Input('refresh', 'n_clicks'),
        Input('auto-refresh','n_intervals'),
        prevent_initial_call=True
    )
    def reload_data(n_intervals,n_clicks):

        print("Reloading file")

        df = pd.read_csv('combined.csv')

        return df.to_dict('records')


    # Change graph view WITHOUT reloading the file
    @callback(
        Output('controls-and-graph', 'figure'),
        Input('controls-and-radio-item', 'value'),
        Input('accelerometer-data', 'data')
    )
    def update_graph(col_chosen, stored_data):

        df = pd.DataFrame(stored_data)

        fig = px.line(
            df,
            x='TimeStamp',
            y=col_chosen,
            markers=True
        )

        return fig


    # Update table only when stored data changes
    @callback(
        Output('accelerometer-table', 'data'),
        Input('accelerometer-data', 'data')
    )
    def update_table(stored_data):

        return stored_data


    plot = threading.Thread(target=app.run)
    plot.start()

class GenericCloudObject:
    def __init__(self):
        self.flags_names = []

def cloud_streaming_graph(cloud_credentials_file:str,cloud_variables: list,write_combined=False):

    generic_cloud_object = GenericCloudObject()

    def make_gettr(variable_name):
        def getter(self):
            return getattr(self,variable_name)
        return getter

    def make_settr(variable_name):
        def setter(self,value):
            setattr(self,variable_name,value)
            setattr(generic_cloud_object,f'received_{variable_name}',True)
        return setter

    def make_serialiser(variable_name,write_combined=False):
        if write_combined:
            def combined_serialise(self,variable_list):
                if os.path.isfile(f'combined.csv'):
                    #loop checks if all the received object flags are true
                    for variable_name in variable_list:
                        if getattr(generic_cloud_object,f'received_{variable_name}') is not True:
                            return

                    with open(f'combined.csv','a+') as file:
                        file.write(f'{datetime.now().isoformat()}')
                        for variable_name in variable_list:
                            file.write(f',{getattr(generic_cloud_object,f'get_{variable_name}')()}')
                        file.write('\n')
                else:
                    with open(f'combined.csv','w') as file:
                        file.write(f'TimeStamp')
                        for variable_name in variable_list:
                            file.write(f',{variable_name}')
                        file.write('\n')
            return combined_serialise

        def serialise(self):
            if os.path.isfile(f'{variable_name}.csv'):
                 with open(f'{variable_name}.csv','a+') as file:
                     file.write(f'{datetime.now().isoformat()},{getattr(generic_cloud_object,f'get_{variable_name}')()}\n')
            else:
                with open(f'{variable_name}.csv','w') as file:
                    file.write(f'TimeStamp,{variable_name}\n')
                    file.write(f'{datetime.now().isoformat()},{getattr(generic_cloud_object,f'get_{variable_name}')()}\n')
        return serialise

    DEVICE_ID = ""
    SECRET_KEY = ""

    with open(cloud_credentials_file,"r") as fp:
        keys = []
        for line in fp:
            keys.append(line)
        DEVICE_ID = keys[0].strip('\n')
        SECRET_KEY = keys[1].strip('\n')

    def create_callback_function(cloud_variable_name: str,combined_write=False):
        def callback_function(client, value):
            print(f"New {cloud_variable_name} value: {value}")
            set_new_value_func = getattr(generic_cloud_object,f'set_{cloud_variable_name}')
            set_new_value_func(value)
            save_func = getattr(generic_cloud_object,f'save_{cloud_variable_name}')
            save_func()
            if combined_write is True:
                combined_writer = make_serialiser(None,True)(self=None,variable_list=['accel_x','accel_y','accel_z'])

        callback_function.__name__ = f'on_change_{cloud_variable_name}'
        return callback_function

    def create_cloud_variable(cloud_variable_name):
        cloud_variable = cloud_variable_name
        cloud_variable_value = 0.0

        setattr(generic_cloud_object,cloud_variable,cloud_variable_value)

        cloud_variable_received_data_flag = f'received_{cloud_variable}'
        cloud_variable_received_data_flag_value = False

        setattr(generic_cloud_object,cloud_variable_received_data_flag,cloud_variable_received_data_flag_value)


        getter_method_name = f'get_{cloud_variable}'
        getter_method = make_gettr(cloud_variable)

        setattr(generic_cloud_object,getter_method_name,types.MethodType(getter_method,generic_cloud_object))

        setter_method_name = f'set_{cloud_variable}'
        setter_method = make_settr(cloud_variable)

        setattr(generic_cloud_object,setter_method_name,types.MethodType(setter_method,generic_cloud_object))

        serialiser_method_name = f'save_{cloud_variable}'
        serialiser_method = make_serialiser(cloud_variable)

        setattr(generic_cloud_object,serialiser_method_name,types.MethodType(serialiser_method,generic_cloud_object))



    client = ArdinoCloud(DEVICE_ID,SECRET_KEY)
    client.setup_client()


    # sets up the cloud variables and injects them into the generic object
    # creates callback functions to pass back the data from the arduino cloud based on the list of cloud
    # variable names given these functions are stored in the ArdinoCloud object
    for variable in cloud_variables:
       local_variable = create_cloud_variable(variable)
       func_ptr = create_callback_function(variable,write_combined)
       client.add_callback_function(func_ptr)


    # Registers the created callback functions
    client.register_callbacks(cloud_variables)

    #draw_accelerometer_data() #transform for api usage

    client.run_client()


if __name__ == "__main__":
    cloud_streaming_graph('key.txt',['accel_x','accel_y','accel_z'],write_combined=True)
