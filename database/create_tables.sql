
-- Table: Countries
CREATE TABLE IF NOT EXISTS countries (
    code VARCHAR(10) PRIMARY KEY,
    name VARCHAR(100)
);

-- Table: Cities
CREATE TABLE IF NOT EXISTS cities (
    city_code VARCHAR(10) PRIMARY KEY,
    name VARCHAR(100),
    country_code VARCHAR(10) REFERENCES countries(code)
);

-- Table: Airports
CREATE TABLE IF NOT EXISTS airports (
    iata_code VARCHAR(10) PRIMARY KEY,
    name VARCHAR(255),
    city_code VARCHAR(10) REFERENCES cities(city_code),
    country_code VARCHAR(10) REFERENCES countries(code),
    latitude FLOAT,
    longitude FLOAT,
    timezone VARCHAR(100),
    utc_offset VARCHAR(10)
);

-- Table: Airlines
CREATE TABLE IF NOT EXISTS airlines (
    airline_code VARCHAR(10) PRIMARY KEY,
    airline_name VARCHAR(255),
    airline_code_icao VARCHAR(10)
);

-- Table: Aircrafts
CREATE TABLE IF NOT EXISTS aircrafts (
    aircraft_code VARCHAR(10) PRIMARY KEY,
    airline_equip_code VARCHAR(10),
    model VARCHAR(100)
);

-- Table: Routes
CREATE TABLE IF NOT EXISTS routes (
    id SERIAL PRIMARY KEY,
    flight_number VARCHAR(20),
    airline_code VARCHAR(10) REFERENCES airlines(airline_code),
    departure_airport VARCHAR(10) REFERENCES airports(iata_code),
    arrival_airport VARCHAR(10) REFERENCES airports(iata_code),
    operating_days VARCHAR(7)
);

-- Table: Historical Flights
CREATE TABLE historical_flights (
    id SERIAL PRIMARY KEY,
    source VARCHAR(20) NOT NULL, -- 'BTS' ou 'FLIGHTRADAR'
    delay_minutes INTEGER,
    is_delayed BOOLEAN,
    bts_data_history_id INTEGER REFERENCES bts_data_history(id)
);


CREATE TABLE IF NOT EXISTS bts_data_history (
    id SERIAL PRIMARY KEY,
    year INTEGER,
    month INTEGER,
    carrier VARCHAR(10),
    carrier_name VARCHAR(100),
    airport VARCHAR(10),
    airport_name VARCHAR(100),
    arr_flights INTEGER,
    arr_del15 INTEGER,
    carrier_ct INTEGER,
    weather_ct INTEGER,
    nas_ct INTEGER,
    security_ct INTEGER,
    late_aircraft_ct INTEGER,
    arr_cancelled INTEGER,
    arr_diverted INTEGER,
    arr_delay INTEGER,
    carrier_delay INTEGER,
    weather_delay INTEGER,
    nas_delay INTEGER,
    security_delay INTEGER,
    late_aircraft_delay INTEGER
);
