-- PostgreSQL schema for DST Airlines project

-- Create sequences first (if needed)
CREATE SEQUENCE IF NOT EXISTS bts_flight_history_id_seq;

-- public.aircrafts definition
CREATE TABLE IF NOT EXISTS public.aircrafts (
	aircraft_code varchar(10) NOT NULL,
	airline_equip_code varchar(10) NULL,
	model varchar(100) NULL,
	CONSTRAINT aircrafts_pkey PRIMARY KEY (aircraft_code)
);

-- public.airlines definition
CREATE TABLE IF NOT EXISTS public.airlines (
	airline_code varchar(10) NOT NULL,
	airline_name varchar(255) NULL,
	airline_code_icao varchar(10) NULL,
	CONSTRAINT airlines_pkey PRIMARY KEY (airline_code)
);

-- public.countries definition
CREATE TABLE IF NOT EXISTS public.countries (
	code varchar(10) NOT NULL,
	"name" varchar(100) NULL,
	CONSTRAINT countries_pkey PRIMARY KEY (code)
);

-- public.cities definition
CREATE TABLE IF NOT EXISTS public.cities (
	city_code varchar(10) NOT NULL,
	"name" varchar(100) NULL,
	country_code varchar(10) NULL,
	CONSTRAINT cities_pkey PRIMARY KEY (city_code),
	CONSTRAINT cities_country_code_fkey FOREIGN KEY (country_code) REFERENCES public.countries(code)
);

-- public.airports definition
CREATE TABLE IF NOT EXISTS public.airports (
	iata_code varchar(10) NOT NULL,
	"name" varchar(255) NULL,
	city_code varchar(10) NULL,
	country_code varchar(10) NULL,
	latitude float8 NULL,
	longitude float8 NULL,
	timezone varchar(100) NULL,
	utc_offset varchar(10) NULL,
	location_type varchar(80) NULL,
	CONSTRAINT airports_pkey PRIMARY KEY (iata_code),
	CONSTRAINT airports_city_code_fkey FOREIGN KEY (city_code) REFERENCES public.cities(city_code),
	CONSTRAINT airports_country_code_fkey FOREIGN KEY (country_code) REFERENCES public.countries(code)
);

-- public.routes definition
CREATE TABLE IF NOT EXISTS public.routes (
	id serial4 NOT NULL,
	departure_airport varchar(10) NULL,
	arrival_airport varchar(10) NULL,
	distance int4 NOT NULL DEFAULT 0,
	important bool DEFAULT false NOT NULL,
	CONSTRAINT routes_pkey PRIMARY KEY (id),
	CONSTRAINT routes_arrival_airport_fkey FOREIGN KEY (arrival_airport) REFERENCES public.airports(iata_code),
	CONSTRAINT routes_departure_airport_fkey FOREIGN KEY (departure_airport) REFERENCES public.airports(iata_code)
);

-- public.bts_flight_history definition (FIXED)
CREATE TABLE IF NOT EXISTS public.bts_flight_history (
	id SERIAL NOT NULL,  -- This will automatically create the sequence
	"year" int4 NULL,
	"month" int4 NULL,
	carrier varchar(10) NULL,
	carrier_name varchar(100) NULL,
	airport varchar(10) NULL,
	airport_name varchar(100) NULL,
	arr_flights int4 NULL,
	arr_del15 int4 NULL,
	carrier_ct int4 NULL,
	weather_ct int4 NULL,
	nas_ct int4 NULL,
	security_ct int4 NULL,
	late_aircraft_ct int4 NULL,
	arr_cancelled int4 NULL,
	arr_diverted int4 NULL,
	arr_delay int4 NULL,
	carrier_delay int4 NULL,
	weather_delay int4 NULL,
	nas_delay int4 NULL,
	security_delay int4 NULL,
	late_aircraft_delay int4 NULL,
	CONSTRAINT bts_flight_history_pkey PRIMARY KEY (id)
);

-- public.historical_flights definition
CREATE TABLE IF NOT EXISTS public.historical_flights (
	id serial4 NOT NULL,
	"source" varchar(20) NOT NULL,
	delay_minutes int4 NULL,
	is_delayed bool NULL,
	bts_flight_history_id int4 NULL,
	CONSTRAINT historical_flights_pkey PRIMARY KEY (id),
	CONSTRAINT historical_flights_bts_flight_history_id_fkey FOREIGN KEY (bts_flight_history_id) REFERENCES public.bts_flight_history(id)
);

-- public.lufthansa_flight_history definition
CREATE TABLE IF NOT EXISTS public.lufthansa_flight_history (
	id serial4 NOT NULL,
	total_journey_duration varchar(15) NULL,
	route_id int4 NULL,
	route_sens varchar(5) NULL,
	departure_schedule_date date NULL,
	departure_schedule_time time NULL,
	departure_terminal varchar(10) NULL,
	arrival_schedule_date date NULL,
	arrival_schedule_time time NULL,
	arrival_terminal varchar(10) NULL,
	marketing_carrier_airline_id varchar(10) NULL,
	marketing_carrier_flight_number varchar(10) NULL,
	equipment_aircraft_code varchar(10) NULL,
	real_departure_schedule_date date NULL,
	real_departure_schedule_time time NULL,
	real_arrival_schedule_date date NULL,
	real_arrival_schedule_time time NULL,
	delay_on_departure interval NULL,
	delay_on_arrival interval NULL,
	CONSTRAINT lufthansa_flight_history_pkey PRIMARY KEY (id),
	CONSTRAINT unique_flight_per_day UNIQUE (marketing_carrier_airline_id, marketing_carrier_flight_number, departure_schedule_date),
	CONSTRAINT lufthansa_flight_history_equipment_aircraft_code_fkey FOREIGN KEY (equipment_aircraft_code) REFERENCES public.aircrafts(aircraft_code),
	CONSTRAINT lufthansa_flight_history_marketing_carrier_airline_id_fkey FOREIGN KEY (marketing_carrier_airline_id) REFERENCES public.airlines(airline_code),
	CONSTRAINT lufthansa_flight_history_route_id_fkey FOREIGN KEY (route_id) REFERENCES public.routes(id)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_routes_arrival_airport ON public.routes USING btree (arrival_airport);
CREATE INDEX IF NOT EXISTS idx_routes_departure_airport ON public.routes USING btree (departure_airport);
CREATE INDEX IF NOT EXISTS idx_routes_important ON public.routes USING btree (important) WHERE (important = true);
CREATE INDEX IF NOT EXISTS idx_routes_origin_destination ON public.routes USING btree (departure_airport, arrival_airport);
CREATE INDEX IF NOT EXISTS idx_flight_history_route_date ON public.lufthansa_flight_history USING btree (route_id, departure_schedule_date);
CREATE INDEX IF NOT EXISTS idx_lh_aircraft_code ON public.lufthansa_flight_history USING btree (equipment_aircraft_code);
CREATE INDEX IF NOT EXISTS idx_lh_airline_id ON public.lufthansa_flight_history USING btree (marketing_carrier_airline_id);
CREATE INDEX IF NOT EXISTS idx_lh_route_id ON public.lufthansa_flight_history USING btree (route_id);