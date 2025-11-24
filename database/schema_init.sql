-- DST Airlines Database Schema Initialization
-- Creates all tables in correct dependency order

-- Create sequences
CREATE SEQUENCE IF NOT EXISTS bts_data_history_id_seq;
CREATE SEQUENCE IF NOT EXISTS historical_flights_id_seq;
CREATE SEQUENCE IF NOT EXISTS lufthansa_flight_history_id_seq;
CREATE SEQUENCE IF NOT EXISTS routes_id_seq;

-- 1. Countries (no dependencies)
CREATE TABLE IF NOT EXISTS public.countries (
    code character varying(10) primary key not null,
    name character varying(100)
);

-- 2. Aircrafts (no dependencies)
CREATE TABLE IF NOT EXISTS public.aircrafts (
    aircraft_code character varying(10) primary key not null,
    airline_equip_code character varying(10),
    model character varying(100)
);

-- 3. Airlines (no dependencies)
CREATE TABLE IF NOT EXISTS public.airlines (
    airline_code character varying(10) primary key not null,
    airline_name character varying(255),
    airline_code_icao character varying(10)
);

-- 4. Cities (depends on countries)
CREATE TABLE IF NOT EXISTS public.cities (
    city_code character varying(10) primary key not null,
    name character varying(100),
    country_code character varying(10),
    foreign key (country_code) references public.countries (code)
        match simple on update no action on delete no action
);

-- 5. Airports (depends on cities and countries)
CREATE TABLE IF NOT EXISTS public.airports (
    iata_code character varying(10) primary key not null,
    name character varying(255),
    city_code character varying(10),
    country_code character varying(10),
    latitude double precision,
    longitude double precision,
    timezone character varying(100),
    utc_offset character varying(10),
    location_type character varying(80),
    foreign key (city_code) references public.cities (city_code)
        match simple on update no action on delete no action,
    foreign key (country_code) references public.countries (code)
        match simple on update no action on delete no action
);

-- 6. Routes (depends on airports)
CREATE TABLE IF NOT EXISTS public.routes (
    id integer primary key not null default nextval('routes_id_seq'::regclass),
    departure_airport character varying(10),
    arrival_airport character varying(10),
    distance integer not null default 0,
    important boolean not null default false,
    foreign key (arrival_airport) references public.airports (iata_code)
        match simple on update no action on delete no action,
    foreign key (departure_airport) references public.airports (iata_code)
        match simple on update no action on delete no action
);

-- Create indexes for routes
CREATE INDEX IF NOT EXISTS idx_routes_departure_airport ON routes USING btree (departure_airport);
CREATE INDEX IF NOT EXISTS idx_routes_arrival_airport ON routes USING btree (arrival_airport);
CREATE INDEX IF NOT EXISTS idx_routes_origin_destination ON routes USING btree (departure_airport, arrival_airport);
CREATE INDEX IF NOT EXISTS idx_routes_important ON routes USING btree (important) WHERE (important = true);

-- 7. BTS Flight History (no dependencies on other flight tables)
CREATE TABLE IF NOT EXISTS public.bts_flight_history (
    id integer primary key not null default nextval('bts_data_history_id_seq'::regclass),
    year integer,
    month integer,
    carrier character varying(10),
    carrier_name character varying(100),
    airport character varying(10),
    airport_name character varying(100),
    arr_flights integer,
    arr_del15 integer,
    carrier_ct integer,
    weather_ct integer,
    nas_ct integer,
    security_ct integer,
    late_aircraft_ct integer,
    arr_cancelled integer,
    arr_diverted integer,
    arr_delay integer,
    carrier_delay integer,
    weather_delay integer,
    nas_delay integer,
    security_delay integer,
    late_aircraft_delay integer
);

