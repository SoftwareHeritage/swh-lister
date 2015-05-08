
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
