import pandas as pd
import matplotlib.pyplot as plt
#load in sensor data as a dataframe

RELATIVE_HUMIDITY = 'value_1'
TEMPERATURE = 'value_2'

LUMINOSITY = 'value_1'

df = pd.read_csv("sensor_data_complete.csv")

dht11 = df[df["Sensor"].astype(str).str.strip() =="DHT11"].copy()


#convert columns into correct data types
dht11["DateTime"] = pd.to_datetime(dht11["DateTime"],format="%H:%M:%S",errors="coerce")
luminosity = df[df["Sensor"].astype(str).str.strip() == "Luminousity"].copy()


#prepare data drop any false values that cannot be coerced

dht11[RELATIVE_HUMIDITY] = pd.to_numeric(
    dht11["value_1"],
    errors="coerce"
)

dht11[TEMPERATURE] = pd.to_numeric(
    dht11["value_2"],
    errors="coerce"
)

luminosity[LUMINOSITY] = pd.to_numeric(
    luminosity[LUMINOSITY],
    errors="coerce"
)

#luminosity[LUMINOSITY] = luminosity.dropna(subset=[LUMINOSITY])

dht11 = (dht11.dropna(subset=["DateTime",RELATIVE_HUMIDITY,TEMPERATURE]).sort_values("DateTime"))

#creating graphs

fig,humidity_axis = plt.subplots(figsize=(11,6))
fig2, histogram_axis = plt.subplots(figsize=(10, 6))

#using a second vertical axis as humidity and temperature are in different units
temperature_axis = humidity_axis.twinx()

humidity_line = humidity_axis.plot(
    dht11["DateTime"],
    dht11[RELATIVE_HUMIDITY],
    linewidth=2,
    linestyle="-",
    label="Relative Humidity"
    )

temperature_line = temperature_axis.plot(
    dht11["DateTime"],
    dht11[TEMPERATURE],
    linewidth=2,
    linestyle="-",
    label="Temperature",
    color="r"
    )

histogram_axis.hist(
    luminosity["value_1"],
    bins=15,
    edgecolor="black"
)

#Add graph labels
humidity_axis.set_title("DHT11 Sensor Data Over Time")
humidity_axis.set_xlabel("Time")
humidity_axis.set_ylabel("Relative humidity (%)")
temperature_axis.set_ylabel("Temperature (°C)")

histogram_axis.set_title("Distribution of Luminosity Readings")
histogram_axis.set_xlabel("Luminosity reading")
histogram_axis.set_ylabel("Frequency")
histogram_axis.grid(axis="y", alpha=0.3)


#Add grid lines
humidity_axis.grid(True, alpha=0.3)

#Combine both lines into one legend
lines = humidity_line + temperature_line
labels = [line.get_label() for line in lines]
humidity_axis.legend(lines, labels, loc="best")

#Format the time labels
fig.autofmt_xdate()

#Prevent labels from being cut off
fig.tight_layout()
fig2.tight_layout()

#Display the graph
plt.show()
