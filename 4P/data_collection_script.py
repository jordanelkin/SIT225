import csv
import time
from datetime import datetime

import serial

BAUD_RATE = 9600
SERIAL_PORT = "/dev/ttyACM0"
COLLECTION_MINUTES = 30
OUTPUT_FILE = "raw_sensor_data.csv"


def parse_data_line(line):
    """Parse DATA,humidity,temperature,pir,light from the Arduino."""
    parts = line.split(",")

    if len(parts) != 5 or parts[0] != "DATA":
        return None

    try:
        humidity = float(parts[1])
        temperature = float(parts[2])
        pir = int(parts[3])
        light = int(parts[4])
    except ValueError:
        return None

    return humidity, temperature, pir, light


def main():
    print(f"Opening serial port {SERIAL_PORT} at {BAUD_RATE} baud...")
    print("The 30-minute collection timer starts only after the first valid sensor row.")

    with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=5) as sensor_serial, \
            open(OUTPUT_FILE, "w", newline="") as data_file:

        writer = csv.writer(data_file)
        writer.writerow([
            "DateTime",
            "Humidity",
            "Temperature",
            "PIR",
            "Light"
        ])

        start_time = None
        valid_rows = 0
        malformed_rows = 0

        while True:
            raw_line = sensor_serial.readline().decode("utf-8", errors="replace").strip()

            if not raw_line:
                continue

            # Arduino status messages are useful on-screen but are not sensor rows.
            if raw_line.startswith("STATUS"):
                print(raw_line)
                continue

            parsed = parse_data_line(raw_line)

            if parsed is None:
                malformed_rows += 1
                print(f"Ignored malformed row: {raw_line}")
                continue

            # Start timing only once real sensor data is arriving. This prevents the
            # two-minute PIR warm-up from reducing the actual collection duration.
            if start_time is None:
                start_time = time.monotonic()
                collection_started = datetime.now()
                print(f"Collection started: {collection_started.isoformat(timespec='seconds')}")

            humidity, temperature, pir, light = parsed
            timestamp = datetime.now().isoformat(timespec="seconds")

            writer.writerow([
                timestamp,
                humidity,
                temperature,
                pir,
                light
            ])
            data_file.flush()  # protect already-collected data if the program is interrupted

            valid_rows += 1
            print(
                f"{timestamp} | RH={humidity:.1f}% | Temp={temperature:.1f}C | "
                f"PIR={pir} | Light={light}"
            )

            elapsed = time.monotonic() - start_time
            if elapsed >= COLLECTION_MINUTES * 60:
                break

    collection_finished = datetime.now()
    print(f"Collection finished: {collection_finished.isoformat(timespec='seconds')}")
    print(f"Valid observations written: {valid_rows}")
    print(f"Malformed observations ignored: {malformed_rows}")
    print(f"Raw data saved to: {OUTPUT_FILE}")
    print("Complete session_log.csv using the actual bathroom-use session times before analysis.")


if __name__ == "__main__":
    main()
