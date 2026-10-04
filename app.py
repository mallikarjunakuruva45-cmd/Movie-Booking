from flask import Flask, jsonify, render_template, request , redirect, session
import os
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import random
import time
from flask import session, flash
import requests

app = Flask(__name__)
app.secret_key = "movie_booking_secret_key"

#
MSG91_AUTHKEY = "561136TcjzLANfgKw6a873eb9P1" 

# MySQL Connection
# Look for Railway's MYSQL_URL or DATABASE_URL
database_url = os.environ.get('MYSQL_URL') or os.environ.get('DATABASE_URL') or 'mysql+pymysql://root:malli2005$@localhost/movie_booking'

# SQLAlchemy requires the exact driver name 'mysql+pymysql' instead of just 'mysql'
if database_url.startswith("mysql://"):
    database_url = database_url.replace("mysql://", "mysql+pymysql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)



# User Table

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(100))
    mobile = db.Column(db.String(15), unique=True, nullable=False)



# Movie Table
class Movie(db.Model):
    __tablename__ = 'movies'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    genre = db.Column(db.String(50))
    duration = db.Column(db.String(20))
    rating = db.Column(db.String(10))
    description = db.Column(db.Text)
    poster = db.Column(db.String(255))
    
    
    
# Admin Table
class Admin(db.Model):
    __tablename__ = 'admins'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50))
    password = db.Column(db.String(100))

class City(db.Model):
    __tablename__ = 'cities'

    id = db.Column(db.Integer, primary_key=True)
    city_name = db.Column(db.String(100))

@app.route('/select_city')
def select_city():

    cities = City.query.all()

    return render_template(
        'select_city.html',
        cities=cities
    )


class Area(db.Model):
    __tablename__ = 'areas'

    id = db.Column(db.Integer, primary_key=True)
    city_id = db.Column(db.Integer)
    area_name = db.Column(db.String(100))


class Theater(db.Model):
    __tablename__ = 'theaters'

    id = db.Column(db.Integer, primary_key=True)
    city_id = db.Column(db.Integer)
    area_id = db.Column(db.Integer)
    theater_name = db.Column(db.String(100))
    address = db.Column(db.String(255))

    # ADD THESE TWO LINES
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)

@app.route('/theater_movies/<int:theater_id>')
def theater_movies(theater_id):

    theater = db.session.get(Theater, theater_id)

    showtimes = db.session.query(
        ShowTime,
        Movie
    ).join(
        Movie,
        ShowTime.movie_id == Movie.id
    ).filter(
        ShowTime.theater_id == theater_id
    ).order_by(
        ShowTime.show_time
    ).all()

    return render_template(
        'theater_movies.html',
        theater=theater,
        showtimes=showtimes
    )

class ShowTime(db.Model):
    __tablename__ = "showtimes"

    id = db.Column(db.Integer, primary_key=True)
    theater_id = db.Column(db.Integer)
    screen_id = db.Column(db.Integer)
    movie_id = db.Column(db.Integer)
    show_date = db.Column(db.Date)
    show_time = db.Column(db.Time)
    ticket_price = db.Column(db.Float)


# Login Page

# =========================
# LOGIN PAGE
# =========================

@app.route('/', methods=['GET'])
def login():
    return render_template('login_mobile.html')


@app.route('/set_mobile', methods=['POST'])
def set_mobile():

    data = request.get_json() or {}

    mobile = str(data.get('mobile', '')).strip()

    # Keep digits only
    mobile = ''.join(ch for ch in mobile if ch.isdigit())

    # Convert 91XXXXXXXXXX to XXXXXXXXXX
    if mobile.startswith("91") and len(mobile) == 12:
        mobile = mobile[2:]

    print("================================")
    print("LOGIN MOBILE:", mobile)
    print("================================")

    if len(mobile) != 10:
        return jsonify({
            "success": False,
            "message": "Invalid mobile number."
        }), 400

    # DO NOT check database here.
    # MSG91 has already sent the OTP.

    session['mobile'] = mobile
    session['otp_pending'] = True

    print("Mobile stored in session:", mobile)

    return jsonify({
        "success": True,
        "message": "OTP sent successfully."
    })


@app.route('/verify_otp')
def verify_otp():

    mobile = session.get('mobile')

    if not mobile:
        return redirect('/')

    return render_template(
        'verify_otp.html',
        mobile=mobile
    )






