from flask import Flask, redirect, render_template, request, url_for
import psycopg2

app = Flask(__name__)

# Database connection
conn = psycopg2.connect(
    database="Lab5",
    user="postgres",
    password="postgres",
    host="localhost",
    port="5434"
)

# Route to render the homepage
@app.route('/')
def index():
    cursor = conn.cursor()

    # Fetch data from Doctor table
    cursor.execute("SELECT * FROM Doctor")
    doctors = cursor.fetchall()

    # Fetch data from Patient table
    cursor.execute("SELECT * FROM Patient")
    patients = cursor.fetchall()

    # Fetch data from Drug table
    cursor.execute("SELECT * FROM drug")
    drugs = cursor.fetchall()

    # Fetch data from Pharmacy table
    cursor.execute("SELECT * FROM Pharmacy")
    pharmacies = cursor.fetchall()

    # Fetch data from Examined_by table
    cursor.execute("SELECT * FROM examined_by")
    examined_by = cursor.fetchall()

    # Fetch data from Prescribes table
    cursor.execute("SELECT * FROM prescribes")
    prescribes = cursor.fetchall()

    # Fetch data from Pharmacy table
    cursor.execute("SELECT * FROM sells")
    sells = cursor.fetchall()

    # Fetch data from Patient table and count total patients
    cursor.execute("SELECT COUNT(*) FROM Patient")
    total_patients = cursor.fetchone()[0]

    # Retrieve drugs assigned and the number of doctors who prescribed each
    cursor.execute("""
        SELECT Drug.Name, COUNT(DISTINCT Prescribes.DID) AS Num_Doctors
        FROM Drug
        LEFT JOIN Prescribes ON Drug.MID = Prescribes.MID
        GROUP BY Drug.Name
    """)
    drugs_assigned = cursor.fetchall()

    return render_template('index.html', doctors=doctors, patients=patients, drugs=drugs, pharmacies=pharmacies, examined_by =examined_by, prescribes =prescribes, sells=sells, total_patients=total_patients, drugs_assigned=drugs_assigned)

@app.route('/doctor-info', methods=['GET'])
def doctor_info():
    doctor_id = request.args.get('doctor_id')

    # Fetch doctor details from the database
    cursor = conn.cursor()

    # Fetch doctor's name
    cursor.execute("SELECT Name FROM Doctor WHERE DID = %s", (doctor_id,))
    doctor_name_row = cursor.fetchone()
    if doctor_name_row:
        doctor_name = doctor_name_row[0]
    else:
        doctor_name = "Please enter Doctor ID"

    # Fetch the number of patients the doctor has
    cursor.execute("SELECT COUNT(PID) FROM Patient JOIN Doctor ON Patient.primarily_examined_by = Doctor.DID WHERE Patient.primarily_examined_by=%s", (doctor_id,))
    patient_count = cursor.fetchone()[0]
    
    patient_names =[]
    # Fetch the names of the doctor's patients
    if patient_count > 0:
        cursor.execute("SELECT Patient.Name FROM Patient JOIN Doctor ON Patient.primarily_examined_by = Doctor.DID WHERE Doctor.did=%s", (doctor_id,))
        patients = cursor.fetchall()
        if patients:
            for patient in patients:
                patient_names.append(patient[0])
        else:
                patient_names.append( "None")

    # Fetch the pharmacies supervised by the doctor
    cursor.execute("SELECT Name FROM Pharmacy WHERE Supervisor=%s", (doctor_id,))
    pharmacies_rows = cursor.fetchall()
    pharmacies=[]
    if pharmacies_rows:
        for pharmacy in pharmacies_rows:
            pharmacies.append(pharmacy[0])

    # Fetch all prescribed drugs for the doctor's patients
    prescribed_drugs = []
    cursor.execute("SELECT Prescribes.Description, Drug.Name, Patient.Name FROM Prescribes INNER JOIN Drug ON Prescribes.MID = Drug.MID INNER JOIN Patient ON Prescribes.PID = Patient.PID WHERE Prescribes.DID=%s", (doctor_id,))
    prescriptions = cursor.fetchall()
    if prescriptions:
        for prescription in prescriptions:
            prescribed_drugs.append(prescription[0] + " using drug: " + prescription[1] + " for patient: " + prescription[2])

    # Pass the fetched details to the HTML template
    return render_template('doctor_info.html', doctor_info={
        'name': doctor_name,
        'patient_count': patient_count,
        'patient_names': patient_names,
        'pharmacies': pharmacies,
        'prescribed_drugs': prescribed_drugs
    })

@app.route('/insert-patient', methods=['POST'])
def insert_patient():
    # Retrieve data from the form
    name = request.form['name']
    age = request.form['age']
    address = request.form['address']
    primary_doctor = request.form['primary_doctor']
    address = address or None
    cursor = conn.cursor()
    
    cursor.execute("SELECT MAX(PID) FROM Patient")
    max_pid = cursor.fetchone()[0]
    next_pid = max_pid + 1 if max_pid is not None else 1  # If no rows in the table, start from 1

    cursor.execute("INSERT INTO Patient (pid, Name, Age, Addresses, Primarily_examined_by) VALUES (%s, %s, %s, %s, %s)",
                   (next_pid,name, age, address, primary_doctor))
    conn.commit()
    return redirect(url_for('insert'))

