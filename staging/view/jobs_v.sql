--liquibase formatted sql

--changeset cbostock:jobs_v_create stripComments:false runOnChange:true

create or replace force view aut.jobs_v as
   select
           job_id
         , job_title
         , min_salary
         , max_salary
         , created_by
         , created_on
       from jobs;
--rollback drop view aut.jobs_v;