# Signup Page

@app.route('/signup', methods=['GET', 'POST'])
def signup():

    if request.method == 'POST':

        fullname = request.form['fullname']
        mobile = request.form['mobile']
        

        user = User(
            fullname=fullname,
            mobile=mobile,
            
            
        )

        db.session.add(user)
        db.session.commit()

        return "User Registered Successfully!"

    return render_template('signup.html')


# Admin Login

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        admin = Admin.query.filter_by(
            username=username,
            password=password
        ).first()

        if admin:
            return redirect('/admin')

        return "Invalid Username or Password"

    return render_template('admin_login.html')



# Home Page

@app.route('/home')
def home():
    movies = Movie.query.all()
    return render_template('home.html', movies=movies)



# Movie Details

@app.route('/movie/<int:id>')
def movie(id):

    movie = Movie.query.get(id)

    return render_template(
        'movie_details.html',
        movie=movie
    )

@app.route('/delete_movie/<int:id>')
def delete_movie(id):

    movie = Movie.query.get(id)

    if movie:
        db.session.delete(movie)
        db.session.commit()

    return redirect('/admin')



# Seat Selection


from collections import OrderedDict



@app.route('/seats/<int:showtime_id>')
def seats(showtime_id):

    show = db.session.get(ShowTime, showtime_id)

    if show is None:
        return "Showtime not found."

    movie = db.session.get(Movie, show.movie_id)
    screen = db.session.get(Screen, show.screen_id)

    seats = Seat.query.filter_by(screen_id=screen.id).all()

    # Group seats into rows
    rows = {}

    for seat in seats:
        row = seat.seat_number[0]   # A, B, C...

        if row not in rows:
            rows[row] = []

        rows[row].append(seat)

    # Get booked seats for this showtime
    bookings = Booking.query.filter_by(showtime_id=show.id).all()

    booked_seats = []

    for booking in bookings:
        if booking.seats:
            booked_seats.extend(booking.seats.split(","))

    return render_template(
        "seats.html",
        movie=movie,
        screen=screen,
        rows=rows,
        show=show,
        booked_seats=booked_seats
    )




class Seat(db.Model):
    __tablename__ = "seats"

    id = db.Column(db.Integer, primary_key=True)
    screen_id = db.Column(db.Integer)
    showtime_id = db.Column(db.Integer)
    seat_number = db.Column(db.String(10))
    status = db.Column(db.String(20))

class Screen(db.Model):
    __tablename__ = "screens"

    id = db.Column(db.Integer, primary_key=True)
    theater_id = db.Column(db.Integer)
    screen_name = db.Column(db.String(50))
    total_rows = db.Column(db.Integer)
    seats_per_row = db.Column(db.Integer)

class Booking(db.Model):
    __tablename__ = 'bookings'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    showtime_id = db.Column(db.Integer)
    movie_id = db.Column(db.Integer)
    seats = db.Column(db.String(200))
    total_amount = db.Column(db.Float)
    booking_date = db.Column(db.DateTime)

    


# Booking Confirmation

from datetime import datetime



@app.route('/booking/<int:showtime_id>')
def booking(showtime_id):

    show = db.session.get(ShowTime, showtime_id)

    if show is None:
        return "Showtime not found."

    # Get movie
    movie = db.session.get(Movie, show.movie_id)

    # Get theater
    theater = db.session.get(Theater, show.theater_id)

    # Get screen
    screen = db.session.get(Screen, show.screen_id)

    # Get selected seats
    seats = request.args.get("seats", "")

    seat_list = [s for s in seats.split(",") if s]

    # Calculate total amount
    amount = len(seat_list) * float(show.ticket_price)

    # Create booking
    booking = Booking(
        user_id=session.get("user_id"),
        movie_id=movie.id,
        showtime_id=show.id,
        seats=",".join(seat_list),
        total_amount=amount
    )

    db.session.add(booking)
    db.session.commit()

    # Send all required information to booking.html
    return render_template(
        "booking.html",
        movie=movie,
        show=show,
        theater=theater,
        screen=screen,
        seats=seat_list,
        amount=amount,
        ticket=booking.id
    )





@app.route('/admin')
def admin():

    movies = Movie.query.all()

    return render_template(
        'admin.html',
        movies=movies
    )

