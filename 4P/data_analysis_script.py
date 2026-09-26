import itertools
import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, ConfusionMatrixDisplay
from sklearn.model_selection import GroupShuffleSplit
from sklearn.tree import DecisionTreeClassifier

RAW_FILE = "raw_sensor_data.csv"
SESSION_LOG_FILE = "session_log.csv"
PROCESSED_FILE = "processed_sensor_data.csv"

BASE_FEATURES = ["Humidity", "Temperature", "PIR", "Light"]
EXPECTED_STATES = ["vacant", "occupied", "shower"]


def load_and_clean_raw_data():
    df = pd.read_csv(RAW_FILE)
    initial_rows = len(df)

    required_columns = ["DateTime", "Humidity", "Temperature", "PIR", "Light"]
    missing_columns = [column for column in required_columns if column not in df.columns]
    if missing_columns:
        raise ValueError(f"Raw data is missing columns: {missing_columns}")

    df["DateTime"] = pd.to_datetime(df["DateTime"], errors="coerce")

    for column in ["Humidity", "Temperature", "PIR", "Light"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    missing_before = df[required_columns].isna().sum()
    duplicate_rows = int(df.duplicated().sum())

    df = df.drop_duplicates()
    df = df.dropna(subset=required_columns)

    # Basic physical/sensor validation. Adjust Light if the ADC resolution is changed.
    valid_range = (
        df["Humidity"].between(0, 100)
        & df["Temperature"].between(0, 50)
        & df["PIR"].isin([0, 1])
        & df["Light"].between(0, 1023)
    )

    outlier_rows = int((~valid_range).sum())
    df = df[valid_range].copy()
    df = df.sort_values("DateTime").reset_index(drop=True)

    print("\nDATA QUALITY REPORT")
    print("-------------------")
    print(f"Raw rows: {initial_rows}")
    print(f"Duplicate rows removed: {duplicate_rows}")
    print(f"Rows outside validation ranges removed: {outlier_rows}")
    print(f"Final valid rows: {len(df)}")
    print("Missing values before cleaning:")
    print(missing_before.to_string())

    return df


def add_session_labels(df):
    """Attach manually recorded ground-truth sessions to the sensor observations."""
    df["SessionID"] = pd.NA
    df["State"] = pd.NA
    df["Ventilation"] = pd.NA
    df["BaselineHumidityLogged"] = np.nan

    if not os.path.exists(SESSION_LOG_FILE):
        print(
            f"\n{SESSION_LOG_FILE} was not found. Sensor processing will continue, "
            "but hypothesis testing and classification will be skipped."
        )
        return df, None

    sessions = pd.read_csv(SESSION_LOG_FILE)

    required = ["SessionID", "State", "StartTime", "EndTime"]
    missing = [column for column in required if column not in sessions.columns]
    if missing:
        raise ValueError(f"Session log is missing columns: {missing}")

    sessions["StartTime"] = pd.to_datetime(sessions["StartTime"], errors="coerce")
    sessions["EndTime"] = pd.to_datetime(sessions["EndTime"], errors="coerce")
    sessions["State"] = sessions["State"].astype(str).str.strip().str.lower()

    if "BaselineHumidity" in sessions.columns:
        sessions["BaselineHumidity"] = pd.to_numeric(
            sessions["BaselineHumidity"], errors="coerce"
        )

    for _, session in sessions.iterrows():
        if pd.isna(session["StartTime"]) or pd.isna(session["EndTime"]):
            continue

        mask = df["DateTime"].between(session["StartTime"], session["EndTime"])
        df.loc[mask, "SessionID"] = session["SessionID"]
        df.loc[mask, "State"] = session["State"]

        if "Ventilation" in sessions.columns:
            df.loc[mask, "Ventilation"] = session["Ventilation"]

        if "BaselineHumidity" in sessions.columns and pd.notna(session["BaselineHumidity"]):
            df.loc[mask, "BaselineHumidityLogged"] = session["BaselineHumidity"]

    labelled = int(df["SessionID"].notna().sum())
    print(f"\nGround-truth labelled rows: {labelled}/{len(df)}")

    unlabelled = len(df) - labelled
    if unlabelled:
        print(
            f"Warning: {unlabelled} rows do not fall inside a session-log time range. "
            "They remain in the processed CSV but are excluded from labelled analyses."
        )

    return df, sessions


def add_temporal_features(df):
    df = df.copy()
    df["ElapsedSeconds"] = (df["DateTime"] - df["DateTime"].min()).dt.total_seconds()

    df["HumidityDelta"] = np.nan
    df["HumidityRatePerMin"] = np.nan
    df["RecentPIR"] = np.nan
    df["LightChange"] = np.nan

    labelled_mask = df["SessionID"].notna()

    if labelled_mask.any():
        for session_id, index in df[labelled_mask].groupby("SessionID").groups.items():
            session = df.loc[index].sort_values("DateTime")
            baseline = session["BaselineHumidityLogged"].dropna()
            baseline_humidity = (
                baseline.iloc[0] if not baseline.empty else session["Humidity"].iloc[0]
            )

            seconds = (session["DateTime"] - session["DateTime"].iloc[0]).dt.total_seconds()
            minutes = seconds / 60.0

            humidity_delta = session["Humidity"] - baseline_humidity
            humidity_rate = humidity_delta / minutes.replace(0, np.nan)

            df.loc[session.index, "HumidityDelta"] = humidity_delta.values
            df.loc[session.index, "HumidityRatePerMin"] = humidity_rate.fillna(0).values
            df.loc[session.index, "RecentPIR"] = (
                session["PIR"].rolling(window=6, min_periods=1).max().values
            )
            df.loc[session.index, "LightChange"] = session["Light"].diff().fillna(0).values
    else:
        df["HumidityDelta"] = df["Humidity"] - df["Humidity"].iloc[0]
        elapsed_minutes = df["ElapsedSeconds"] / 60.0
        df["HumidityRatePerMin"] = (
            df["HumidityDelta"] / elapsed_minutes.replace(0, np.nan)
        ).fillna(0)
        df["RecentPIR"] = df["PIR"].rolling(window=6, min_periods=1).max()
        df["LightChange"] = df["Light"].diff().fillna(0)

    return df


def print_descriptive_statistics(df):
    print("\nDESCRIPTIVE STATISTICS")
    print("----------------------")
    stats_table = df[BASE_FEATURES].describe(percentiles=[0.25, 0.50, 0.75, 0.95])
    print(stats_table.to_string())

    print("\nCorrelation matrix:")
    print(df[BASE_FEATURES].corr().to_string())


def make_basic_plots(df):
    # Plot 1: humidity and temperature over time
    fig, humidity_axis = plt.subplots(figsize=(11, 6))
    temperature_axis = humidity_axis.twinx()

    humidity_line = humidity_axis.plot(
        df["DateTime"], df["Humidity"], linewidth=2, label="Relative Humidity"
    )
    temperature_line = temperature_axis.plot(
        df["DateTime"], df["Temperature"], linewidth=2, linestyle="--", label="Temperature"
    )

    humidity_axis.set_title("Temperature and Relative Humidity Over Time")
    humidity_axis.set_xlabel("Time")
    humidity_axis.set_ylabel("Relative Humidity (%)")
    temperature_axis.set_ylabel("Temperature (°C)")
    humidity_axis.grid(True, alpha=0.3)

    lines = humidity_line + temperature_line
    labels = [line.get_label() for line in lines]
    humidity_axis.legend(lines, labels, loc="best")
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig("plot_1_environment_over_time.png", dpi=200)

    # Plot 2: light distribution
    fig2, axis2 = plt.subplots(figsize=(10, 6))
    axis2.hist(df["Light"], bins=15, edgecolor="black")
    axis2.set_title("Distribution of Light Sensor Readings")
    axis2.set_xlabel("Light Sensor Reading")
    axis2.set_ylabel("Frequency")
    axis2.grid(axis="y", alpha=0.3)
    fig2.tight_layout()
    fig2.savefig("plot_2_light_distribution.png", dpi=200)

    # Plot 3: relationship between state and humidity change, if labels are available.
    labelled = df.dropna(subset=["State", "HumidityDelta"])
    states_present = [state for state in EXPECTED_STATES if state in labelled["State"].unique()]

    if len(states_present) >= 2:
        fig3, axis3 = plt.subplots(figsize=(10, 6))
        data = [
            labelled.loc[labelled["State"] == state, "HumidityDelta"]
            for state in states_present
        ]
        axis3.boxplot(data, tick_labels=states_present)
        axis3.set_title("Relative Humidity Change by Bathroom State")
        axis3.set_xlabel("Bathroom State")
        axis3.set_ylabel("Change from Session Baseline RH (percentage points)")
        axis3.grid(axis="y", alpha=0.3)
        fig3.tight_layout()
        fig3.savefig("plot_3_humidity_change_by_state.png", dpi=200)


def build_session_summary(df):
    labelled = df.dropna(subset=["SessionID", "State"]).copy()
    if labelled.empty:
        return pd.DataFrame()

    summaries = []

    for session_id, session in labelled.groupby("SessionID"):
        session = session.sort_values("DateTime")
        state = session["State"].iloc[0]

        logged_baseline = session["BaselineHumidityLogged"].dropna()
        baseline = logged_baseline.iloc[0] if not logged_baseline.empty else session["Humidity"].iloc[0]
        peak = session["Humidity"].max()
        humidity_change = peak - baseline

        elapsed_minutes = (
            session["DateTime"] - session["DateTime"].iloc[0]
        ).dt.total_seconds() / 60.0

        if len(session) >= 2 and elapsed_minutes.max() > 0:
            humidity_slope = np.polyfit(elapsed_minutes, session["Humidity"], 1)[0]
        else:
            humidity_slope = np.nan

        summaries.append({
            "SessionID": session_id,
            "State": state,
            "SampleCount": len(session),
            "BaselineHumidity": baseline,
            "PeakHumidity": peak,
            "HumidityChange": humidity_change,
            "HumiditySlopePerMin": humidity_slope,
            "PIRActivityRate": session["PIR"].mean(),
            "MeanTemperature": session["Temperature"].mean(),
            "MeanLight": session["Light"].mean(),
        })

    return pd.DataFrame(summaries)


def test_h2(session_summary):
    print("\nH2: SHOWER VS OCCUPIED HUMIDITY RESPONSE")
    print("----------------------------------------")

    if session_summary.empty:
        print("No labelled sessions are available; H2 cannot be tested.")
        return

    shower = session_summary[session_summary["State"] == "shower"]
    occupied = session_summary[session_summary["State"] == "occupied"]

    if shower.empty or occupied.empty:
        print("Both shower and occupied-without-shower sessions are required for H2.")
        return

    print(
        f"Mean RH increase - shower: {shower['HumidityChange'].mean():.2f} percentage points; "
        f"occupied: {occupied['HumidityChange'].mean():.2f} percentage points"
    )
    print(
        f"Mean RH slope - shower: {shower['HumiditySlopePerMin'].mean():.3f} pp/min; "
        f"occupied: {occupied['HumiditySlopePerMin'].mean():.3f} pp/min"
    )

    # The session, not each individual sensor row, is the independent observation.
    if len(shower) >= 2 and len(occupied) >= 2:
        change_test = stats.ttest_ind(
            shower["HumidityChange"], occupied["HumidityChange"], equal_var=False
        )
        slope_test = stats.ttest_ind(
            shower["HumiditySlopePerMin"].dropna(),
            occupied["HumiditySlopePerMin"].dropna(),
            equal_var=False,
        )
        print(f"Welch t-test for humidity increase: p={change_test.pvalue:.4f}")
        print(f"Welch t-test for humidity rate: p={slope_test.pvalue:.4f}")
    else:
        print(
            "Fewer than two independent sessions exist in one or both groups. "
            "Report the descriptive difference, but do not treat individual rows as independent samples."
        )


def find_group_split(labelled):
    """Find a session-based split that retains all observed classes in train and test."""
    observed_states = set(labelled["State"].unique())
    group_count = labelled["SessionID"].nunique()

    # The test set needs enough complete sessions to contain all three states.
    # With the minimum two sessions per state (six total), this means a 50/50 split.
    minimum_test_fraction = len(observed_states) / group_count
    test_fraction = max(0.30, minimum_test_fraction)

    if test_fraction >= 1.0:
        return None, None

    splitter = GroupShuffleSplit(n_splits=100, test_size=test_fraction, random_state=42)

    for train_index, test_index in splitter.split(
        labelled, labelled["State"], groups=labelled["SessionID"]
    ):
        train_states = set(labelled.iloc[train_index]["State"].unique())
        test_states = set(labelled.iloc[test_index]["State"].unique())

        if observed_states.issubset(train_states) and observed_states.issubset(test_states):
            return train_index, test_index

    return None, None


def test_h1_and_h3(df):
    print("\nH1/H3: DECISION TREE CLASSIFICATION")
    print("-----------------------------------")

    labelled = df.dropna(subset=["SessionID", "State"] + BASE_FEATURES).copy()
    labelled = labelled[labelled["State"].isin(EXPECTED_STATES)]

    if labelled.empty:
        print("No labelled data are available; classifier analysis is skipped.")
        return

    session_counts = labelled.groupby("State")["SessionID"].nunique()
    print("Independent session counts by state:")
    print(session_counts.to_string())

    # To have each class represented in both train and test, at least two sessions
    # per class are needed.
    if len(session_counts) < 3 or (session_counts < 2).any():
        print(
            "At least two independent sessions for each of vacant, occupied and shower "
            "are required for a defensible session-based train/test comparison."
        )
        return

    train_index, test_index = find_group_split(labelled)
    if train_index is None:
        print("Could not form a session-based split containing all states in both sets.")
        return

    train = labelled.iloc[train_index]
    test = labelled.iloc[test_index]

    y_train = train["State"]
    y_test = test["State"]

    comparisons = []

    # H1: compare each individual sensor with the complete four-sensor array.
    feature_sets = {
        "Humidity only": ["Humidity"],
        "Temperature only": ["Temperature"],
        "PIR only": ["PIR"],
        "Light only": ["Light"],
        "All sensors": BASE_FEATURES,
    }

    full_model = None
    full_predictions = None

    for name, features in feature_sets.items():
        model = DecisionTreeClassifier(max_depth=4, random_state=42)
        model.fit(train[features], y_train)
        predictions = model.predict(test[features])
        accuracy = accuracy_score(y_test, predictions)
        comparisons.append({"Model": name, "Accuracy": accuracy})

        if name == "All sensors":
            full_model = model
            full_predictions = predictions

    comparison_df = pd.DataFrame(comparisons).sort_values("Accuracy", ascending=False)
    print("\nH1 model comparison:")
    print(comparison_df.to_string(index=False, formatters={"Accuracy": "{:.3f}".format}))

    comparison_df.to_csv("model_comparison_h1.csv", index=False)

    fig, axis = plt.subplots(figsize=(10, 6))
    axis.bar(comparison_df["Model"], comparison_df["Accuracy"])
    axis.set_title("Decision Tree Accuracy by Sensor Configuration")
    axis.set_xlabel("Sensor Configuration")
    axis.set_ylabel("Accuracy")
    axis.set_ylim(0, 1)
    axis.tick_params(axis="x", rotation=25)
    fig.tight_layout()
    fig.savefig("plot_4_classifier_accuracy.png", dpi=200)

    if full_predictions is not None:
        print("\nFull sensor model classification report:")
        print(classification_report(y_test, full_predictions, zero_division=0))
        print("Confusion matrix:")
        print(confusion_matrix(y_test, full_predictions, labels=EXPECTED_STATES))

        fig_cm, axis_cm = plt.subplots(figsize=(7, 6))
        ConfusionMatrixDisplay.from_predictions(
            y_test,
            full_predictions,
            labels=EXPECTED_STATES,
            ax=axis_cm,
            colorbar=False,
        )
        axis_cm.set_title("Full Sensor Decision Tree Confusion Matrix")
        fig_cm.tight_layout()
        fig_cm.savefig("plot_5_confusion_matrix.png", dpi=200)

    # H3 is exploratory. The revised design does not specify one exact reduced subset,
    # so compare all 2- and 3-sensor subsets without treating the best one as definitive.
    reduced_results = []
    for feature_count in (2, 3):
        for features in itertools.combinations(BASE_FEATURES, feature_count):
            model = DecisionTreeClassifier(max_depth=4, random_state=42)
            model.fit(train[list(features)], y_train)
            predictions = model.predict(test[list(features)])
            reduced_results.append({
                "Sensors": " + ".join(features),
                "Accuracy": accuracy_score(y_test, predictions),
            })

    reduced_df = pd.DataFrame(reduced_results).sort_values("Accuracy", ascending=False)
    reduced_df.to_csv("model_comparison_h3_reduced.csv", index=False)

    print("\nH3 reduced-array comparison:")
    print(reduced_df.to_string(index=False, formatters={"Accuracy": "{:.3f}".format}))
    print(
        "Interpret H3 by comparing these reduced-array accuracies with the full-array result. "
        "The hypothesis uses the term 'comparable' but Task 3 did not define a numerical threshold, "
        "so report the observed difference rather than inventing one."
    )


def main():
    df = load_and_clean_raw_data()
    df, _ = add_session_labels(df)
    df = add_temporal_features(df)

    df.to_csv(PROCESSED_FILE, index=False)
    print(f"\nProcessed data saved to: {PROCESSED_FILE}")

    print_descriptive_statistics(df)
    make_basic_plots(df)

    session_summary = build_session_summary(df)
    if not session_summary.empty:
        session_summary.to_csv("session_summary.csv", index=False)
        print("Session-level summary saved to: session_summary.csv")

    test_h2(session_summary)
    test_h1_and_h3(df)

    plt.show()


if __name__ == "__main__":
    main()
