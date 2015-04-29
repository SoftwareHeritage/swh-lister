
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
