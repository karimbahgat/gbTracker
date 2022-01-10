# gbTracker
geoBoundaries Django-based tool for tracking and recreating administrative boundary changes.

# Apps

The website is divided into the following components or apps, each responsible for particular tasks:

## changeManager

API-only for receiving, storing, and sharing data on boundary changes. 

## changeTracker

Forms and workflows for users to manually input and track individual boundary changes, sending it to the `changeManager`. 

## dataImporter

Forms and procedures for importing data from GIS-files into the `changeManager` app. 

## mapDigitizer

Interactive map forms for digitizing and extracting boundary data from map images, and sending it to the `changeManager`. 

## boundaryBuilder

The scripts and interactive workflows responsible for reconstructing and building boundaries over time based on data points from the `changeManager` app. 
