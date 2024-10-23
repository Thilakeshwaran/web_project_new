let timeout = null;
let lastCheckedCourseTitle = '';

console.log('JavaScript is connected!');

document.getElementById('register_number').addEventListener('keydown', function () {
    clearTimeout(timeout);  // Clear previous timeout

    // Wait for 1 second after the user stops typing
    timeout = setTimeout(() => {
        const registerNumber = document.getElementById('register_number').value;
        const messageDiv = document.getElementById('message');
        const loadingDiv = document.getElementById('loading');
        const studentInfoDiv = document.getElementById('student_info');

        // Clear old messages
        messageDiv.textContent = '';
        studentInfoDiv.style.display = 'none';  // Hide previous results

        if (validateRegisterNumber(registerNumber)) {
            // Indicate valid input field
            document.getElementById('register_number').classList.add('valid');
            document.getElementById('register_number').classList.remove('invalid');
            
            // Show loader
            loadingDiv.style.display = 'block';

            // Automatically call the student info checker when the input is valid
            fetchStudentInfo(registerNumber);
        } else {
            // Indicate invalid input field
            document.getElementById('register_number').classList.add('invalid');
            document.getElementById('register_number').classList.remove('valid');
            messageDiv.textContent = "Please enter a valid 12-digit Register Number.";
            messageDiv.style.color = "red";
        }
    }, 1000);  // Wait for 1000ms (1 second)
});

// Add keydown listener for course title input
document.getElementById('course_title').addEventListener('keydown', function (event) {
    // Trigger checkEligibility when Enter is pressed
    if (event.key === 'Enter') {
        event.preventDefault();  // Prevent default Enter behavior
        checkEligibility();  // Call the eligibility check on Enter
        document.getElementById('suggestions').innerHTML = '';
    }
});

// Add click listener for the Check Eligibility button
document.getElementById('checkEligibilityButton').addEventListener('click', function() {
    checkEligibility();  // Call the eligibility check when button is clicked
});

document.getElementById('course_title').addEventListener('input', () => {
    const courseTitle = document.getElementById('course_title').value.trim();
    const messageDiv = document.getElementById('message');
    const relevantCoursesDiv = document.getElementById('relevant_courses');

    if (courseTitle === '') {
        // If course title is cleared, hide the relevant courses and message
        relevantCoursesDiv.classList.remove('show');
        relevantCoursesDiv.style.display = 'none'; // Alternatively hide by setting display none

        messageDiv.classList.remove('show');
        messageDiv.style.display = 'none'; // Alternatively hide by setting display none
        lastCheckedCourseTitle = '';
    } else {
        // If there is text in the course title, show suggestions
        fetchCourseSuggestions();  // Call fetch for suggestions as user types
    }
});

// Separate validation function
function validateRegisterNumber(registerNumber) {
    return registerNumber.length === 12 && !isNaN(registerNumber);
}

// Fetch student info based on register number
function fetchStudentInfo(registerNumber) {
    const loadingDiv = document.getElementById('loading');
    const studentInfoDiv = document.getElementById('student_info');
    const messageDiv = document.getElementById('message');

    // Clear old messages
    messageDiv.textContent = '';

    fetch('http://127.0.0.1:5001/get_student_info', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ register_number: registerNumber })
    })
    .then(response => response.json())
    .then(data => {
        loadingDiv.style.display = 'none';  // Hide loader after response
        if (data.status === "success") {
            const department = `<p><strong>Department:</strong> ${data.department}</p>`;
            const year = `<p><strong>Year:</strong> ${data.student_year}</p>`;
            const regulation = `<p><strong>Regulation:</strong> ${data.regulation.replace('Course Code ', '')}</p>`;
            studentInfoDiv.innerHTML = `${department}${year}${regulation}`;
            studentInfoDiv.style.display = 'block';
        } else {
            studentInfoDiv.innerHTML = `<p style="color:red;">${data.message}</p>`;
            studentInfoDiv.style.display = 'block';
        }
    })
    .catch(error => {
        messageDiv.textContent = "Error fetching student info. Please try again later.";
        messageDiv.style.color = "orange";
        loadingDiv.style.display = 'none';  // Hide loader on error
    });
}

