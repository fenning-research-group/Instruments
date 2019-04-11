# FRG Instruments

## Repository Description
This repository holds scripts to aid in the extraction and processing of data from various tools across campus. The organization structure is as follows:

- Tool Class
  - Data Extraction
    - Specific Tool
      - Scripts for loading data files output by the specific tool into matlab
  - Data Processing
    - Scripts for analyzing data as extracted by a script from the Data Extraction folder

## Use Example
I have taken a UV-Vis powder reflectance curve, and would like to perform a Tauc plot analysis to determine the powder material's bandgap.

### 1. Go to the UV-Vis folder
```
fenning-research-group/Instruments/UV-Vis
```
### 2. Determine which instrument I used (let's say the Lambda 1050 in MRC), and go to the appropriate subfolder in UV-Vis/Data Extraction
```
fenning-research-group/Instruments/UV-Vis/Data Extraction/Lambda 1050 MRC
```
### 3. Use the script to load my raw data into matlab. 
#### This procedure will be tool specific, so refer to the code header for specific use instructions

getlambdadata.m header file looks like:
```
%loads all spectra from an output save folder from the Lambda 1050
%spectrophotometer in the SME basement. If any argument is passed, it will
%attempt to sort spectra by "Cycle#'. This is only relevant in diffusion experiment setup(ie, if cycles are
%set to > 1, and if all cycles are in one series. If you have 10 samples
%with 3 cycle each, this function will break. Don't use any argument in
%this case).
%
%  ex: mydata = getlambdadata    (opens UI to select folder, loads all spectra files within the folder)
%      mydata = getlambdadata(1) (opens UI to select folder, loads all spectra files within folder, then sorts by cycle number)
%
%      outputs data in struct format
 ```
Based on the example, I run the following
```
mypowderref = getlambdadata
```  
### 4. Look in the UV-Vis/Data Processing folder to see if there is a Tauc plot analysis code already
   #### - If yes, run the script using the recently loaded data in matlab (again, refer to the code header for specific use instructions
  ####    - If the script does not work, and you fix it, consider submitting a pull request to update the shared script

   #### - If no, and you make one that works, consider submitting a pull request to share the script