@app.route('/insert')
def insert():
    cursor = conn.cursor()
    cursor.execute("SELECT DID, Name FROM Doctor")
    doctors = [{'DID': row[0], 'Name': row[1]} for row in cursor.fetchall()]
    cursor.execute("SELECT PID, Name FROM patient")
    patients = [{'Pid': row[0], 'Name': row[1]} for row in cursor.fetchall()]
    cursor.execute("SELECT MID, Name FROM Drug")
    drugs = [{'Mid': row[0], 'Name': row[1]} for row in cursor.fetchall()]
    return render_template('insert_req.html', doctors=doctors, patients=patients, drugs=drugs)

@app.route('/insert-doctor', methods=['POST'])
def insert_doctor():
    # Retrieve data from the form
    name = request.form['name']
    specialty = request.form['specialty']
    years_of_experience = request.form['years_of_experience']
    patient_id = request.form['patients']
    primary_patient = 'primary_patient' in request.form

    cursor = conn.cursor()

    # Fetch the maximum existing DID from the Doctor table
    cursor.execute("SELECT MAX(DID) FROM Doctor")
    max_did = cursor.fetchone()[0]
    next_did = max_did + 1 if max_did is not None else 1  # If no rows in the table, start from 1

    # Insert the new doctor into the Doctor table
    cursor.execute("INSERT INTO Doctor (DID, Name, Specialty, Years_of_Experience) VALUES (%s, %s, %s, %s)",
                   (next_did, name, specialty, years_of_experience))

    # Insert or update the Examined_by table based on whether the patient is primary or not
    if primary_patient:
        cursor.execute("UPDATE Patient SET Primarily_examined_by = %s WHERE PID = %s", (next_did, patient_id))
    else:
        cursor.execute("INSERT INTO Examined_by (DID, PID) VALUES (%s, %s)", (next_did, patient_id))

    # Commit the transaction
    conn.commit()

    return redirect(url_for('insert'))

@app.route('/insert-pharmacy', methods=['POST'])
def insert_pharmacy():
    # Retrieve data from the form
    name = request.form['name']
    location = request.form['location']
    supervisor = request.form['Supervisor']

    cursor = conn.cursor()
    cursor.execute("SELECT MAX(HID) FROM pharmacy")
    max_hid = cursor.fetchone()[0]
    next_hid = max_hid + 1 if max_hid is not None else 1  # If no rows in the table, start from 1

    cursor.execute("INSERT INTO pharmacy (hid, Name, location, supervisor) VALUES (%s, %s, %s, %s)",
                   (next_hid,name, location, supervisor ))
    conn.commit()
    return redirect(url_for('insert'))

@app.route('/insert-prescription', methods=['POST'])
def insert_prescription():
    # Retrieve data from the form
    patient_id = request.form['patients']
    doctor_id = request.form['doctor']
    drug_id = request.form['drug']
    date = request.form['date']
    description = request.form['description']

    cursor = conn.cursor()

    # Insert the prescription into the Prescribes table
    cursor.execute("INSERT INTO Prescribes (PID, DID, MID, Date, Description) VALUES (%s, %s, %s, %s, %s)",
                   (patient_id, doctor_id, drug_id, date, description))

    # Commit the transaction
    conn.commit()
    return redirect(url_for('insert'))

@app.route('/search-location', methods=['POST'])
def search_location():
    # Retrieve location input from the form
    location = request.form['location']

    cursor = conn.cursor()

    # Search for patients living at or near the specified location
    cursor.execute("SELECT PID, Name, Addresses FROM Patient WHERE Addresses LIKE %s", ('%' + location + '%',))
    patients = [{'Pid': row[0], 'Name': row[1], 'Address': row[2]} for row in cursor.fetchall()]


    # Search for pharmacies located at or near the specified location
    cursor.execute("SELECT HID, Name, Location FROM Pharmacy WHERE Location LIKE %s", ('%' + location + '%',))
    pharmacies = [{'hid': row[0], 'Name': row[1], 'Location': row[2]} for row in cursor.fetchall()]

    return render_template('Search.html', patients=patients, pharmacies=pharmacies)
@app.route('/search', methods=['GET'])
def search():
    return render_template('search.html')


@app.route('/patient-info', methods=['GET'])
def patient_info():
    name = request.args.get('name')

    cursor = conn.cursor()

    cursor.execute("SELECT PID FROM patient WHERE name = %s", (name,))
    pid_row = cursor.fetchone()
    if pid_row:
        pid = pid_row[0]
    else:
        pid = None

    cursor.execute("SELECT Doctor.name FROM DOCTOR JOIN patient ON doctor.did = patient.primarily_examined_by WHERE pid = %s", (pid,))
    primary_doctor_row = cursor.fetchone()
    if primary_doctor_row:
        primary_doctor = primary_doctor_row[0]
    else:
        primary_doctor = None

    cursor.execute("SELECT name FROM DOCTOR JOIN examined_by ON Doctor.did = examined_by.did WHERE examined_by.pid=%s", (pid,))
    normal_doctors_rows = cursor.fetchall()
    normal_doctors = []
    if normal_doctors_rows:
        for doctor in normal_doctors_rows:
            normal_doctors.append(doctor[0])
    
    cursor.execute("SELECT drug.name FROM DRUG JOIN PRESCRIBES ON Drug.mid = prescribes.mid WHERE prescribes.pid =%s", (pid,))
    Drugs_rows=cursor.fetchall()
    drugs = []
    if Drugs_rows:
        for drug in Drugs_rows:
            drugs.append(drug[0])
    
    # Pass the fetched details to the HTML template
    return render_template('patient-info.html', patient_info={
        'pid': pid,
        'primary_doctor': primary_doctor,
        'normal_doctors': normal_doctors,
        'Drugs': drugs
    })

if __name__ == '__main__':
    app.run(debug=True)