@app.route('/add_movie', methods=['GET', 'POST'])
def add_movie():

    if request.method == 'POST':

        movie = Movie(
            title=request.form['title'],
            genre=request.form['genre'],
            duration=request.form['duration'],
            rating=request.form['rating'],
            description=request.form['description'],
            poster=request.form['poster']
        )

        db.session.add(movie)
        db.session.commit()

        return redirect('/admin')

    return render_template('add_movie.html')

@app.route('/mybookings')
def mybookings():

    bookings = Booking.query.filter_by(
        user_id=session['user_id']
    ).all()

    return render_template(
        "my_bookings.html",
        bookings=bookings
    )

import requests
from flask import redirect, request

@app.route('/location')
def location():
    return render_template('select_location.html')


@app.route('/search_cities')
def search_cities():

    query = request.args.get('q', '').strip()

    if not query:
        return jsonify([])

    cities = (
        City.query
        .filter(City.city_name.ilike(f'%{query}%'))
        .order_by(City.city_name)
        .limit(10)
        .all()
    )

    results = []

    for city in cities:

        theater_count = Theater.query.filter_by(
            city_id=city.id
        ).count()

        results.append({
            "id": city.id,
            "name": city.city_name,
            "theater_count": theater_count
        })

    return jsonify(results)


@app.route('/city/<int:city_id>')
def city_theaters(city_id):

    city = db.session.get(City, city_id)

    if city is None:
        return "City not found.", 404

    theaters = (
        Theater.query
        .filter_by(city_id=city.id)
        .order_by(Theater.theater_name)
        .all()
    )

    return render_template(
        'city_theaters.html',
        city=city,
        theaters=theaters
    )


from math import radians, sin, cos, sqrt, atan2

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)

    a = (
        sin(dlat/2)**2 +
        cos(radians(lat1)) *
        cos(radians(lat2)) *
        sin(dlon/2)**2
    )

    return R * 2 * atan2(sqrt(a), sqrt(1-a))


@app.route('/detect_location')
def detect_location():

    lat = request.args.get("lat", type=float)
    lon = request.args.get("lon", type=float)

    theaters = Theater.query.filter(
        Theater.latitude.isnot(None),
        Theater.longitude.isnot(None)
    ).all()

    nearby = []

    for theater in theaters:
        d = haversine(
            lat,
            lon,
            float(theater.latitude),
            float(theater.longitude)
        )

        nearby.append({
            "theater": theater,
            "distance": round(d, 1)
        })

    nearby.sort(key=lambda x: x["distance"])

    return render_template(
        "nearby_theaters.html",
        nearby=nearby[:20]
    )



