
CREATE VIEW orig_repos AS
    SELECT id, name, full_name, html_url, description, last_seen
    FROM repos
    WHERE NOT fork;

CREATE VIEW fork_repos AS
    SELECT id, name, full_name, html_url, description, last_seen
    FROM repos
    WHERE fork

CREATE EXTENSION pg_trgm;

CREATE INDEX ix_trgm_repos_description ON
    repos USING gin (description gin_trgm_ops);

CREATE INDEX ix_trgm_repos_full_name ON
    repos USING gin (full_name gin_trgm_ops);

CREATE TABLE repos_history (
    ts          timestamp DEFAULT current_timestamp,
    repos       integer NOT NULL,
    fork_repos  integer,
    orig_repos  integer
);

CREATE VIEW repo_creations AS
    SELECT today.ts :: date as date,
           today.repos - yesterday.repos as repos,
           today.fork_repos - yesterday.fork_repos as fork_repos,
           today.orig_repos - yesterday.orig_repos as orig_repos
    FROM repos_history today
    JOIN repos_history yesterday ON
         (yesterday.ts = (SELECT max(ts)
                          FROM repos_history
                          WHERE ts < today.ts));

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
