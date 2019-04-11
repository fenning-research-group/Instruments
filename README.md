# FRG Instruments

## Repository Description
This repository holds scripts to aid in the extraction and processing of data from various tools across campus. The organization structure is as follows:

- Tool Class
  - Data Extraction
    - Specific Tool
      - Scripts for loading data files output by the specific tool into matlab
  - Data Analysis
    - Scripts for analyzing data as extracted by a script from the Data Extraction folder

## Use Example
I have taken a UV-Vis powder reflectance curve, and would like to perform a Tauc plot analysis to determine the powder material's bandgap.

1. Go to the UV-Vis folder
2. Determine which instrument I used (let's say the Lambda 1050 in MRC), and go to the appropriate subfolder in UV-Vis/Data Extraction
3. Use the script to load my raw data into matlab. 
   - This procedure will be tool specific, so refer to the code header for specific use instructions
4. Look in the UV-Vis/Data Analysis folder to see if there is a Tauc plot analysis code already
   - If yes, run the script using the recently loaded data in matlab (again, refer to the code header for specific use instructions
     - If the script does not work, and you fix it, consider submitting a pull request to update the shared script
   - If no, and you make one that works, consider submitting a pull request to share the script

