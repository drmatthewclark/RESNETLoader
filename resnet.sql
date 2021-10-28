set search_path to resnet;

alter table resnet.control add PRIMARY KEY(id);
alter table resnet.attr add PRIMARY KEY (id);
create index on resnet.attr(name);
create index on resnet.attr(value);

alter table resnet.node add PRIMARY KEY (id);
create index on resnet.node(urn);
create index on resnet.node(name);
create index on resnet.node(nodetype);

alter table resnet.pathway add PRIMARY KEY(id);
create index on resnet.pathway(name);
create index on resnet.pathway(type);
create index on resnet.pathway(urn);


create index on resnet.reference(id);
create index on resnet.reference(tissue);
create index on resnet.reference(pubyear);
create index on resnet.reference(textref);

select * into resnet.temp_outkey from  (select control.id, string_agg(node.name, '|') as outname  from control, node where node.id = any(control.outkey) group by control.id)a;
select * into resnet.temp_inkey from  (select control.id, string_agg(node.name, '|') as inname  from control, node where node.id = any(control.inkey) group by control.id)a;
select * into resnet.temp_inoutkey from  (select control.id, string_agg(node.name, '|') as inoutname  from control, node where node.id = any(control.inoutkey) group by control.id)a;

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

create index on resnet.control(controltype);
create index on resnet.control(ontology);
create index on resnet.control(relationship);
create index on resnet.control(effect);
create index on resnet.control(mechanism);
create index on resnet.control(inname);
create index on resnet.control(outname);
create index on resnet.control(inoutname);
alter table resnet.control add column num_refs integer;

update resnet.control set num_refs = count from (select count(reference.id) as count, control.id from resnet.reference, resnet.control  where reference.id = control.attributes group by control.id)a  where a.id= control.id;

ALTER TABLE resnet.reference add constraint control_ref  foreign key (id) references resnet.control(id);
