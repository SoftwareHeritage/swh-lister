
-- -- return a random sample of repos, containing %percent repositories
-- create or replace function repos_random_sample_array(percent real)
-- returns setof repos as $$
-- declare
--     samples integer;
--     repo repos%rowtype;
--     ids integer[];
-- begin
--     select floor(count(*) / 100 * percent) into samples from repos;
--     ids := array(select id from repos order by id);
--     for i in 1 .. samples loop
--      select * into repo
--          from repos
--          where id = ids[round(random() * samples)];
--      return next repo;
--     end loop;
--     return;
-- end
-- $$
-- language plpgsql;

-- return a random sample of repositories
create or replace function repos_random_sample(percent real)
returns setof repos as $$
declare
    sample_size integer;
begin
    select floor(count(*) / 100 * percent) into sample_size from repos;
    return query
        select * from repos
        order by random()
        limit sample_size;
    return;
end
$$
language plpgsql;

-- -- return a random sample of repositories
-- create or replace function random_sample_sequence(percent real)
-- returns setof repos as $$
-- declare
--     sample_size integer;
--     seq_size integer;
--     min_id integer;
--     max_id integer;
-- begin
--     select floor(count(*) / 100 * percent) into sample_size from repos;
--     select min(id) into min_id from repos;
--     select max(id) into max_id from repos;
--     seq_size := sample_size * 3;  -- IDs are sparse, generate a larger sequence
--                                   -- to have enough of them
--     return query
--         select * from repos
--         where id in
--             (select floor(random() * (max_id - min_id + 1))::integer
--                     + min_id
--              from generate_series(1, seq_size))
--         order by random() limit sample_size;
--     return;
-- end
-- $$
-- language plpgsql;

create or replace function repos_well_known()
returns setof repos as $$
begin
    return query
        select * from repos
	where full_name like 'apache/%'
	   or full_name like 'eclipse/%'
	   or full_name like 'mozilla/%'
	   or full_name = 'torvalds/linux'
	   or full_name = 'gcc-mirror/gcc';
    return;
end
$$
language plpgsql;

create table crawl_history (
    id       bigserial primary key,
    repo     integer references repos(id),
    task_id  uuid,  -- celery task id
    date     timestamptz not null,
    duration interval,
    status   boolean,
    result   json,
    stdout   text,
    stderr   text
);

create index on crawl_history (repo);

create view missing_orig_repos AS
    select *
    from orig_repos as repos
    where not exists
        (select 1 from crawl_history as history
	 where history.repo = repos.id);

create view missing_fork_repos AS
    select *
    from fork_repos as repos
    where not exists
        (select 1 from crawl_history as history
	 where history.repo = repos.id);
