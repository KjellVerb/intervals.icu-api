import os
import requests
import json
import base64
from datetime import datetime

# Configuration
ATHLETE_ID = "ID"  # Replace with your athlete ID
API_KEY = "API_KEY"        # Replace with your API key
BASE_URL = "https://intervals.icu/api/v1/athlete"

# Encode "API_KEY:api_key" in Base64 for the Authorization header
def encode_auth(api_key):
    token = f"API_KEY:{api_key}".encode("utf-8")
    return base64.b64encode(token).decode("utf-8")

HEADERS = {
    "Authorization": f"Basic {encode_auth(API_KEY)}",
    "Content-Type": "application/json"
}

# Load training data from JSON file
def load_trainings(file_path):
    with open(file_path, "r") as file:
        return json.load(file)

# Convert duration values handling time (m, s) and distance (km)
def convert_duration(duration):
    if "km" in duration:
        return float(duration.replace("km", "")) * 1000  # Convert km to meters
    elif "m" in duration and not duration.endswith("km"):
        return int(duration.replace("m", "")) * 60  # Convert minutes to seconds
    elif "s" in duration:
        return int(duration.replace("s", ""))  # Keep seconds as is
    else:
        return int(duration)  # Default for unknown formats

# Format training data for API submission
def format_training_data(trainings):
    formatted_data = []
    for training_name, training in trainings.items():
        description_lines = []
        moving_time = 0

        for step in training["steps"]:
            if "reps" in step.keys():
                description_lines.append(f"\n{step['reps']}x")
                for substep in step["steps"]:
                    description_line = f"- {substep['description']}"
                    description_line += f" {substep['duration']}"
                    description_line += f" in {substep['zone']}"
                    description_line += f" cadence={substep['cadence']}" if 'cadence' in substep else ''
                    description_line += f" intensity={substep['intensity']}" if 'intensity' in substep else ''
                    description_lines.append(description_line)

                    moving_time += convert_duration(substep['duration'])

                description_lines.append('\n')
            else:
                description_line = f"- {step['description']}"
                description_line += f" {step['duration']}"
                description_line += f" in {step['zone']}"
                description_line += f" cadence={step['cadence']}" if 'cadence' in step else ''
                description_line += f" intensity={step['intensity']}" if 'intensity' in step else ''
                description_lines.append(description_line)

                moving_time += convert_duration(step['duration'])

        formatted_data.append({
            "start_date_local": training["date"] + "T00:00:00",
            "category": "WORKOUT",
            "name": training_name,
            "description": "\n".join(description_lines).strip(),
            "type": training["activity"],
            "moving_time": moving_time,
            "steps": training["steps"]
        })
    return formatted_data

# Upload training data to Intervals.icu
def upload_trainings(data):
    url = f"{BASE_URL}/{ATHLETE_ID}/events/bulk"
    response = requests.post(url, headers=HEADERS, json=data)
    if response.status_code == 200:
        print("Trainings uploaded successfully.")
    else:
        print(f"Failed to upload trainings. Status code: {response.status_code}")
        print(response.text)

# Main function
def main():
    try:
        os.chdir(os.path.dirname(__file__))
        trainings = load_trainings("trainings.json")
        formatted_data = format_training_data(trainings)
        upload_trainings(formatted_data)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
