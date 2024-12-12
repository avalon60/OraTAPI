--liquibase formatted sql

--changeset cbostock:regions_v_create stripComments:false runOnChange:true

create or replace force view aut.regions_v as
   select
           region_id
         , region_name
         , created_by
         , created_on
       from regions;
--rollback drop view aut.regions_v;
