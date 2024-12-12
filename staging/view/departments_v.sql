--liquibase formatted sql

--changeset cbostock:departments_v_create stripComments:false runOnChange:true

create or replace force view aut.departments_v as
   select
           department_id
         , department_name
         , manager_id
         , location_id
         , created_by
         , created_on
       from departments;
--rollback drop view aut.departments_v;