@app.route("/verify_msg91", methods=["POST"])
def verify_msg91():

    try:
        data = request.get_json(silent=True) or {}

        mobile = data.get("mobile")
        access_token = data.get("access_token")

        print("\n================================")
        print("MSG91 ACCESS TOKEN VERIFICATION")
        print("================================")
        print("Mobile:", mobile)
        print("Access token received:", bool(access_token))

        
        # MOBILE
        

        if not mobile:
            mobile = session.get("mobile")

        if not mobile:
            return jsonify({
                "success": False,
                "message": "Mobile number is missing."
            }), 400

        # Keep digits only
        mobile = ''.join(ch for ch in str(mobile) if ch.isdigit())

        # Convert 91XXXXXXXXXX -> XXXXXXXXXX
        if mobile.startswith("91") and len(mobile) == 12:
            mobile = mobile[2:]

        if len(mobile) != 10:
            return jsonify({
                "success": False,
                "message": "Invalid mobile number."
            }), 400

        
        # ACCESS TOKEN
        

        if not access_token:
            print("ERROR: Access token missing")

            return jsonify({
                "success": False,
                "message": "MSG91 access token was not received."
            }), 400

        print("Access token received.")
        print("Token length:", len(access_token))

        
        # VERIFY ACCESS TOKEN WITH MSG91
        

        headers = {
            "authkey": MSG91_AUTHKEY,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        response = requests.post(
            "https://api.msg91.com/api/v5/widget/verifyAccessToken",
            headers=headers,
            json={
                "access-token": access_token
            },
            timeout=15
        )

        print("MSG91 HTTP STATUS:", response.status_code)
        print("MSG91 SERVER RESPONSE:", response.text)

        
        # PARSE RESPONSE
        

        try:
            result = response.json()
        except ValueError:
            result = {}

        
        # TOKEN VERIFIED
        

        if response.ok:

            print("MSG91 ACCESS TOKEN VERIFIED.")
            print("Verified mobile:", mobile)

            
            # FIND USER
            

            user = User.query.filter_by(mobile=mobile).first()

            
            # CREATE USER IF NEW
            

            if not user:

                print("New mobile number.")
                print("Creating new user...")

                user = User(
                    fullname="User",
                    mobile=mobile
                )

                db.session.add(user)
                db.session.commit()

                print("NEW USER CREATED")
                print("User ID:", user.id)
                print("Mobile:", user.mobile)

            else:

                print("Existing user found.")
                print("User ID:", user.id)
                print("Name:", user.fullname)

            
            # CREATE LOGIN SESSION
            

            session["logged_in"] = True
            session["user_id"] = user.id
            session["mobile"] = user.mobile
            session["fullname"] = user.fullname
            session["otp_pending"] = False

            print("================================")
            print("LOGIN SUCCESS")
            print("USER ID:", user.id)
            print("MOBILE:", user.mobile)
            print("================================")

            return jsonify({
                "success": True,
                "message": "Login successful.",
                "redirect": "/home"
            })

        
        # MSG91 REJECTED TOKEN
        

        print("MSG91 TOKEN VERIFICATION FAILED")

        error_message = (
            result.get("message")
            or result.get("error")
            or "MSG91 access token verification failed."
        )

        return jsonify({
            "success": False,
            "message": error_message
        }), 401

    except requests.RequestException as e:

        print("================================")
        print("MSG91 REQUEST ERROR")
        print(str(e))
        print("================================")

        return jsonify({
            "success": False,
            "message": "Unable to contact MSG91."
        }), 500

    except Exception as e:

        db.session.rollback()

        print("================================")
        print("VERIFY MSG91 ERROR")
        print(str(e))
        print("================================")

        return jsonify({
            "success": False,
            "message": "Login failed. Please try again."
        }), 500



# USER PROFILE


@app.route('/profile')
def profile():

    user_id = session.get('user_id')

    if not user_id:
        return redirect('/')

    user = db.session.get(User, user_id)

    if not user:
        session.clear()
        return redirect('/')

    return render_template(
        'profile.html',
        user=user
    )



# LOGOUT


@app.route('/logout')
def logout():

    session.clear()

    return redirect('/')





import json
from datetime import datetime

with app.app_context():
    db.create_all()
    
    # Auto-seed the database if it's empty
    try:
        with open('seed_data.json', 'r') as f:
            seed_data = json.load(f)
            
        model_map = {
            'User': User, 'Movie': Movie, 'Admin': Admin,
            'City': City, 'Area': Area, 'Theater': Theater,
            'Screen': Screen, 'ShowTime': ShowTime,
            'Seat': Seat, 'Booking': Booking
        }
        
        for table_name in ['User', 'Movie', 'Admin', 'City', 'Area', 'Theater', 'Screen', 'ShowTime', 'Seat', 'Booking']:
            model_class = model_map[table_name]
            
            # Skip if already has data
            if model_class.query.first():
                continue
                
            records = seed_data.get(table_name, [])
            objects = []
            
            for row in records:
                # Convert date/time strings back to objects
                for k, v in row.items():
                    if isinstance(v, str):
                        if len(v) == 10 and v.count('-') == 2:
                            try:
                                row[k] = datetime.strptime(v, '%Y-%m-%d').date()
                            except ValueError: pass
                        elif len(v) == 8 and v.count(':') == 2:
                            try:
                                row[k] = datetime.strptime(v, '%H:%M:%S').time()
                            except ValueError: pass
                        elif len(v) > 10 and '-' in v and ':' in v:
                            try:
                                row[k] = datetime.strptime(v.split('.')[0], '%Y-%m-%d %H:%M:%S')
                            except ValueError: pass
                            
                objects.append(model_class(**row))
            
            if objects:
                # Use fast bulk insert
                db.session.bulk_save_objects(objects)
                db.session.commit()
                
    except Exception as e:
        print("Seeding skipped/failed:", e)

if __name__ == '__main__':
    app.run(debug=True)

    

    