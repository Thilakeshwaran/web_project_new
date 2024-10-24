from flask import Flask, request, jsonify, render_template
import pandas as pd
from flask_cors import CORS
import logging
import traceback
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from threading import Lock
import os

app = Flask(__name__)

# Enable CORS for specific origins
CORS(app, resources={r"/*": {"origins": "*"}})

# Setup error log file with rotation
handler = RotatingFileHandler('error.log', maxBytes=10000, backupCount=1)
handler.setLevel(logging.ERROR)
app.logger.addHandler(handler)

# Enable logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Get the file path from environment variable or use default
file_path = 'updateddata2.xlsx'

# Cache to store the Excel data and reload timestamp
excel_cache = {
    'sheets': None,
    'last_loaded': None
}

# Lock to make cache access thread-safe
cache_lock = Lock()

# Function to load the Excel file and its sheets
def load_excel_sheets(file_path):
    global excel_cache
    reload_interval = timedelta(minutes=10)
    
    try:
        current_time = datetime.now()

        # Thread-safe access to cache
        with cache_lock:
            if excel_cache['sheets'] is None or (current_time - excel_cache['last_loaded']) > reload_interval:
                app.logger.info("Reloading Excel sheets...")
                excel_cache['sheets'] = pd.read_excel(file_path, sheet_name=None, engine='openpyxl')
                excel_cache['last_loaded'] = current_time
                app.logger.info(f"Excel file reloaded at {current_time}")
            else:
                app.logger.info("Using cached Excel data.")
        
        return excel_cache['sheets']
    except Exception as e:
        app.logger.error(f"Error reading Excel file: {e}")
        traceback.print_exc()
        return None

# Initially load the Excel sheets
excel_sheets = load_excel_sheets(file_path)
online_courses_sheet = excel_sheets.get("Online Courses(SCOFT)")

# Mapping department codes to Excel sheet names
DEPARTMENT_SHEETS = {
    "23": "AIDS - Mapped",
    "24": "AIML - Mapped",
    "11": "IOT - Mapped",
    "10": "Cyber Security(CS) - Mapped",
    "01": {
        "year_1_2": "CSE - II Years",
        "year_3_4": "CSE - Mapped, III & IV Years"
    },
    "22": {
        "year_1_2": "IT - II Years",
        "year_3_4": "IT - Mapped III & IV Years"
    }
}

# Mapping department codes to department names
DEPARTMENT_MAPPINGS = {
    "23": "Artificial Intelligence and Data Science (AIDS)",
    "24": "Artificial Intelligence and Machine Learning (AIML)",
    "10": "CSE (Cyber Security)",
    "11": "CSE (Internet of Things)",
    "01": "Computer Science and Engineering",
    "22": "Information Technology"
}

# Regulation Mapping Function
def get_regulation_mapping(admission_year):
    """Determine regulation based on the admission year."""
    admission_year = int(admission_year)
    if 19 <= admission_year <= 22:
        return "R2019"
    elif admission_year >= 23:
        return "R2024"
    else:
        return None

# Function to get department info based on the register number
def get_department_info(register_number):
    department_code = register_number[6:8]
    return DEPARTMENT_MAPPINGS.get(department_code, None)

# Function to get the sheet name based on the register number and student year
def get_department_sheet(register_number, student_year):
    department_code = register_number[6:8]

    if department_code not in DEPARTMENT_SHEETS:
        print(f"Department code {department_code} not found in DEPARTMENT_SHEETS")
        return None

    department_sheets = DEPARTMENT_SHEETS[department_code]

    if isinstance(department_sheets, dict):
        if student_year in [1, 2]:
            return department_sheets.get("year_1_2")
        elif student_year in [3, 4]:
            return department_sheets.get("year_3_4")
    else:
        return department_sheets

    return None

# Function to determine the regulation column based on admission year
def get_regulation_column(admission_year):
    regulation = get_regulation_mapping(admission_year)
    if regulation:
        return f"Course Code {regulation}"
    return None

# Function to calculate the student's current year of study
def get_student_year(admission_year):
    current_year = datetime.now().year % 100
    admission_year = int(admission_year)
    student_year = current_year - admission_year + 1

    if 1 <= student_year <= 4:
        return student_year
    elif student_year > 4:
        return "Graduated"
    return None

# Function to fetch relevant courses from the "Online Courses(SCOFT)" sheet
def get_relevant_courses(course_title):
    try:
        online_df = online_courses_sheet
        online_df.columns = online_df.columns.str.strip().str.replace('\n', ' ')

        relevant_courses = online_df[online_df['Course_Title'].str.contains(course_title, case=False, na=False)]
        if not relevant_courses.empty:
            return relevant_courses['Course_Title'].tolist()
        else:
            return []
    except Exception as e:
        traceback.print_exc()
        return []

@app.route('/')
def home():
    return render_template('index.html', key1=value1, key2=value2, key3=value3)


# API to fetch student info based on register number
@app.route('/get_student_info', methods=[ 'POST'])
def get_student_info():
    try:
        data = request.json
        register_number = data.get('register_number')

        if not register_number or len(register_number) != 12:
            return jsonify({"message": "Invalid Register Number", "status": "failure"}), 400

        department = get_department_info(register_number)
        if not department:
            return jsonify({"message": "Invalid Department Code", "status": "failure"}), 400

        admission_year = register_number[4:6]
        student_year = get_student_year(admission_year)

        regulation = get_regulation_column(admission_year)
        if not regulation:
            return jsonify({"message": "Invalid Admission Year", "status": "failure"}), 400

        return jsonify({
            "department": department,
            "student_year": student_year,
            "regulation": regulation,
            "status": "success"
        }), 200

    except Exception as e:
        logging.error(f"Error in get_student_info: {e}")
        traceback.print_exc()
        return jsonify({"message": f"Error occurred: {str(e)}", "status": "error"}), 500


