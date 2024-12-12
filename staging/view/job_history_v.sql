--liquibase formatted sql

--changeset cbostock:job_history_v_create stripComments:false runOnChange:true

create or replace force view aut.job_history_v as
   select
           employee_id
         , start_date
         , end_date
         , job_id
         , department_id
         , created_by
         , created_on
       from job_history;
--rollback drop view aut.job_history_v;
