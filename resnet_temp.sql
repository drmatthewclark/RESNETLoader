set search_path to resnet_temp;

alter table resnet_temp.control add PRIMARY KEY(id);
alter table resnet_temp.attr add PRIMARY KEY (id);
create index on resnet_temp.attr(name);
create index on resnet_temp.attr(value);

alter table resnet_temp.node add PRIMARY KEY (id);
create index on resnet_temp.node(urn);
create index on resnet_temp.node(name);
create index on resnet_temp.node(nodetype);

alter table resnet_temp.pathway add PRIMARY KEY(id);
create index on resnet_temp.pathway(name);
create index on resnet_temp.pathway(type);
create index on resnet_temp.pathway(urn);


create index on resnet_temp.reference(id);
create index on resnet_temp.reference(tissue);
create index on resnet_temp.reference(pubyear);
create index on resnet_temp.reference(textref);

select * into resnet_temp.temp_outkey from  (select control.id, string_agg(node.name, '|') as outname  from control, node where node.id = any(control.outkey) group by control.id)a;
select * into resnet_temp.temp_inkey from  (select control.id, string_agg(node.name, '|') as inname  from control, node where node.id = any(control.inkey) group by control.id)a;
select * into resnet_temp.temp_inoutkey from  (select control.id, string_agg(node.name, '|') as inoutname  from control, node where node.id = any(control.inoutkey) group by control.id)a;

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

create index on resnet_temp.control(controltype);
create index on resnet_temp.control(ontology);
create index on resnet_temp.control(relationship);
create index on resnet_temp.control(effect);
create index on resnet_temp.control(mechanism);
create index on resnet_temp.control(inname);
create index on resnet_temp.control(outname);
create index on resnet_temp.control(inoutname);
alter table resnet_temp.control add column num_refs integer;

update resnet_temp.control set num_refs = count from (select count(reference.id) as count, control.id from resnet_temp.reference, resnet_temp.control  where reference.id = control.attributes group by control.id)a  where a.id= control.id;