function checkEligibility() {
    const registerNumber = document.getElementById('register_number').value;
    const courseTitle = document.getElementById('course_title').value;
    const messageDiv = document.getElementById('message');
    const loadingDiv = document.getElementById('loading');
    const relevantCoursesDiv = document.getElementById('relevant_courses');

    // Clear old messages and suggestions
    messageDiv.textContent = '';
    messageDiv.classList.remove('show');  // Hide old messages
    relevantCoursesDiv.innerHTML = '';  // Clear previous relevant courses
    relevantCoursesDiv.classList.remove('show');  // Hide relevant courses initially
    document.getElementById('suggestions').innerHTML = '';  // Clear suggestions

    // Check if the eligibility check has already been performed for this course title
    if (courseTitle === lastCheckedCourseTitle) {
        return;  // Do nothing if it's the same course title as before
    }

    if (!validateRegisterNumber(registerNumber)) {
        messageDiv.textContent = "Please enter a valid 12-digit Register Number first.";
        messageDiv.style.color = "red";
        messageDiv.classList.add('show');  // Show error message
        return;
    }

    if (!courseTitle) {
        messageDiv.textContent = "Please enter a course title.";
        messageDiv.style.color = "red";
        messageDiv.classList.add('show');  // Show error message
        return;
    }

    // Show loader while checking eligibility
    loadingDiv.style.display = 'block';

    // Pass the partial course title to the server
    fetch('http://127.0.0.1:5001/check_eligibility', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            register_number: registerNumber,
            course_title: courseTitle  // This can be partial
        })
    })
    .then(response => response.json())
    .then(data => {
        loadingDiv.style.display = 'none';  // Hide loader after response

        // Regardless of eligibility, show relevant courses if they exist
        if (data.relevant_courses && data.relevant_courses.length > 0) {
            let suggestionsHTML = `<p><strong>Relevant Courses:</strong></p><ul>`;
            data.relevant_courses.forEach(course => {
                suggestionsHTML += `<li>${course}</li>`;
            });
            suggestionsHTML += `</ul>`;
            relevantCoursesDiv.innerHTML = suggestionsHTML;  // Display suggestions here
            relevantCoursesDiv.classList.add('show');  // Show relevant courses section
        }

        if (data.status === "success") {
            const eligibility = `<p><strong>Eligibility Status:</strong> ${data.message}</p>`;
            messageDiv.innerHTML = eligibility;
            messageDiv.style.color = "green";
            messageDiv.classList.add('show');  // Show success message
        } else {
            messageDiv.textContent = data.message;
            messageDiv.style.color = "red";
            messageDiv.classList.add('show');  // Show error message
        }
        // Set the last checked course title to the current one
        lastCheckedCourseTitle = courseTitle;
    })
    .catch(error => {
        messageDiv.textContent = "Error checking course eligibility. Please try again later.";
        messageDiv.style.color = "orange";
        messageDiv.classList.add('show');  // Show error message
        loadingDiv.style.display = 'none';  // Hide loader on error
    });
}


// Fetch course suggestions as the user types
function fetchCourseSuggestions() {
    const registerNumber = document.getElementById('register_number').value;
    const courseTitle = document.getElementById('course_title').value;
    const suggestionsDiv = document.getElementById('suggestions');
    // Clear old suggestions
    suggestionsDiv.innerHTML = '';

    // Don't fetch if the input is empty or invalid register number
    if (!courseTitle || !validateRegisterNumber(registerNumber)) {
        suggestionsDiv.innerHTML = '';  // Clear suggestions if the input is invalid
        return;
    }

    // Send fetch request to the server to get suggestions
    fetch('http://127.0.0.1:5001/get_course_suggestions', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            register_number: registerNumber,
            partial_course_title: courseTitle  // Use partial input for suggestions
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === "success") {
            const newSuggestions = [...new Set(data.suggestions)];  // Ensure uniqueness
            updateSuggestions(newSuggestions, suggestionsDiv);
        }
    })
    .catch(error => {
        console.error("Error fetching course suggestions:", error);
    });
}

// Helper function to update suggestions dropdown
function updateSuggestions(suggestions, suggestionsDiv) {
    if (suggestions.length > 0) {
        let suggestionsHTML = '';
        suggestions.forEach(suggestion => {
            suggestionsHTML += `<li onclick="selectSuggestion('${suggestion}')">${suggestion}</li>`;
        });
        suggestionsDiv.innerHTML = suggestionsHTML;
    } else {
        suggestionsDiv.innerHTML = '';
    }
}


// Function to handle selecting a suggestion (not mandatory)
function selectSuggestion(courseTitle) {
    document.getElementById('course_title').value = courseTitle;  // Set the value when clicked
    document.getElementById('suggestions').innerHTML = '';  // Clear suggestions after selection
    checkEligibility();
}

// Allow free typing in course title field without forcing a selection
document.getElementById('course_title').addEventListener('input', function() {
    fetchCourseSuggestions();  // Fetch suggestions as the user types
});
