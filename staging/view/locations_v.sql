--liquibase formatted sql

--changeset cbostock:locations_v_create stripComments:false runOnChange:true

create or replace force view aut.locations_v as
   select
           location_id
         , street_address
         , postal_code
         , city
         , state_province
         , country_id
         , created_by
         , created_on
       from locations;
--rollback drop view aut.locations_v;
