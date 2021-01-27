#!/usr/bin/Rscript

# This R script calls the buildin API to get list of
# all the packages of R and their description, then convert the API
# response to JSON string and print it

db <- tools::CRAN_package_db()[, c("Package", "Version", "Packaged")]
dbjson <- jsonlite::toJSON(db)
print(dbjson)