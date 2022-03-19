set search_path to xxxx;

alter table control add PRIMARY KEY(id);
alter table attr add PRIMARY KEY (id);
create index on attr(name);
create index on attr(value);

alter table node add PRIMARY KEY (id);
create index on node(urn);
create index on node(name);
create index on node(nodetype);

alter table pathway add PRIMARY KEY(id);
create index on pathway(name);
create index on pathway(type);
create index on pathway(urn);


alter table reference add PRIMARY KEY(unique_id);
create index on reference(id);
create index on reference(tissue);
create index on reference(pubyear);
create index on reference(textref);

select * into temp_outkey from  (select control.id, string_agg(node.name, '|') as outname  from control, node where node.id = any(control.outkey) group by control.id)a;
select * into temp_inkey from  (select control.id, string_agg(node.name, '|') as inname  from control, node where node.id = any(control.inkey) group by control.id)a;
select * into temp_inoutkey from  (select control.id, string_agg(node.name, '|') as inoutname  from control, node where node.id = any(control.inoutkey) group by control.id)a;

alter table control add column inname text;
alter table control add column outname text;
alter table control add column inoutname text;

create index on temp_inkey(id);
create index on temp_outkey(id);
create index on temp_inoutkey(id);

update control set inname    = temp_inkey.inname    from temp_inkey     where temp_inkey.id  = control.id;
update control set outname   = temp_outkey.outname  from temp_outkey    where temp_outkey.id = control.id;
update control set inoutname = temp_inoutkey.inoutname from temp_inoutkey  where temp_inoutkey.id  = control.id;

drop table temp_outkey;
drop table temp_inkey;
drop table temp_inoutkey;

create index on control(controltype);
create index on control(ontology);
create index on control(relationship);
create index on control(effect);
create index on control(mechanism);
create index on control(inname);
create index on control(outname);
create index on control(inoutname);
alter table control add column num_refs integer;

update control set num_refs = count from (select count(reference.id) as count, control.id from resnet.reference, resnet.control  where reference.id = control.attributes group by control.id)a  where a.id= control.id;

ALTER TABLE reference add constraint control_ref  foreign key (id) references resnet.control(id);
