create table if not exists public.aircrafts (
                                  aircraft_code character varying(10) primary key not null,
                                  airline_equip_code character varying(10),
                                  model character varying(100)
);

create table if not exists public.airlines (
                                 airline_code character varying(10) primary key not null,
                                 airline_name character varying(255),
                                 airline_code_icao character varying(10)
);

create table if not exists public.airports (
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

create table if not exists public.bts_flight_history (
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

create table if not exists public.cities (
                               city_code character varying(10) primary key not null,
                               name character varying(100),
                               country_code character varying(10),
                               foreign key (country_code) references public.countries (code)
                                   match simple on update no action on delete no action
);

create table if not exists public.countries (
                                  code character varying(10) primary key not null,
                                  name character varying(100)
);

create table if not exists public.historical_flights (
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

create table if not exists public.lufthansa_flight_history (
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
create unique index if not exists unique_flight_per_day on lufthansa_flight_history using btree (marketing_carrier_airline_id, marketing_carrier_flight_number, departure_schedule_date);
create index if not exists idx_lh_route_id on lufthansa_flight_history using btree (route_id);
create index if not exists  idx_lh_airline_id on lufthansa_flight_history using btree (marketing_carrier_airline_id);
create index if not exists  idx_lh_aircraft_code on lufthansa_flight_history using btree (equipment_aircraft_code);
create index if not exists  idx_flight_history_route_date on lufthansa_flight_history using btree (route_id, departure_schedule_date);
create index if not exists  ix_lfh_arrival_today_refresh on lufthansa_flight_history using btree (arrival_schedule_date, actuals_refreshed);

create table if not exists public.routes (
                               id integer primary key not null default nextval('routes_id_seq'::regclass),
                               departure_airport character varying(10),
                               arrival_airport character varying(10),
                               distance integer not null,
                               important boolean not null default false,
                               foreign key (arrival_airport) references public.airports (iata_code)
                                   match simple on update no action on delete no action,
                               foreign key (departure_airport) references public.airports (iata_code)
                                   match simple on update no action on delete no action
);
create index if not exists  idx_routes_departure_airport on routes using btree (departure_airport);
create index if not exists  idx_routes_arrival_airport on routes using btree (arrival_airport);
create index if not exists  idx_routes_origin_destination on routes using btree (departure_airport, arrival_airport);
create index if not exists  idx_routes_important on routes using btree (important) WHERE (important = true);

create table if not exists weather_hourly_cache
(
    iata_code    varchar(8)              not null,
    hour_local   timestamp               not null,
    payload_json jsonb                   not null,
    created_at   timestamp default now() not null,
    primary key (iata_code, hour_local)
);

create index idx_weather_cache_iata_hour
    on weather_hourly_cache (iata_code, hour_local);

create table if not exists owm_api_quota
(
    date_key   date              not null
        primary key,
    used_calls integer default 0 not null
);