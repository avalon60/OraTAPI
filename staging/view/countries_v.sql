--liquibase formatted sql

--changeset cbostock:countries_v_create stripComments:false runOnChange:true

create or replace force view aut.countries_v as
   select
           country_id
         , country_name
         , region_id
         , created_by
         , created_date
       from countries;
--rollback drop view aut.countries_v;
