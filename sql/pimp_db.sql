
create view orig_repos as
    select id, name, full_name, html_url, description, last_seen
    from repos
    where not fork;

create view fork_repos as
    select id, name, full_name, html_url, description, last_seen
    from repos
    where fork

create extension pg_trgm;

create index ix_trgm_repos_description on
    repos using gin (description gin_trgm_ops);

create index ix_trgm_repos_full_name on
    repos using gin (full_name gin_trgm_ops);

create table repos_history (
    ts          timestamp default current_timestamp,
    repos       integer not null,
    fork_repos  integer,
    orig_repos  integer
);

create view repo_creations as
    select today.ts :: date as date,
           today.repos - yesterday.repos as repos,
           today.fork_repos - yesterday.fork_repos as fork_repos,
           today.orig_repos - yesterday.orig_repos as orig_repos
    from repos_history today
    join repos_history yesterday on
         (yesterday.ts = (select max(ts)
                          from repos_history
                          where ts < today.ts));