-- 8. Lufthansa Flight History (depends on routes, airlines, aircrafts)
CREATE TABLE IF NOT EXISTS public.lufthansa_flight_history (
    id integer primary key not null default nextval('lufthansa_flight_history_id_seq'::regclass),
    total_journey_duration character varying(15),
    route_id integer,
    route_sens character varying(5),
    departure_schedule_date date,
    departure_schedule_time time without time zone,
    departure_terminal character varying(10),
    arrival_schedule_date date,
    arrival_schedule_time time without time zone,
    arrival_terminal character varying(10),
    marketing_carrier_airline_id character varying(10),
    marketing_carrier_flight_number character varying(10),
    equipment_aircraft_code character varying(10),
    real_departure_schedule_date date,
    real_departure_schedule_time time without time zone,
    real_arrival_schedule_date date,
    real_arrival_schedule_time time without time zone,
    delay_on_departure interval,
    delay_on_arrival interval,
    depart_airport_meteo jsonb,
    arr_airport_meteo jsonb,
    actuals_refreshed boolean not null default false,
    actuals_refreshed_at timestamp with time zone,
    foreign key (equipment_aircraft_code) references public.aircrafts (aircraft_code)
        match simple on update no action on delete no action,
    foreign key (marketing_carrier_airline_id) references public.airlines (airline_code)
        match simple on update no action on delete no action,
    foreign key (route_id) references public.routes (id)
        match simple on update no action on delete no action
);

-- Create indexes for lufthansa_flight_history
CREATE UNIQUE INDEX IF NOT EXISTS unique_flight_per_day ON lufthansa_flight_history USING btree (marketing_carrier_airline_id, marketing_carrier_flight_number, departure_schedule_date);
CREATE INDEX IF NOT EXISTS idx_lh_route_id ON lufthansa_flight_history USING btree (route_id);
CREATE INDEX IF NOT EXISTS idx_lh_airline_id ON lufthansa_flight_history USING btree (marketing_carrier_airline_id);
CREATE INDEX IF NOT EXISTS idx_lh_aircraft_code ON lufthansa_flight_history USING btree (equipment_aircraft_code);
CREATE INDEX IF NOT EXISTS idx_flight_history_route_date ON lufthansa_flight_history USING btree (route_id, departure_schedule_date);
CREATE INDEX IF NOT EXISTS ix_lfh_arrival_today_refresh ON lufthansa_flight_history USING btree (arrival_schedule_date, actuals_refreshed);

-- 9. Historical Flights (depends on all flight tables)
CREATE TABLE IF NOT EXISTS public.historical_flights (
    id integer primary key not null default nextval('historical_flights_id_seq'::regclass),
    source character varying(20) not null,
    delay_minutes integer,
    is_delayed boolean,
    bts_data_history_id integer,
    lufthansa_data_history_id integer,
    departure_airport character varying(10),
    arrival_airport character varying(10),
    airline_code character varying(10),
    aircraft_code character varying(10),
    depart_airport_meteo character varying(50),
    arr_airport_meteo character varying(50),
    foreign key (aircraft_code) references public.aircrafts (aircraft_code)
        match simple on update no action on delete no action,
    foreign key (airline_code) references public.airlines (airline_code)
        match simple on update no action on delete no action,
    foreign key (arrival_airport) references public.airports (iata_code)
        match simple on update no action on delete no action,
    foreign key (bts_data_history_id) references public.bts_flight_history (id)
        match simple on update no action on delete no action,
    foreign key (departure_airport) references public.airports (iata_code)
        match simple on update no action on delete no action,
    foreign key (lufthansa_data_history_id) references public.lufthansa_flight_history (id)
        match simple on update no action on delete no action
);

-- 10. Weather cache
CREATE TABLE IF NOT EXISTS weather_hourly_cache (
    iata_code varchar(8) not null,
    hour_local timestamp not null,
    payload_json jsonb not null,
    created_at timestamp default now() not null,
    primary key (iata_code, hour_local)
);

CREATE INDEX IF NOT EXISTS idx_weather_cache_iata_hour ON weather_hourly_cache (iata_code, hour_local);

-- 11. OWM API Quota tracking
CREATE TABLE IF NOT EXISTS owm_api_quota (
    date_key date not null primary key,
    used_calls integer default 0 not null
);
