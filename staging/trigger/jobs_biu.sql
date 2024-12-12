--liquibase formatted sql
 
--changeset cbostock:jobs_biu_create stripComments:false endDelimiter:/ runOnChange:true
create or replace trigger aut.jobs_biu
before insert or update on aut.jobs
for each row
begin

   if inserting then
      :new.row_version := 1;
   elsif updating then
      :new.updated_on := current_timestamp;
      :new.updated_by := coalesce(sys_context('APEX$SESSION','APP_USER'), sys_context('USERENV', 'PROXY_USER'), sys_context('USERENV','SESSION_USER'), user);
      :new.row_version := :old.row_version + 1;
   end if;

end;
/

--rollback drop trigger aut.jobs_biu;
