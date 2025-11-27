# Main server app

from flask import Flask, render_template, request, redirect, url_for, make_response, session
from werkzeug.utils import secure_filename
import os
from os.path import join, dirname, realpath, basename
import database
import json
from datetime import datetime

os.chdir(__file__.replace(basename(__file__), ''))

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Change this to a secure key in production
UPLOAD_FOLDER = join(dirname(realpath(__file__)), 'static/uploads/')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/')
def index():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    room = database.source("all_rooms.sql")
    types = database.source("all_room_types.sql")
    types = {type[0]: [type[1], type[2]] for type in types}

    customer = database.source("all_customers.sql")
    customer_dict = {c[0]: c[1] + " " + c[2] for c in customer}

    employees = database.source("all_employees.sql")
    jobs = database.source("all_jobs.sql")
    jobs = {job[0]: [job[1], job[2]] for job in jobs}

    reservations = database.source("all_reservations.sql")
    success = request.args.get('success')
    return render_template("index.html", len_room=len(room),
                            room=room, room_type=types,
                            customer=customer, len_cust=len(customer),
                            jobs=jobs, employees=employees,
                            len_emp=len(employees), len_res=len(reservations),
                            cust_dict=customer_dict, res=reservations, success=success)

@app.route('/Customer', methods=['GET', 'POST'])
def customer():
    if request.method == 'POST':
        fname = request.form['fname']
        lname = request.form['lname']
        address = request.form['address']
        ph_no = request.form['ph_no']
        database.source("new_customer.sql", fname, lname, address, ph_no, 0, output=False)
        return redirect(url_for('index', success='Customer added successfully'))
    return render_template("new_form.html", var="Customer")

@app.route('/Employee', methods=['GET', 'POST'])
def employee():
    if request.method == 'POST':
        fname = request.form['fname']
        lname = request.form['lname']
        address = request.form['address']
        ph_no = request.form['ph_no']
        job_id = request.form['job']
        database.source("new_employee.sql", job_id, fname, lname, address, ph_no, output=False)
        return redirect(url_for('index', success='Employee added successfully'))
    jobs = database.source("all_jobs.sql")
    return render_template("new_form.html", var="Employee", jobs=jobs)

@app.route('/reservation', methods=['GET', 'POST'])
def reservation():
    if request.method == 'POST':
        cust_id = int(request.form['cust'])
        room = int(request.form['room'])
        date_format = "%Y-%m-%d"
        in_date = datetime.strptime(request.form['in'], date_format)
        out_date = datetime.strptime(request.form['out'], date_format)
        days = out_date - in_date
        days = days.days + 1
        t_id = request.form['txn']
        t_date = request.form['dated']
        mode = request.form['mode']
        amount = int(request.form['amount'])
        status = int(request.form['status'])

        res_id = database.source("new_reservation.sql",
                                cust_id, room, t_id, in_date, out_date, days,
                                output=False, lastRowId=True)
        database.source("new_transaction.sql",
                        t_id, None, res_id, t_date, amount, mode, 1, status, output=False)

        return redirect(url_for('index', success='Reservation added successfully'))
    customer = database.source("all_customers.sql")
    rooms = database.source("all_rooms.sql")
    return render_template("reservation.html", customer=customer, rooms=rooms)

@app.route('/t')
def transaction_details():
    id = request.args["id"]
    details = database.source("get_transaction.sql", id)[0]
    details = {"date": str(details[0]),
                "amount": details[1],
                "payment": details[2],
                "status": details[3]
            }
    return json.dumps(details)

@app.route('/del/<name>')
def delete(name):
    id = request.args["id"]
    print(id)
    if name == "room":
        database.source("del_room.sql", id, output=False)
    elif name == "res":
        database.source("del_reservation.sql", id, output=False)
    elif name == "cust":
        database.source("del_customer.sql", id, output=False)
    elif name == "emp":
        database.source("del_employee.sql", id, output=False)
    
    return redirect(url_for('index'))

@app.route('/import')
def imp():
    return render_template("import.html")

@app.route('/import/<name>', methods=['POST'])
def imprt(name):
    file = request.files['file']
    if file:
        filename = secure_filename(file.filename)
        filename = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filename)
        database.import_from_csv(name, filename)
    return redirect(url_for('imp'))

@app.route('/export')
def exp():
    return render_template("export.html")

@app.route('/export/<name>')
def exprt(name):
    filename = f"./static/exports/{name}.csv"
    database.export_to_csv(name, filename)

    response = make_response(filename, 200)
    response.mimetype = "text/plain"
    return response

@app.route('/clear')
def clear():
    database.clear()
    return redirect(url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == 'admin' and password == 'password':
            session['logged_in'] = True
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='Invalid credentials')
    success = request.args.get('success')
    return render_template('login.html', success=success)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        if password != confirm_password:
            return render_template('signup.html', error='Passwords do not match')
        # For demo purposes, just redirect to login with success message
        # In a real app, save to database
        return redirect(url_for('login', success='Account created successfully. Please log in.'))
    return render_template('signup.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
    