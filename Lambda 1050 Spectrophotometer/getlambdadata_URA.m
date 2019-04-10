%loads all spectra from an output save folder from the Lambda 1050
%spectrophotometer in the SME basement. Specifically loads data saved by URA, which only allows one file to be
%scanned at a time. Select the folder that holds indiviual URA scan export subfolders. If all spectra
%have been exported in one folder, use "getlambdadata.m" instead.

function [wavelengths, spectra, titles, outputcell] = getlambdadata_URA

    checkstring = 'Sample.Raw.csv';
    
    folder = uigetdir();    
%     folder = 'E:\Data\MRC Spec\Rishi Kumar\20180323';
    topdir = dir(folder);    
    numfiles = size(topdir, 1) - 2;
    
    dataindex = 1;
    
    for i = 1:numfiles
        subpath = strcat(folder, '\', topdir(i+2).name);
        founddata = 0;
        
        if(isfolder(subpath))
            middir = dir(subpath);
            bottompath = strcat(middir(3).folder, '\', middir(3).name);
            bottomdir = dir(bottompath);
            numfiles_bot = size(bottomdir,1) - 2;
            for j = 1:numfiles_bot
                fpath = strcat(bottomdir(j+2).folder, '\', bottomdir(j+2).name);
                if (contains(fpath, checkstring))
                    outputcell{dataindex, 1} = topdir(i+2).name;
                    outputcell{dataindex, 2} = csvread(fpath, 1, 0);
                    dataindex = dataindex + 1;
                    founddata = 1;
                end
%                
%                 if(founddata == 1)
%                     break;
%                 end 
            end                    
        end
    end
        
    numspectra = size(outputcell, 1);
    numwavelengths = size(outputcell{1,2}, 1);
    
    
    spectra = zeros(numwavelengths, numspectra);
    
    for i = 1:numspectra
        if i == 1
            wavelengths = outputcell{1,2}(:,1);
        end
        
        spectra(:,i) = outputcell{i,2}(:,2);
    end
    
    titles = outputcell(:,1);
end
       