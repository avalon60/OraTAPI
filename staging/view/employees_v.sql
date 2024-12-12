--liquibase formatted sql

--changeset cbostock:employees_v_create stripComments:false runOnChange:true

create or replace force view aut.employees_v as
   select
           employee_id
         , first_name
         , last_name
         , email
         , phone_number
         , hire_date
         , job_id
         , salary
         , commission_pct
         , manager_id
         , department_id
         , created_by
         , created_on
         , updated_by
         , updated_on
         , row_version
       from employees;
--rollback drop view aut.employees_v;
