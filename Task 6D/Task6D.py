from arduino_iot_cloud import ArduinoCloudClient
from datetime import datetime

import os
import pandas as pd
from dash import Dash, html, dash_table, dcc, callback, Output, Input,no_update
import plotly.express as px
import threading
import types
import time
import cv2
import base64

#global lock to ensure shared resources cannot be accessed simultaneously
data_lock = threading.Lock()


class ArduinoCloud:
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
        self.arduino_client = ArduinoCloudClient(device_id=self.device_id,username=self.device_id ,password=self.key,sync_mode=True)
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

    def get_callback_functions(self):
        return self.callback_functions

    def run_client(self):
       self.arduino_client.start()
       #loop to synchronise with the arduino cloud queue as per synchronous mode documentation
       while True:
           self.arduino_client.update()
           time.sleep(0.1)

def draw_data(cloud_variable_list:list,graph_refresh_interval:int,graph_title:str,data_store:str,sensor_data_name:str,sequence_number=0):
    app = Dash()

    #block until data_store has been created
    while not os.path.isfile(data_store):
        time.sleep(1)

    # Initial load
    with data_lock:
        df = pd.read_csv(data_store)
        os.makedirs('captured_data',exist_ok=True)
    camera = cv2.VideoCapture(0)

    app.layout = [
        html.Div(children=graph_title, style={"textAlign":"center"}),
        html.Hr(),

        dcc.RadioItems(
            options=cloud_variable_list,
            inline=True,
            value=cloud_variable_list[0],
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
        html.H3(
    "Activity Image",
    style={"textAlign": "center"}
        ),

        html.Img(
        id='activity-image',
        style={
            "display": "block",
            "margin": "auto",
            "width": "600px",
            "maxWidth": "100%"
            }
        ),

        html.Div(
        id='capture-status',
        style={"textAlign": "center"}
        ),

        dash_table.DataTable(
            id='accelerometer-table',
            data=df.to_dict('records'),
            page_size=6
        ),
        dcc.Interval(
        id='auto-refresh',
        interval=graph_refresh_interval,  # milliseconds
        n_intervals=0
)
    ]

    # Only reload the CSV when Refresh is clicked
    @callback(
        Output('accelerometer-data', 'data'),
        Output('activity-image', 'src'),
        Output('capture-status', 'children'),

        Input('refresh', 'n_clicks'),
        Input('auto-refresh', 'n_intervals'),

        prevent_initial_call=True
    )

    def reload_data(n_clicks,n_intervals):
        nonlocal sequence_number
        for _ in range(3):
            camera.grab()
        res,frame = camera.retrieve()

        if not res:
            return (no_update,no_update,"Capture Failed :(")

        print("Reloading file")
        with data_lock:

            df = pd.read_csv(data_store)

        if df.empty:
            return (no_update,no_update,"no data available yet")

        df.to_csv(f'captured_data/{sequence_number}_{datetime.now().strftime('%Y%m%d%H%M%S')}.csv')

            # Write graph to file for later analysis, using same file naming Syntax
            # Using separate graph than displayed to maintain dashboard structure

        saved_fig = px.line(
            df,
            x='TimeStamp',
            y=cloud_variable_list,
            markers=True,
            title=f'Accelerometer Data Sequence Number: {sequence_number}'
            )

        saved_fig.update_layout(
            title_x=0.5,
            xaxis_title="Time",
            yaxis_title="Acceleration",
            legend_title="Axis"
            )

        saved_fig.write_image(
            f'captured_data/{sequence_number}_{datetime.now().strftime('%Y%m%d%H%M%S')}.png',
            width=1200,
            height=700,
            scale=2
            )

        empty_df = pd.DataFrame(columns=df.columns)
        empty_df.to_csv(data_store,index=False)

        cv2.imwrite(f'captured_data/{sequence_number}_{datetime.now().strftime('%Y//%m//%d//%H//%M//%S')}.jpg',frame)

        res,encoded_image = cv2.imencode(".jpg",frame)

        encoded_string = base64.b64encode(encoded_image).decode("utf-8")

        image_src = ("data:image/jpeg;base64,"+ encoded_string)
        status = (f"Captured window {sequence_number}:" f'{sequence_number}_{datetime.now().strftime('%Y%m%d%H%M%S')}.csv')

        sequence_number+=1

        return (df.to_dict('records'),image_src,status)


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
            markers=True,
            title=f' Graph of {sensor_data_name} - {col_chosen}'
        )

        fig.update_layout(title_x=0.5)

        return fig


    # Update table only when stored data changes
    @callback(
        Output('accelerometer-table', 'data'),
        Input('accelerometer-data', 'data')
    )
    def update_table(stored_data):

        return stored_data
    app.run()

class GenericCloudObject:
    def __init__(self):
        pass

def cloud_streaming_graph(cloud_credentials_file:str,cloud_variables: list,write_combined=False, graph_refresh_interval= 500,graph_title="Default Graph of Data from Arduino Cloud",data_store='combined.csv',sensor_data_name='accelerometer'):

    generic_cloud_object = GenericCloudObject()

    def make_getter(variable_name):
        def getter(self):
            return getattr(self,variable_name)
        return getter

    def make_setter(variable_name):
        def setter(self,value):
            setattr(self,variable_name,value)
            setattr(self,f'received_{variable_name}',True)
        return setter

    def make_serialiser(variable_name,write_combined=False):
        if write_combined:
            def combined_serialise(self,variable_list):
                with data_lock:
                    if os.path.isfile(data_store):
                        #loop checks if all the received object flags are true
                        for variable_name in variable_list:
                            if getattr(generic_cloud_object,f'received_{variable_name}') is not True:
                                return
                        with open(data_store,'a+') as file:
                            file.write(f'{datetime.now().isoformat()}')
                            for variable_name in variable_list:
                                file.write(f',{getattr(generic_cloud_object,f'get_{variable_name}')()}')
                            file.write('\n')

                        for variable_name in variable_list:
                            setattr(generic_cloud_object,f'received_{variable_name}',False)

                    # Create the combined CSV with headers only.
                    # The first complete sample is intentionally discarded
                    # to avoid recording transient/junk startup data.
                    else:
                        with open(data_store,'w') as file:
                            file.write(f'TimeStamp')
                            for variable_name in variable_list:
                                file.write(f',{variable_name}')
                            file.write('\n')
            return combined_serialise

        def serialise(self):
            with data_lock:
                if os.path.isfile(f'{variable_name}.csv'):
                    with open(f'{variable_name}.csv','a+') as file:
                        file.write(f'{datetime.now().isoformat()},{getattr(generic_cloud_object,f'get_{variable_name}')()}\n')
                else:
                    with open(f'{variable_name}.csv','w') as file:
                        file.write(f'TimeStamp,{variable_name}\n')
                        file.write(f'{datetime.now().isoformat()},{getattr(generic_cloud_object,f'get_{variable_name}')()}\n')
        return serialise


    def create_callback_function(cloud_variable_name: str,combined_write=False):
        def callback_function(client, value):
            print(f"New {cloud_variable_name} value: {value}")
            set_new_value_func = getattr(generic_cloud_object,f'set_{cloud_variable_name}')
            set_new_value_func(value)
            save_func = getattr(generic_cloud_object,f'save_{cloud_variable_name}')
            save_func()
            if combined_write is True:
                make_serialiser(None,True)(self=None,variable_list=cloud_variables)

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
        getter_method = make_getter(cloud_variable)

        setattr(generic_cloud_object,getter_method_name,types.MethodType(getter_method,generic_cloud_object))

        setter_method_name = f'set_{cloud_variable}'
        setter_method = make_setter(cloud_variable)

        setattr(generic_cloud_object,setter_method_name,types.MethodType(setter_method,generic_cloud_object))

        serialiser_method_name = f'save_{cloud_variable}'
        serialiser_method = make_serialiser(cloud_variable)

        setattr(generic_cloud_object,serialiser_method_name,types.MethodType(serialiser_method,generic_cloud_object))

    DEVICE_ID = ""
    SECRET_KEY = ""

    with open(cloud_credentials_file,"r") as fp:
        keys = []
        for line in fp:
            keys.append(line)
        DEVICE_ID = keys[0].strip('\n')
        SECRET_KEY = keys[1].strip('\n')


    client = ArduinoCloud(DEVICE_ID,SECRET_KEY)
    client.setup_client()


    # sets up the cloud variables and injects them into the generic object
    # creates callback functions to pass back the data from the arduino cloud based on the list of cloud
    # variable names given these functions are stored in the ArduinoCloud object
    for variable in cloud_variables:
       create_cloud_variable(variable)
       func_ptr = create_callback_function(variable,write_combined)
       client.add_callback_function(func_ptr)


    # Registers the created callback functions
    client.register_callbacks(cloud_variables)

    plot = threading.Thread(target=draw_data,args=(cloud_variables,graph_refresh_interval,graph_title,data_store,sensor_data_name))

    plot.start()

    client.run_client()


if __name__ == "__main__":
    cloud_streaming_graph('key.txt',['accel_x','accel_y','accel_z'],write_combined=True,graph_refresh_interval= 10_000)