@app.route('/check_eligibility', methods=['POST'])
def check_eligibility():
    try:
        # Load Excel sheets dynamically
        excel_sheets = load_excel_sheets(file_path)
        data = request.json
        register_number = data.get('register_number')
        course_title = data.get('course_title')

        # Validate register number and course title
        if not register_number or len(register_number) != 12:
            return jsonify({"message": "Invalid Register Number", "status": "failure"}), 400
        if not course_title:
            return jsonify({"message": "Course title is required", "status": "failure"}), 400

        # Extract admission year from register number (5th and 6th digits)
        admission_year = register_number[4:6]

        # Get the correct sheet based on the department and year of study
        student_year = get_student_year(admission_year)
        sheet_name = get_department_sheet(register_number, student_year)
        if not sheet_name:
            return jsonify({"message": "Invalid Department or Register Number", "status": "failure"}), 400

        # Load the specific sheet for the department
        df = excel_sheets[sheet_name]
        df.columns = df.columns.str.strip().str.replace('\n', ' ')
        df['Course Title'] = df['Course Title'].str.strip().str.lower()
        df['Category'] = df['Category'].fillna('')

        # Load online courses sheet
        online_courses_df = online_courses_sheet
        online_courses_df['Course_Title'] = online_courses_df['Course_Title'].str.strip().str.lower()

        # Step 1: Check for exact match in online courses
        exact_match_online = online_courses_df[online_courses_df['Course_Title'] == course_title.strip().lower()]

        if not exact_match_online.empty:
            # Check if the course is in the department sheet
            department_match = df[df['Course Title'].str.strip().str.lower() == course_title.strip().lower()]

            if not department_match.empty and department_match['Category'].str.upper().values[0] == "PC":
                return jsonify({"message": "ELIGIBILITY STATUS: Not Eligible (Professional Core - PC)", "status": "failure"}), 200
            
            return jsonify({"message": "Course is eligible", "status": "success"}), 200

        # Step 2: Check for partial matches in online courses
        partial_matches_online = online_courses_df[online_courses_df['Course_Title'].str.contains(course_title.strip().lower(), case=False)]

        if not partial_matches_online.empty:
            relevant_courses = partial_matches_online['Course_Title'].tolist()
            return jsonify({
                "message": "Here are some relevant courses",
                "status": "success",
                "relevant_courses": relevant_courses
            }), 200

        # Step 3: If no match found
        return jsonify({"message": "Course not found in online courses", "status": "failure"}), 404

    except Exception as e:
        logging.error(f"Error in check_eligibility: {e}")
        traceback.print_exc()
        return jsonify({"message": f"Error occurred: {str(e)}", "status": "error"}), 500


# API to fetch course suggestions based on register number and partial course title
@app.route('/get_course_suggestions', methods=['POST'])
def get_course_suggestions():
    try:
        data = request.json
        register_number = data.get('register_number')
        partial_course_title = data.get('partial_course_title')

        # Validate register number and partial course title
        if not register_number or len(register_number) != 12:
            print(f"Invalid Register Number: {register_number}")  # Debugging log
            return jsonify({"message": "Invalid Register Number", "status": "failure"}), 400
        if not partial_course_title:
            print("Course title is required")  # Debugging log
            return jsonify({"message": "Course title is required", "status": "failure"}), 400


        # Get the relevant sheet name based on the Register Number (department code)
        sheet_name = "Online Courses(SCOFT)"
        if not sheet_name:
            print(f"Sheet name not found for department with register number: {register_number}")  # Debugging log
            return jsonify({"message": "Invalid Department or Register Number", "status": "failure"}), 400

        # Load the specific sheet for the department
        df = excel_sheets[sheet_name]
        df.columns = df.columns.str.strip().str.replace('\n', ' ')
        print(f"Loaded sheet: {sheet_name}")  # Debugging log

        # Search for course titles that contain the partial course title (case insensitive)
        matching_courses = df[df['Course_Title'].str.contains(partial_course_title, case=False, na=False)]
        
        # Strip any leading/trailing whitespaces from course titles to avoid subtle differences
        matching_courses['Course_Title'] = matching_courses['Course_Title'].str.strip()
        print(f"Found matching courses: {matching_courses}")  # Debugging log

        # Return a list of matching course titles
        course_suggestions = matching_courses['Course_Title'].unique().tolist()

        return jsonify({"suggestions": course_suggestions, "status": "success"}), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"message": f"Error occurred: {str(e)}", "status": "error"}), 500

# API to search courses by title
@app.route('/search', methods=['POST'])
def search():
    try:
        data = request.json
        course_title = data.get('course_title')

        if not course_title:
            return jsonify({"message": "Course title is required", "status": "failure"}), 400

        relevant_courses = get_relevant_courses(course_title)

        if not relevant_courses:
            return jsonify({"message": "No relevant courses found", "status": "failure"}), 404

        return jsonify({
            "message": "Relevant courses found",
            "status": "success",
            "relevant_courses": relevant_courses
        }), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"message": f"Error occurred: {str(e)}", "status": "error"}), 500

if __name__ == '__main__':
    from waitress import serve
    app.debug = True
    serve(app, host='0.0.0.0', port=5001)