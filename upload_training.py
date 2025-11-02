import os
import requests
import json
import base64
import argparse
from datetime import datetime, timedelta

def get_next_monday():
    """Get the date of the next Monday from today"""
    today = datetime.now()
    days_ahead = 7 - today.weekday()  # Monday is 0, so 7-0=7 for Monday, 7-1=6 for Tuesday, etc.
    if days_ahead == 7:  # If today is Monday, get next Monday
        days_ahead = 7
    elif today.weekday() == 0:  # If today is Monday, get next Monday
        days_ahead = 7
    return today + timedelta(days=days_ahead)

# Configuration
ATHLETE_ID = os.getenv("INTERVALS_ATHLETE_ID")  # Set via environment variable
API_KEY = os.getenv("INTERVALS_API_KEY")        # Set via environment variable
BASE_URL = "https://intervals.icu/api/v1/athlete"

# Validate required environment variables
if not ATHLETE_ID:
    raise ValueError("INTERVALS_ATHLETE_ID environment variable is required")
if not API_KEY:
    raise ValueError("INTERVALS_API_KEY environment variable is required")

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
def format_training_data(trainings, folder_id=None):
    formatted_data = []
    for training_name, training in trainings.items():
        description_lines = []
        moving_time = 0

        for step in training["steps"]:
            if "reps" in step.keys():
                description_lines.append(f"\n{step['description']} {step['reps']}x")
                for substep in step["steps"]:
                    description_line = f"- {substep['description']}"
                    description_line += f" {substep['duration']}"
                    description_line += f" in {substep['zone']}"
                    description_line += f" cadence={substep['cadence']}" if 'cadence' in substep else ''
                    description_line += f" pace={substep['pace']}" if 'pace' in substep else ''
                    description_line += f" power={substep['power']}" if 'power' in substep else ''
                    description_line += f" intensity={substep['intensity']}" if 'intensity' in substep else ''
                    description_lines.append(description_line)

                    moving_time += convert_duration(substep['duration'])

                description_lines.append('\n')
            else:
                description_line = f"- {step['description']}"
                description_line += f" {step['duration']}"
                description_line += f" in {step['zone']}"
                description_line += f" cadence={step['cadence']}" if 'cadence' in step else ''
                description_line += f" pace={step['pace']}" if 'pace' in step else ''
                description_line += f" power={step['power']}" if 'power' in step else ''
                description_line += f" intensity={step['intensity']}" if 'intensity' in step else ''
                description_lines.append(description_line)

                moving_time += convert_duration(step['duration'])

        formatted_data.append({
            "category": "WORKOUT",
            "name": training_name,
            "description": "\n".join(description_lines).strip(),
            "type": training["activity"],
            "moving_time": moving_time,
            "steps": training["steps"]
        })

        if folder_id == None:
            formatted_data[-1]["start_date_local"] = training["date"] + "T00:00:00"
        else:
            formatted_data[-1]["folder_id"] = folder_id
            formatted_data[-1]["day"] = training["day"]

    return formatted_data

# create training data to Intervals.icu
def create_plan(plan_name):
    folder_payload = {
        "name": plan_name,
        "type": "PLAN",
        "parent_id": None,  # Use `None` for null in Python
        "description": "Folder for " + plan_name,
        "start_date_local": get_next_monday().strftime("%Y-%m-%dT00:00:00")
    }
    url = f"{BASE_URL}/{ATHLETE_ID}/folders/"
    response = requests.post(url,  auth=('API_KEY', API_KEY), json=folder_payload)
    response_json = json.loads(response.text)
    folder_id = response_json['id']
    if response.status_code == 200:
        print(f"Training plan folder created successfully. Folder id: {folder_id}")
    else:
        print(f"Failed to create training plan folder. Status code: {response.status_code}")
        print(response.text)
    return folder_id

# Upload training data to Intervals.icu
def upload_workouts(data):
    if 'folder_id' in data[0]:
        url = f"{BASE_URL}/{ATHLETE_ID}/workouts/bulk"
    else:
        url = f"{BASE_URL}/{ATHLETE_ID}/events/bulk"
    response = requests.post(url, headers=HEADERS, json=data)
    if response.status_code == 200:
        print("Workouts uploaded successfully.")
    else:
        print(f"Failed to upload workouts. Status code: {response.status_code}")
        print(response.text)

# Main function
def main():
    parser = argparse.ArgumentParser(description='Upload training data to Intervals.icu. Either create a plan or upload separate workouts. The default start date for a plan is next Monday.')
    parser.add_argument('json_file', help='Path to the JSON file containing training data', default='trainings.json')
    parser.add_argument('--mode', choices=['plan', 'workouts'], default='workouts', 
                       help='Choose whether to create a plan or upload separate workouts (default: workouts)')
    parser.add_argument('--plan-name', default='Python training plan',
                       help='Name for the training plan (default: Python training plan)')
    
    args = parser.parse_args()
    
    try:
        os.chdir(os.path.dirname(__file__))
        trainings = load_trainings(args.json_file)
        
        if args.mode == 'plan':
            folder_id = create_plan(args.plan_name)
            formatted_data = format_training_data(trainings, folder_id)
        else:  # workouts mode
            formatted_data = format_training_data(trainings)
            
        upload_workouts(formatted_data)

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
