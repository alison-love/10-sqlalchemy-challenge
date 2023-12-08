# import dependencies

from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, func
from flask import Flask, jsonify
import datetime as dt
import numpy as np

# set up the database

engine = create_engine('sqlite:///hawaii.sqlite')
Base = automap_base()
Base.prepare(autoload_with=engine)

# map the tables

station = Base.classes.station
measurement = Base.classes.measurement

# Flask setup

app = Flask(__name__)

def calculate_one_year_ago(session):
    most_recent_date = session.query(func.max(measurement.date)).scalar()
    most_recent_date = dt.datetime.strptime(most_recent_date, '%Y-%m-%d')
    return most_recent_date - dt.timedelta(days=365)

def get_most_active_station_id(session):
    return session.query(measurement.station, func.count(measurement.station))\
                  .group_by(measurement.station)\
                  .order_by(func.count(measurement.station).desc())\
                  .first()[0]

# define Flask routes

@app.route('/')
def home():
    return (
        f"Welcome to the Hawaii Climate Analysis API!<br/>"
        f"Available Routes:<br/>"
        f"/api/v1.0/precipitation<br/>"
        f"/api/v1.0/stations<br/>"
        f"/api/v1.0/tobs<br/>"
        f"/api/v1.0/&lt;start&gt;<br/>"
        f"/api/v1.0/&lt;start&gt;/&lt;end&gt;"
    )

@app.route('/api/v1.0/precipitation')
def precipitation():
    session = Session(engine)
    one_year_ago = calculate_one_year_ago(session)

    results = session.query(measurement.date, measurement.prcp).filter(measurement.date >= one_year_ago).all()
    session.close()
    
    precipitation_dict = {date: prcp for date, prcp in results}
    return jsonify(precipitation_dict)

@app.route('/api/v1.0/stations')
def stations():
    session = Session(engine)
    results = session.query(station.station).all()
    session.close()

    stations_list = [item[0] for item in results]
    return jsonify(stations_list)

@app.route('/api/v1.0/tobs')
def tobs():
    session = Session(engine)
    one_year_ago = calculate_one_year_ago(session)
    most_active_station_id = get_most_active_station_id(session)

    results = session.query(measurement.date, measurement.tobs).\
        filter(measurement.station == most_active_station_id).\
        filter(measurement.date >= one_year_ago).all()
    session.close()

    tobs_list = list(np.ravel(results))
    return jsonify(tobs_list)

@app.route('/api/v1.0/<start>')
def start(start):
    session = Session(engine)

    # try to parse the start date, return an error if the format is incorrect
    try:
        start_date = dt.datetime.strptime(start, '%Y-%m-%d')
    except ValueError:
        session.close()
        return jsonify({"error": "Invalid start date format. Please use YYYY-MM-DD."}), 400

    results = session.query(func.min(measurement.tobs), 
                            func.avg(measurement.tobs), 
                            func.max(measurement.tobs)).\
                        filter(measurement.date >= start_date).all()
    session.close()

    # check if data is found
    if results[0][0] is None:
        return jsonify({"error": "No data found for the given start date."}), 404

    temps = {'min_temperature': results[0][0], 
             'avg_temperature': results[0][1], 
             'max_temperature': results[0][2]}

    return jsonify(temps)

@app.route('/api/v1.0/<start>/<end>')
def start_end(start, end):
    session = Session(engine)

    # try to parse the start and end dates, return an error if the format is incorrect
    
    try:
        start_date = dt.datetime.strptime(start, '%Y-%m-%d')
        end_date = dt.datetime.strptime(end, '%Y-%m-%d')
    except ValueError:
        session.close()
        return jsonify({"error": "Invalid date format. Please use YYYY-MM-DD."}), 400

    # ensure start_date is before end_date

    if start_date > end_date:
        session.close()
        return jsonify({"error": "Start date must be before end date."}), 400

    results = session.query(func.min(measurement.tobs), 
                            func.avg(measurement.tobs), 
                            func.max(measurement.tobs)).\
                        filter(measurement.date >= start_date, 
                               measurement.date <= end_date).all()
    session.close()

    # check if data is found

    if results[0][0] is None:
        return jsonify({"error": "No data found for the given date range."}), 404

    temps = {'min_temperature': results[0][0], 
             'avg_temperature': results[0][1], 
             'max_temperature': results[0][2]}

    return jsonify(temps)


if __name__ == '__main__':
    app.run(debug=True)